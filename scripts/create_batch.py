"""Create and submit an OpenAI Batch covering one or more experiment configs.

Generates all (model × problem) inference requests, writes the batch input
JSONL, uploads it to the Files API, and submits it as a Batch job.
A state file is saved so process_batch.py can reconstruct which result
belongs to which problem and run mutation scoring.

Usage (from the dissertation root, with venv active):
    python scripts/create_batch.py \\
        configs/gpt_5_mini__dynamic_L1L2.yaml \\
        configs/gpt_5__dynamic_L1L2.yaml

Output files (in data/batches/):
    batch_input_<timestamp>.jsonl   – uploaded request lines
    batch_state_<timestamp>.json    – batch_id + per-request metadata
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from openai import OpenAI  # noqa: E402
from src.eval.test_gen_runner import _load_problems  # noqa: E402

# Reasoning-class models that reject custom temperature/top_p.
# Detected experimentally; add new models here as needed.
_FIXED_TEMP_MODELS = {
    "gpt-5-2025-08-07",
    "gpt-5-mini-2025-08-07",
}


def _build_request_body(model_id: str, messages: list[dict], max_tokens: int) -> dict:
    body: dict = {
        "model": model_id,
        "messages": messages,
        "max_completion_tokens": max_tokens,
    }
    # Reasoning models only accept temperature=1 (their default).
    # Omitting the parameter is cleaner than passing 1 explicitly.
    if model_id not in _FIXED_TEMP_MODELS:
        body["temperature"] = 0.2
        body["top_p"] = 1.0
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("configs", nargs="+", type=Path,
                        help="One or more YAML experiment configs")
    parser.add_argument("--batches-dir", default="data/batches", type=Path)
    parser.add_argument("--submit", action="store_true",
                        help="Upload and submit the batch to OpenAI (spends real money). "
                             "Default is to only write the batch JSONL/state files without "
                             "uploading or submitting — changed 2026-08-05 so the default "
                             "action of this script is never a paid submission; the prior "
                             "default was --no-submit as an opt-OUT, i.e. running this script "
                             "with no flags used to submit and spend by default.")
    args = parser.parse_args()

    client = OpenAI()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    args.batches_dir.mkdir(parents=True, exist_ok=True)

    batch_input_path = args.batches_dir / f"batch_input_{ts}.jsonl"
    state_path       = args.batches_dir / f"batch_state_{ts}.json"

    # ── build request lines ──────────────────────────────────────────────────
    request_meta: list[dict] = []   # parallel list to batch_lines
    batch_lines:  list[str]  = []

    for cfg_path in args.configs:
        with open(cfg_path) as f:
            config = yaml.safe_load(f)

        model_id   = config["model"]["id"]
        max_tokens = config["generation"]["max_new_tokens"]

        # Dispatches to the Dynamic loader or the ULT/PLT static-benchmark
        # loader based on config["benchmark"] — same dispatch test_gen_runner.py
        # uses for live eval, so batch-prepared requests and live-eval requests
        # are guaranteed to load identical problems for a given config.
        problems = _load_problems(config)

        print(f"{cfg_path.name}: {len(problems)} problems for {model_id}")

        for prob in problems:
            idx        = len(batch_lines)
            custom_id  = f"req-{idx:05d}"

            line = {
                "custom_id": custom_id,
                "method":    "POST",
                "url":       "/v1/chat/completions",
                "body":      _build_request_body(model_id, prob.messages, max_tokens),
            }
            batch_lines.append(json.dumps(line, ensure_ascii=False))

            request_meta.append({
                "custom_id":          custom_id,
                "config_name":        config["name"],
                "model_id":           model_id,
                "model_revision":     config["model"].get("revision", model_id),
                "provider":           config["model"]["provider"],
                "template_id":        prob.template_id,
                "instance_seed":      prob.instance_seed,
                "tier":               prob.tier,
                "instantiation_id":   prob.instantiation_id,
                "instantiation_seed": config.get("instantiation_seed"),  # None for ULT/PLT (no instantiations)
                "prompting_condition":prob.prompting_condition,
                "benchmark":          prob.benchmark,
                "K":                  config.get("K", 1),
                "max_new_tokens":     max_tokens,
                "mutation_workers":   config.get("mutation_workers", 4),
                "mutant_timeout_s":   config.get("mutant_timeout_seconds", 30),
                "output_dir":         config["output_dir"],
            })

    total = len(batch_lines)
    print(f"\nTotal requests: {total}")

    # ── write batch input file ────────────────────────────────────────────────
    batch_input_path.write_text("\n".join(batch_lines) + "\n")
    print(f"Batch input written: {batch_input_path}")

    if not args.submit:
        # Also save a state file without a batch_id so process_batch.py can
        # be used once someone (you or a supervisor) submits and provides
        # the batch_id / results file.
        state = {
            "batch_id":      None,
            "input_file_id": None,
            "created_at":    ts,
            "status":        "not_submitted",
            "n_requests":    total,
            "requests":      request_meta,
        }
        state_path.write_text(json.dumps(state, indent=2))
        print(f"State saved: {state_path}")
        print(f"\nNot submitted (default — pass --submit to upload and submit for real).")
        print(f"Send {batch_input_path} to your supervisor, or re-run with --submit")
        print("using your own OpenAI API key to fund it yourself.")
        print("When you have the results JSONL, run:")
        print(f"  python scripts/process_batch.py {state_path} \\")
        print(f"      --results-file <path-to-results.jsonl>")
        return

    # ── upload and submit ─────────────────────────────────────────────────────
    print("Uploading to OpenAI Files API…")
    with batch_input_path.open("rb") as fh:
        uploaded = client.files.create(file=fh, purpose="batch")
    print(f"File uploaded: {uploaded.id}")

    print("Submitting batch…")
    batch = client.batches.create(
        input_file_id    = uploaded.id,
        endpoint         = "/v1/chat/completions",
        completion_window= "24h",
    )
    print(f"Batch created: {batch.id}  status={batch.status}")

    # ── save state ───────────────────────────────────────────────────────────
    state = {
        "batch_id":        batch.id,
        "input_file_id":   uploaded.id,
        "created_at":      ts,
        "status":          batch.status,
        "n_requests":      total,
        "requests":        request_meta,
    }
    state_path.write_text(json.dumps(state, indent=2))
    print(f"State saved: {state_path}")
    print(f"\nRun next:\n  python scripts/process_batch.py {state_path}")


if __name__ == "__main__":
    main()
