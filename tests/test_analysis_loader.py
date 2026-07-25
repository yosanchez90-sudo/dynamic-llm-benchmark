"""Unit tests for src/Analysis/loader.py's dedup behavior.

Regression test for the 2026-07-25 audit finding: a stale partial-tier
retry file left in data/results/dynamic/ alongside its complete replacement
(seen for claude-sonnet-4-6/claude-haiku-4-5 inst1-4) was silently
double-counted by load_records, since it had no dedup logic at all — biasing
any aggregate (StableMut@K, Kendall tau) that doesn't filter by a single
tier. Fixed by deduping on the natural key, keeping the newest row by
timestamp.
"""
from __future__ import annotations

import json

from src.Analysis.loader import load_records


def _write(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _record(**overrides):
    base = {
        "model": "claude-sonnet-4-6", "model_revision": "claude-sonnet-4-6",
        "model_label": "claude-sonnet-4-6", "instantiation_id": "1",
        "template_id": "L3-bucket-001", "instance_seed": 1101, "tier": "L3",
        "K": 1, "prompting_condition": "zero_shot", "benchmark": "dynamic",
        "mutation_score": 1.0, "exec_rate": 1.0, "timestamp": "2026-07-14T14:10:33+00:00",
    }
    base.update(overrides)
    return base


def test_stale_rerun_is_superseded_by_newer_row(tmp_path):
    # Older, stale attempt (kept on disk per the append-only convention).
    _write(tmp_path / "old.jsonl", [_record(mutation_score=1.0, timestamp="2026-07-14T14:10:33+00:00")])
    # Newer, complete rerun of the SAME (model, instantiation, template, seed, tier).
    _write(tmp_path / "new.jsonl", [_record(mutation_score=0.5, timestamp="2026-07-23T13:35:58+00:00")])

    df = load_records(tmp_path, benchmark="dynamic")

    assert len(df) == 1
    assert df.iloc[0]["mutation_score"] == 0.5
    assert df.iloc[0]["source_file"] == "new.jsonl"


def test_distinct_problems_are_not_deduped(tmp_path):
    _write(tmp_path / "a.jsonl", [
        _record(template_id="L3-bucket-001", instance_seed=1101),
        _record(template_id="L3-bucket-002", instance_seed=1102),
    ])

    df = load_records(tmp_path, benchmark="dynamic")

    assert len(df) == 2
