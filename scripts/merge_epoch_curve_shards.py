"""Merge Part G / G2 shard CSVs (see submit_epoch_curve_shards.py) into the
per-condition epoch_perf_<name>.csv files, after verifying every expected
(epoch, instantiation, draw) triple is present exactly once across that
condition's shards.

Append-only: never overwrites an existing epoch_perf_<name>.csv row-for-row
-- it reads what's already there (if anything), skips triples already
present, and appends the rest. Refuses to merge a condition whose shards are
incomplete (missing or duplicate triples) so a partial run can never silently
produce a partial-looking-complete curve.

Usage:
    python scripts/merge_epoch_curve_shards.py --manifest data/results/finetune_rebuild/shards/manifests/manifest_<ts>.csv
    python scripts/merge_epoch_curve_shards.py --manifest <path> --check-only   # verify without writing
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NON_FINAL_EPOCHS = [3, 5, 10, 15, 20, 25]
SAMPLING_SEEDS = [42, 43, 44]
INSTANTIATIONS = [1, 2, 3]


def expected_triples() -> set[tuple[int, int, str]]:
    triples: set[tuple[int, int, str]] = set()
    for inst in INSTANTIATIONS:
        triples.add((0, inst, "greedy"))
        triples.add((1, inst, "greedy"))
        for ep in NON_FINAL_EPOCHS:
            triples.add((ep, inst, "greedy"))
        triples.add((30, inst, "greedy"))
        for seed in SAMPLING_SEEDS:
            triples.add((30, inst, f"sampling_seed{seed}"))
    return triples


def load_manifest(path: Path) -> dict[str, list[Path]]:
    by_condition: dict[str, list[Path]] = defaultdict(list)
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            by_condition[row["config_name"]].append(ROOT / row["out_path"])
    return by_condition


def read_rows(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        return []
    with csv_path.open(newline="") as f:
        return list(csv.DictReader(f))


def verify_condition(config_name: str, shard_paths: list[Path]) -> tuple[bool, list[dict], list[str]]:
    """Returns (ok, rows, problems)."""
    problems: list[str] = []
    all_rows: list[dict] = []
    seen: set[tuple[int, int, str]] = set()

    for sp in shard_paths:
        if not sp.exists():
            problems.append(f"missing shard file: {sp}")
            continue
        rows = read_rows(sp)
        if not rows:
            problems.append(f"empty shard file: {sp}")
            continue
        for row in rows:
            triple = (int(row["epoch"]), int(row["instantiation"]), row["draw"])
            if triple in seen:
                problems.append(f"duplicate triple {triple} in {sp} (also seen in another shard)")
                continue
            seen.add(triple)
            all_rows.append(row)

    missing = expected_triples() - seen
    if missing:
        problems.append(f"missing {len(missing)} expected triples: {sorted(missing)}")

    extra = seen - expected_triples()
    if extra:
        problems.append(f"unexpected triples not in the plan: {sorted(extra)}")

    return (len(problems) == 0), all_rows, problems


def merge_into_target(config_name: str, rows: list[dict]) -> Path:
    target = ROOT / f"data/results/finetune_rebuild/epoch_perf_{config_name}.csv"
    existing_rows = read_rows(target)
    existing_triples = {
        (int(r["epoch"]), int(r["instantiation"]), r["draw"]) for r in existing_rows
    }

    fieldnames = list(rows[0].keys())
    new_rows = [r for r in rows if (int(r["epoch"]), int(r["instantiation"]), r["draw"]) not in existing_triples]

    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        with target.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(new_rows)
    else:
        with target.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerows(new_rows)

    print(f"  {target.relative_to(ROOT)}: {len(existing_rows)} existing + {len(new_rows)} appended "
          f"= {len(existing_rows) + len(new_rows)} rows")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true",
                        help="Verify completeness without writing the merged CSV")
    args = parser.parse_args()

    by_condition = load_manifest(args.manifest)
    all_ok = True

    for config_name, shard_paths in sorted(by_condition.items()):
        print(f"\n{config_name}: {len(shard_paths)} shards")
        ok, rows, problems = verify_condition(config_name, shard_paths)
        if not ok:
            all_ok = False
            print(f"  INCOMPLETE — not merging:")
            for p in problems:
                print(f"    - {p}")
            continue

        print(f"  complete: {len(rows)} rows, all {len(expected_triples())} expected triples present")
        if not args.check_only:
            merge_into_target(config_name, rows)

    print()
    if all_ok:
        print("All conditions complete." + (" (check-only, nothing written)" if args.check_only else ""))
    else:
        print("Some conditions incomplete — re-run their missing shards, then re-run this script.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
