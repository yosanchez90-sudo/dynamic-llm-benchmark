"""Check status of the six GPT-5/-mini batches submitted 2026-08-06 (split
per-model after the first submission attempt was rejected: OpenAI requires
one model per batch, and the originally-prepared files interleaved
gpt-5/gpt-5-mini). Exit 0 if all six are `completed`; exit 1 otherwise
(prints per-batch status either way). Read-only, never resubmits, never
scores anything.

Used by scripts/slurm/poll_openai_batches.slurm to decide whether to keep
polling or stop; also fine to run by hand any time:
    python scripts/check_openai_batch_status.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

from openai import OpenAI  # noqa: E402

STATE_FILES = [
    ("Backfill / gpt-5 (1,200 req)", "data/batches/batch_state_20260806T195356a__backfill__gpt5.json"),
    ("Backfill / gpt-5-mini (1,200 req)", "data/batches/batch_state_20260806T195356b__backfill__gpt5mini.json"),
    ("Retry / gpt-5 (6 req)", "data/batches/batch_state_20260806T195356c__retry__gpt5.json"),
    ("Retry / gpt-5-mini (1 req)", "data/batches/batch_state_20260806T195356d__retry__gpt5mini.json"),
    ("ULT/PLT / gpt-5 (800 req)", "data/batches/batch_state_20260806T195356e__ultplt__gpt5.json"),
    ("ULT/PLT / gpt-5-mini (800 req)", "data/batches/batch_state_20260806T195356f__ultplt__gpt5mini.json"),
]
# Superseded by the split above (OpenAI rejected these: "Each batch must
# contain requests for a single model". Both models were interleaved in
# one file). Rejected at validation, request_counts completed=0/0 on all
# three, no charge incurred. Kept here as a record, not polled.
_FAILED_MIXED_MODEL_STATE_FILES = [
    ("Backfill (2,400 req, FAILED mismatched_model)", "data/batches/batch_state_20260714T131617.json"),
    ("Retry (7 req, FAILED mismatched_model)", "data/batches/batch_state_20260714T131346.json"),
    ("ULT/PLT core_400 (1,600 req, FAILED mismatched_model)", "data/batches/batch_state_20260713T124543.json"),
]


def main() -> None:
    client = OpenAI()
    all_completed = True
    any_failed = False

    for label, rel_path in STATE_FILES:
        state_path = ROOT / rel_path
        state = json.loads(state_path.read_text())
        batch_id = state.get("batch_id")
        if not batch_id:
            print(f"{label}: no batch_id in state file -- not submitted?")
            all_completed = False
            continue

        b = client.batches.retrieve(batch_id)
        counts = b.request_counts
        print(f"{label}: status={b.status}  "
              f"completed={counts.completed}/{counts.total}  failed={counts.failed}"
              f"{'  errors=' + str(b.errors) if b.errors else ''}")

        # Keep the state file's cached status current for anything else that reads it.
        state["status"] = b.status
        state_path.write_text(json.dumps(state, indent=2))

        if b.status in ("failed", "expired", "cancelled"):
            any_failed = True
        if b.status != "completed":
            all_completed = False

    print()
    if any_failed:
        print("AT LEAST ONE BATCH FAILED/EXPIRED/CANCELLED -- needs attention, not a normal poll outcome.")
        sys.exit(2)
    elif all_completed:
        print("ALL THREE BATCHES COMPLETED. Ready for Phase B ingestion.")
        sys.exit(0)
    else:
        print("Still in progress.")
        sys.exit(1)


if __name__ == "__main__":
    main()
