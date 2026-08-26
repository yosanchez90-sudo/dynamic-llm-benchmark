"""Download completed OpenAI Batch results and run mutation scoring.

Polls the batch until it completes, downloads the output file, then for
each response: extracts the test file, runs the mutation scorer, and
appends a fully scored record to the appropriate per-model JSONL file.

Run this on a k2-medpri node (CPU-only) via run_eval_api.slurm, or on the
login node for small result sets.

Usage:
    python scripts/process_batch.py data/batches/batch_state_<ts>.json

    # Check status only (no scoring):
    python scripts/process_batch.py data/batches/batch_state_<ts>.json --status-only

    # If results are already downloaded, skip the API poll:
    python scripts/process_batch.py data/batches/batch_state_<ts>.json \\
        --results-file data/batches/batch_output_<ts>.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from openai import OpenAI  # noqa: E402
from src.data import test_gen, ult_plt  # noqa: E402
from src.eval.test_gen_problem import TestGenRecord, compute_model_label  # noqa: E402
from src.eval.test_gen_scorer import (  # noqa: E402
    extract_test_file, sanitize_test_file, score_problem,
)
from src.logging_utils import append_jsonl  # noqa: E402
from src.pricing import compute_cost  # noqa: E402

# Every row this script scores comes from the OpenAI Batch API by
# construction (that's the whole point of this script). OpenAI bills
# Batch API usage at exactly 50% of the standard rate in src/pricing.py's
# PRICING table (confirmed directly against OpenAI's pricing page/model
# pages, analysis/OPENAI_COST_AND_BILLING.md). compute_cost() has no
# batch-awareness of its own (same function is also called for live/
# real-time API models elsewhere), so this script must apply the discount
# itself. Found 2026-08-07: it never did. Every cost_usd this script has
# ever written (including every pre-existing GPT-5/-mini row from the
# original inst1 batches) is exactly 2x the real billed amount. Not
# corrected retroactively in already-written rows, same policy as the
# gpt-5.4 pricing-table bug found earlier this pass (cost_usd is a
# logged-at-the-time field), see CLAUDE.md / OPENAI_COST_AND_BILLING.md
# for the disclosure.
_BATCH_DISCOUNT = 0.5


# ── poll until done ──────────────────────────────────────────────────────────

def poll_batch(client: OpenAI, batch_id: str, poll_interval: int = 60) -> str:
    """Block until batch reaches a terminal state. Returns output_file_id."""
    terminal = {"completed", "failed", "expired", "cancelled"}
    while True:
        batch = client.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(
            f"  [{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
            f"status={batch.status}  "
            f"total={counts.total}  completed={counts.completed}  "
            f"failed={counts.failed}",
            flush=True,
        )
        if batch.status in terminal:
            if batch.status != "completed":
                raise RuntimeError(f"Batch ended with status: {batch.status}")
            return batch.output_file_id
        time.sleep(poll_interval)


# ── download results ─────────────────────────────────────────────────────────

def download_results(client: OpenAI, output_file_id: str, dest: Path) -> Path:
    content = client.files.content(output_file_id)
    dest.write_bytes(content.read())
    print(f"Results downloaded: {dest}  ({dest.stat().st_size:,} bytes)")
    return dest


# ── reconstruct problems (for fn_name, source, mutants) ──────────────────────

def build_problem_map(state: dict) -> dict[str, object]:
    """Return {custom_id: TestGenProblem} by re-running the template engine
    (Dynamic) or the ULT/PLT static-benchmark loader, dispatched per
    req["benchmark"], mirrors test_gen_runner.py::_load_problems()'s own
    dispatch.

    Fixed 2026-08-06 (Phase B pre-scoring validation, caught before ever
    running against a real batch): this previously called test_gen.load()
    (the Dynamic loader) unconditionally, regardless of benchmark. For a
    ULT/PLT batch this doesn't crash. It just returns Dynamic-shaped
    (template_id, instance_seed) keys that never match ULT/PLT's own
    ("ULT-<task_id>"/"PLT-<task_id>", int(task_id)) keys, so every single
    ULT/PLT row would silently print "problem not reconstructed" and get
    skipped. 1,600 real, already-paid-for API responses would never be
    scored or written anywhere, with no exception raised to flag it.
    """
    # Group requests by config so we call the loader once per config.
    by_config: dict[str, list[dict]] = {}
    for req in state["requests"]:
        by_config.setdefault(req["config_name"], []).append(req)

    problem_map: dict[str, object] = {}
    for config_name, reqs in by_config.items():
        # All requests in a group share the same load() parameters, except
        # tier, which varies per-request. Derive it from the group itself
        # instead of assuming L1/L2 (batches can target L3/L4 too).
        r0 = reqs[0]
        if r0["benchmark"] in ("ult", "plt"):
            # task_id round-trips through instance_seed=int(task_id) in
            # ult_plt.py's own load(), reconstructing the string form
            # from the batch's own recorded instance_seed, not
            # re-deriving which subsample_tag was used (not stored in
            # request_meta). ult_plt.load() raises loudly if any requested
            # task_id isn't found in the current candidate pool ("data
            # drift?") instead of silently dropping it, so a formatting
            # mismatch here surfaces as an exception, not silent data loss.
            task_ids = {str(r["instance_seed"]) for r in reqs}
            problems = ult_plt.load(
                r0["benchmark"],
                prompting_condition=r0["prompting_condition"],
                task_ids=task_ids,
            )
        else:
            tiers = tuple(sorted({r["tier"] for r in reqs}))
            problems = test_gen.load(
                instantiation_id   = r0["instantiation_id"],
                instantiation_seed = r0.get("instantiation_seed", 1),
                instance_seeds     = (101,102,103,104,105),
                tiers              = tiers,
                prompting_condition= r0["prompting_condition"],
            )
        # Index by (template_id, instance_seed) for fast lookup.
        prob_index = {(p.template_id, p.instance_seed): p for p in problems}
        for req in reqs:
            key = (req["template_id"], req["instance_seed"])
            if key in prob_index:
                problem_map[req["custom_id"]] = prob_index[key]
            else:
                print(f"  WARNING: problem not found for {req['custom_id']} {key}")

    return problem_map


# ── score and write ───────────────────────────────────────────────────────────

def process_results(
    results_path: Path,
    state: dict,
    problem_map: dict,
) -> None:
    req_index = {r["custom_id"]: r for r in state["requests"]}

    # Collect output paths so we can print a summary.
    out_paths: set[Path] = set()

    lines = [l for l in results_path.read_text().splitlines() if l.strip()]
    print(f"\nProcessing {len(lines)} results…\n")

    for raw_line in lines:
        result = json.loads(raw_line)
        custom_id = result["custom_id"]
        req       = req_index.get(custom_id)

        if req is None:
            print(f"  SKIP {custom_id}: not in state file")
            continue

        # ── extract response ──────────────────────────────────────────────
        # A row can fail in three shapes: top-level "error" set, an empty
        # response body (transient 5xx with no body), or a populated body
        # that itself holds an OpenAI error object instead of "choices"
        # (e.g. 400 invalid_prompt, 500 server_error). All three must be
        # caught here or the "choices"[0] lookup below raises KeyError and
        # aborts the whole batch mid-run.
        resp_body  = result.get("response", {}).get("body", {})
        body_error = result.get("error") or resp_body.get("error")
        if not resp_body or body_error or not resp_body.get("choices"):
            print(f"  ERROR {custom_id}: {body_error or 'no choices in response body'}")
            continue

        choice       = resp_body["choices"][0]
        response_text= choice["message"]["content"] or ""
        finish_reason= choice.get("finish_reason", "")
        usage        = resp_body.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens= usage.get("completion_tokens", 0)
        standard_rate_cost = compute_cost(req["model_id"], input_tokens, output_tokens)
        cost_usd = standard_rate_cost * _BATCH_DISCOUNT if standard_rate_cost is not None else None

        # ── reconstruct problem ───────────────────────────────────────────
        prob = problem_map.get(custom_id)
        if prob is None:
            print(f"  SKIP {custom_id}: problem not reconstructed")
            continue

        # ── extract + sanitize test file ──────────────────────────────────
        test_file          = extract_test_file(response_text)
        test_file, repairs = sanitize_test_file(test_file, prob.fn_name)

        # ── score ─────────────────────────────────────────────────────────
        scored = score_problem(
            fn_source  = prob.source,
            fn_name    = prob.fn_name,
            test_source= test_file,
            mutants    = prob.mutants,
            timeout    = req["mutant_timeout_s"],
            n_workers  = req["mutation_workers"],
        )

        canonical_prompt = json.dumps({"messages": prob.messages},
                                      sort_keys=True, ensure_ascii=False)

        record = TestGenRecord(
            model                            = req["model_id"],
            instantiation_id                 = req["instantiation_id"],
            template_id                      = req["template_id"],
            instance_seed                    = req["instance_seed"],
            tier                             = req["tier"],
            K                               = req["K"],
            prompting_condition              = req["prompting_condition"],
            benchmark                        = req["benchmark"],
            exec_rate                        = 1.0 if scored.exec_ok else 0.0,
            statement_coverage               = scored.statement_coverage,
            branch_coverage                  = scored.branch_coverage,
            mutation_score                   = scored.mutation_score,
            mutants_total                    = scored.mutants_total,
            mutants_killed                   = scored.mutants_killed,
            mutants_dropped_for_import_failure= scored.mutants_dropped,
            generation_latency_seconds       = 0.0,    # not available for batch API calls
            model_revision                   = req["model_revision"],
            provider                         = req["provider"],
            prompt_hash                      = hashlib.sha256(
                                                  canonical_prompt.encode()
                                               ).hexdigest(),
            response                         = response_text,
            extracted_test_file              = test_file,
            generation_config                = {
                "max_new_tokens": req["max_new_tokens"],
                "do_sample": True,
                "temperature": None,   # omitted for reasoning models
                "top_p": None,
                "seed": None,
            },
            cost_usd                         = cost_usd,
            timestamp                        = datetime.now(timezone.utc).isoformat(),
            runtime_info                     = {
                "api_response_id":   resp_body.get("id"),
                "finish_reason":     finish_reason,
                "system_fingerprint":resp_body.get("system_fingerprint"),
                "input_tokens":      input_tokens,
                "output_tokens":     output_tokens,
                "batch_custom_id":   custom_id,
            },
            baseline_passed                  = scored.baseline_passed,
            notes                            = "; ".join(
                filter(None, [scored.notes] + repairs)
            ),
            model_label                      = compute_model_label(req["model_id"]),
        )

        # ── write to per-model output file ────────────────────────────────
        safe_model = compute_model_label(req["model_id"])
        out_dir    = Path(req["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        # Use the state timestamp so all records from one batch land in one file.
        out_path = out_dir / (
            f"{safe_model}__{req['benchmark']}__{req['prompting_condition']}"
            f"__inst{req['instantiation_id']}__batch_{state['created_at']}.jsonl"
        )
        append_jsonl(record, out_path)
        out_paths.add(out_path)

        ms = (f"{scored.mutation_score:.2f}"
              if scored.mutation_score is not None else "n/a")
        print(f"  {custom_id}  {req['template_id']} seed={req['instance_seed']}"
              f"  exec={'Y' if scored.exec_ok else 'N'}  Mut@K={ms}")

    print(f"\nOutput files:")
    for p in sorted(out_paths):
        n = sum(1 for _ in p.open())
        print(f"  {p}  ({n} records)")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_file", type=Path)
    parser.add_argument("--status-only", action="store_true",
                        help="Print batch status and exit without scoring.")
    parser.add_argument("--results-file", type=Path, default=None,
                        help="Use a pre-downloaded results JSONL (skip polling).")
    parser.add_argument("--poll-interval", type=int, default=60,
                        help="Seconds between status checks (default 60).")
    args = parser.parse_args()

    state = json.loads(args.state_file.read_text())
    batch_id = state["batch_id"]
    client   = OpenAI()

    print(f"Batch: {batch_id}  ({state['n_requests']} requests)")

    if args.status_only:
        batch = client.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(f"Status: {batch.status}")
        print(f"  total={counts.total}  completed={counts.completed}  failed={counts.failed}")
        return

    # ── poll / download ───────────────────────────────────────────────────────
    if args.results_file:
        results_path = args.results_file
        print(f"Using pre-downloaded results: {results_path}")
    else:
        print("Polling batch status…")
        output_file_id = poll_batch(client, batch_id, args.poll_interval)

        batches_dir  = args.state_file.parent
        results_path = batches_dir / f"batch_output_{state['created_at']}.jsonl"
        download_results(client, output_file_id, results_path)

        # Update state with output file id.
        state["output_file_id"] = output_file_id
        state["results_file"]   = str(results_path)
        args.state_file.write_text(json.dumps(state, indent=2))

    # ── reconstruct problems + score ──────────────────────────────────────────
    print("Reconstructing problems from template engine…")
    problem_map = build_problem_map(state)
    print(f"  {len(problem_map)} problems reconstructed.")

    process_results(results_path, state, problem_map)


if __name__ == "__main__":
    main()
