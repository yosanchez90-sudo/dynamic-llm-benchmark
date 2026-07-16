"""Read-only helper for the inst1-control investigation (step G): for the
ACTUAL inst1 training examples (train_qwen{1_5b,7b}_inst1.jsonl), join back
to the source dynamic-benchmark results file on (template_id, instance_seed)
and report what fraction were ALSO baseline_passed=True (i.e. not just
exec_ok, but actually correct). This is the theoretical ceiling on "seen"
baseline_pass a model could reach via pure verbatim memorization of its own
training targets, since inst1's min_quality filter is exec_ok, not
baseline_passed (unlike bp_gpt5/bp_own, which filter on baseline_passed).

Usage:
    python analysis/inst1_control_memorization_ceiling.py \\
        --train-file data/finetune/train_qwen1_5b_inst1.jsonl \\
        --source-file data/results/dynamic/Qwen__Qwen2.5-Coder-1.5B-Instruct__dynamic__zero_shot__inst1__20260609T221336.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-file", type=Path, required=True)
    parser.add_argument("--source-file", type=Path, required=True)
    args = parser.parse_args()

    train_rows = [json.loads(l) for l in args.train_file.read_text().splitlines() if l.strip()]
    source_rows = [json.loads(l) for l in args.source_file.read_text().splitlines() if l.strip()]

    # source file may contain duplicate (template_id, instance_seed) rows
    # (observed: 300 rows for what should be a single 150-problem
    # instantiation) -- de-dup by keeping the first occurrence, since the
    # training-data-prep script's own log says "Loaded 150 records".
    by_key: dict[tuple, dict] = {}
    for r in source_rows:
        key = (r["template_id"], r["instance_seed"])
        by_key.setdefault(key, r)

    print(f"train file: {args.train_file} ({len(train_rows)} examples)")
    print(f"source file: {args.source_file} ({len(source_rows)} rows, "
          f"{len(by_key)} unique (template_id, instance_seed) keys)")

    matched = 0
    also_passed = 0
    unmatched = []
    for t in train_rows:
        key = (t["template_id"], t["instance_seed"])
        src = by_key.get(key)
        if src is None:
            unmatched.append(key)
            continue
        matched += 1
        if src.get("baseline_passed") is True:
            also_passed += 1

    print(f"matched to source: {matched}/{len(train_rows)} "
          f"({len(unmatched)} unmatched: {unmatched[:5]}{'...' if len(unmatched) > 5 else ''})")
    print(f"also baseline_passed=True: {also_passed}/{matched} "
          f"({100 * also_passed / matched:.1f}%)")
    print(f"-> memorization ceiling for 'seen' baseline_pass if every "
          f"training example were reproduced verbatim: ~{100 * also_passed / matched:.1f}%")


if __name__ == "__main__":
    main()
