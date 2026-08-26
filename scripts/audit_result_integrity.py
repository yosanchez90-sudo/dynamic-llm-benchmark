"""Data-integrity audit for data/results/{dynamic,ult,plt}/*.jsonl.

Triggered by finding that src/eval/test_gen_runner.py's resume-file matcher
(_find_resume_file) matches on (model_label, benchmark, prompting_condition,
instantiation_id) only, NOT tier. Two SLURM jobs targeting the same
(benchmark, instantiation) with overlapping runtimes (confirmed via job
logs for several models' inst4/inst5 dynamic backfill, 2026-07-14) could
race on the same output file. This script checks what
actually happened to the data, instead of reasoning about what could have:

  1. STRICT PARSE: every line in every non-.bak .jsonl file must be valid
     JSON. Reports file + line number for any failure (malformed/truncated
     lines are the direct fingerprint of an interleaved-write race).
  2. DUPLICATE TRIPLES: (template_id, instance_seed, model_label) should be
     unique within one benchmark directory. Reports every duplicate,
     including whether the two rows agree in content (byte-identical
     concatenation of the fields load_records() reads) or genuinely
     conflict (would bias an aggregate mean, not just double-count
     a screenshot of the same value).
  3. ROW COUNT: physical line count per (model_label, benchmark, tier,
     instantiation) cell vs count of DISTINCT (template_id, instance_seed)
     pairs. A gap between the two is exactly what a race would produce
     (N rows for M<N distinct problems).

Read-only. Does not modify or delete anything. Run directly (pure Python,
JSON parsing over ~10-20k lines total, not GPU/CPU research compute).

Usage: python scripts/audit_result_integrity.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRS = ["dynamic", "ult", "plt"]


def iter_files(d: Path):
    for fp in sorted(d.glob("*.jsonl")):
        if ".bak" in fp.name or "pre_model_label_migration" in fp.name:
            continue
        yield fp


def main() -> None:
    total_parse_errors = 0
    total_duplicate_triples = 0
    total_conflicting_duplicates = 0

    for dname in DIRS:
        d = ROOT / "data" / "results" / dname
        if not d.exists():
            continue
        print(f"\n{'='*70}\n{dname}/\n{'='*70}")

        # key -> list of (file, lineno, row)
        rows_by_key: dict[tuple, list] = defaultdict(list)
        parse_errors: list[tuple] = []
        file_row_counts: dict[str, int] = {}

        for fp in iter_files(d):
            n_lines = 0
            with fp.open(encoding="utf-8", errors="strict") as f:
                for lineno, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    n_lines += 1
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError as e:
                        parse_errors.append((fp.name, lineno, str(e), line[:200]))
                        continue
                    label = row.get("model_label") or row.get("model")
                    key = (row.get("template_id"), row.get("instance_seed"), label)
                    rows_by_key[key].append((fp.name, lineno, row))
            file_row_counts[fp.name] = n_lines

        print(f"Files: {len(file_row_counts)} | Total data lines: {sum(file_row_counts.values())}")

        if parse_errors:
            print(f"\n*** {len(parse_errors)} STRICT-PARSE FAILURES ***")
            for fn, lineno, err, snippet in parse_errors:
                print(f"  {fn}:{lineno}: {err}\n    {snippet!r}")
        else:
            print("Strict parse: OK (0 failures)")
        total_parse_errors += len(parse_errors)

        dups = {k: v for k, v in rows_by_key.items() if len(v) > 1}
        print(f"\nDistinct (template_id, instance_seed, model_label) keys: {len(rows_by_key)}")
        print(f"Duplicate keys (appear >1x): {len(dups)}")
        total_duplicate_triples += len(dups)

        conflicting = 0
        for key, occurrences in dups.items():
            # "content" = the fields that matter for aggregation: tier,
            # exec_rate, mutation_score, baseline_passed. If these differ
            # across occurrences of the same key, it's a genuine conflict
            # (not just the same value written twice), and load_records()'s
            # dedup (keeps latest by timestamp) is silently picking a winner.
            contents = set()
            for fn, lineno, row in occurrences:
                sig = (row.get("tier"), row.get("exec_rate"),
                       row.get("mutation_score"), row.get("baseline_passed"))
                contents.add(sig)
            status = "CONFLICTING (values differ)" if len(contents) > 1 else "identical content"
            if len(contents) > 1:
                conflicting += 1
            locs = ", ".join(f"{fn}:{lineno}" for fn, lineno, _ in occurrences)
            print(f"  {key}: {len(occurrences)}x [{status}] -- {locs}")
        total_conflicting_duplicates += conflicting

        if not dups:
            print("(no duplicate triples)")

    print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
    print(f"Total strict-parse failures across all directories: {total_parse_errors}")
    print(f"Total duplicate (template_id, instance_seed, model_label) triples: {total_duplicate_triples}")
    print(f"  of which content-conflicting (not just repeated): {total_conflicting_duplicates}")


if __name__ == "__main__":
    main()
