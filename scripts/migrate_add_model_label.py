"""One-off migration: stamp model_label into existing
data/results/{dynamic,smoke}/*.jsonl files written before it became a
first-class TestGenRecord field (2026-07-09). Uses the exact same
filename-derivation logic src/Analysis/loader.py already used as its
fallback (_model_label_from_filename), same algorithm, just applied once
and written to disk instead of recomputed on every load.

adapter_path/adapter_hash are NOT backfilled here: we don't
have provable evidence of which exact adapter snapshot was loaded at
generation time for these older runs (the current data/finetune/*/adapter_
final files could differ from what was live back then), and
stamping an unverifiable value into a result record would be worse than
leaving it null. New runs get these fields natively via src/models/local.py.

Idempotent: skips a file if every record already has a non-empty
model_label. Backs up each file (byte-identical copy) before writing, then
rewrites in place and verifies line-count and every-other-field parity
before the rewrite is allowed to replace the original. This is a
metadata-only backfill of a value already fully determined by the
filename, not a re-scoring, so treating it as append-only-file-plus-verified
-backup (instead of skipping entirely or scattering parallel copies) keeps
downstream code pointed at one canonical file per run.

Usage:
    python scripts/migrate_add_model_label.py            # dry run, report only
    python scripts/migrate_add_model_label.py --apply     # actually write
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.Analysis.loader import _model_label_from_filename  # noqa: E402

RESULT_DIRS = [ROOT / "data/results/dynamic", ROOT / "data/results/smoke"]
BACKUP_SUFFIX = ".pre_model_label_migration.bak"


def migrate_file(path: Path, apply: bool) -> str:
    lines = path.read_text().splitlines()
    records = [json.loads(l) for l in lines if l.strip()]
    if not records:
        return "SKIP (empty file)"

    if all(r.get("model_label") for r in records):
        return "SKIP (already migrated)"

    label = _model_label_from_filename(path)
    new_records = []
    for r in records:
        r = dict(r)  # copy; preserves existing key order, new keys land at the end
        if not r.get("model_label"):
            r["model_label"] = label
        r.setdefault("adapter_path", None)
        r.setdefault("adapter_hash", None)
        new_records.append(r)

    if not apply:
        return f"WOULD migrate {len(records)} records -> model_label={label!r}"

    backup_path = path.parent / (path.name + BACKUP_SUFFIX)
    if not backup_path.exists():
        shutil.copy2(path, backup_path)

    new_text = "\n".join(json.dumps(r, ensure_ascii=False) for r in new_records) + "\n"
    tmp_path = path.parent / (path.name + ".tmp")
    tmp_path.write_text(new_text)

    # Verify before replacing: same record count, every field other than the
    # three we're adding is byte-for-byte unchanged.
    verify_records = [json.loads(l) for l in tmp_path.read_text().splitlines() if l.strip()]
    assert len(verify_records) == len(records), f"record count changed for {path.name}!"
    added = {"model_label", "adapter_path", "adapter_hash"}
    for old, new in zip(records, verify_records):
        for k in set(old.keys()) - added:
            assert old[k] == new[k], f"field {k!r} changed for a record in {path.name}!"

    tmp_path.replace(path)
    return f"MIGRATED {len(records)} records -> model_label={label!r} (backup: {backup_path.name})"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually write changes (default: dry run, report only)")
    args = parser.parse_args()

    for result_dir in RESULT_DIRS:
        if not result_dir.exists():
            continue
        print(f"=== {result_dir.relative_to(ROOT)} ===")
        for path in sorted(result_dir.glob("*.jsonl")):
            status = migrate_file(path, args.apply)
            print(f"  {path.name}: {status}")
        print()

    if not args.apply:
        print("Dry run only — re-run with --apply to write changes.")


if __name__ == "__main__":
    main()
