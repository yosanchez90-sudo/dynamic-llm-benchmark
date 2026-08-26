"""Prepare instruction-tuning training data for the contamination-simulation experiment.

Reads the Qwen 7B inst1 evaluation results, reconstructs the original prompt
for each problem (using the same template engine the evaluation used), pairs it
with the model's own extracted test file, and writes a training JSONL.

Only records where the generated test executed cleanly (exec_ok) are kept. We
don't want to teach the model to produce broken syntax.

Output: data/finetune/train_qwen7b_inst1.jsonl
Each line: {"messages": [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}],
            "template_id": "...", "instance_seed": 1101}

Usage:
    python scripts/prepare_finetune_data.py
    python scripts/prepare_finetune_data.py --min-quality baseline_passed
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data import test_gen  # noqa: E402


RESULTS_FILE = (
    ROOT / "data/results/dynamic"
    / "Qwen__Qwen2.5-Coder-7B-Instruct__dynamic__zero_shot__inst1__20260617T124709.jsonl"
)
OUT_FILE = ROOT / "data/finetune/train_qwen7b_inst1.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None,
                        help="Finetune YAML config. Reads data.results_file, "
                             "data.train_file, data.min_quality if not overridden.")
    parser.add_argument(
        "--min-quality",
        choices=["exec_ok", "baseline_passed"],
        default=None,
    )
    parser.add_argument("--results-file", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    # Resolve from config first, then CLI flags override.
    cfg_data: dict = {}
    if args.config:
        cfg_data = yaml.safe_load(args.config.read_text()).get("data", {})

    results_file = args.results_file or Path(cfg_data.get("results_file", RESULTS_FILE))
    out_file     = args.out         or Path(cfg_data.get("train_file",    OUT_FILE))
    min_quality  = args.min_quality or cfg_data.get("min_quality", "exec_ok")

    # Rebind so the rest of the function uses these names.
    args.results_file = results_file
    args.out          = out_file
    args.min_quality  = min_quality

    # ── load scored results ───────────────────────────────────────────────────
    rows = [json.loads(l) for l in args.results_file.read_text().splitlines() if l.strip()]
    print(f"Loaded {len(rows)} records from {args.results_file.name}")

    if args.min_quality == "baseline_passed":
        rows = [r for r in rows if r.get("baseline_passed")]
    else:
        rows = [r for r in rows if r.get("exec_rate", 0) == 1.0]

    print(f"After quality filter ({args.min_quality}): {len(rows)} training examples")

    # ── rebuild problem prompts from the template engine ─────────────────────
    # test_gen.load() is deterministic given (instantiation_seed, instance_seeds).
    # inst1 used instantiation_seed=1, instance_seeds=(101..105).
    problems = test_gen.load(
        instantiation_id="1",
        instantiation_seed=1,
        instance_seeds=(101, 102, 103, 104, 105),
        tiers=("L1", "L2"),
        prompting_condition="zero_shot",
    )
    prob_index = {(p.template_id, p.instance_seed): p for p in problems}
    print(f"Template engine produced {len(problems)} problems")

    # ── pair prompts with responses ───────────────────────────────────────────
    args.out.parent.mkdir(parents=True, exist_ok=True)
    written, skipped = 0, 0

    with args.out.open("w") as fh:
        for r in rows:
            key = (r["template_id"], r["instance_seed"])
            prob = prob_index.get(key)
            if prob is None:
                skipped += 1
                continue

            test_source = r.get("extracted_test_file", "").strip()
            if not test_source:
                skipped += 1
                continue

            # The prompt is the last user message the model received.
            # prob.messages is a list of {"role":..., "content":...} dicts.
            record = {
                "messages": prob.messages + [
                    {"role": "assistant", "content": test_source}
                ],
                "template_id":   r["template_id"],
                "instance_seed": r["instance_seed"],
                "tier":          r["tier"],
                "mutation_score": r.get("mutation_score"),
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    print(f"\nWrote {written} training examples to {args.out}")
    if skipped:
        print(f"Skipped {skipped} examples (no matching problem or empty test file)")


if __name__ == "__main__":
    main()
