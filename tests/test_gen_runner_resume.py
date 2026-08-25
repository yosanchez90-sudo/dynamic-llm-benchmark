"""Regression tests for src/eval/test_gen_runner.py's resume-file matching.

2026-07-26 race audit: _find_resume_file matched on (model_label, benchmark,
prompting_condition, instantiation_id) only -- NOT tier. Two Dynamic configs
for the same (model, instantiation) but different tier sets (e.g. L1L2 vs
L3L4, this project's standard tier-group split) were therefore
indistinguishable to the matcher. Confirmed via real job logs (2026-07-14,
jobs 9376519/9376524 for claude-haiku-4-5 inst4) that a later L1L2 retry job
(9468234, 2026-07-23) resumed into the L3L4 job's own output file, and a
later L3L4 retry (9468238) did the same again -- producing duplicate,
sometimes content-conflicting rows for the same (template_id, instance_seed)
across the two tier groups' files. See CLAUDE.md's isolation/matcher note
and data/raw/ult_plt/PROVENANCE.md-adjacent audit output for the full trail.
No data was lost (coverage_matrix.py's set-based check shows every in-scope
cell complete) and src/Analysis/loader.py's existing timestamp-based dedup
already resolves the duplicates for analysis -- this test guards the root
cause so future runs don't depend on manual job sequencing to avoid it.
"""
from __future__ import annotations

import json

import pytest

from src.eval.test_gen_runner import _find_resume_file, _tier_signature

pytestmark = pytest.mark.torch


def test_tier_signature_dynamic_config():
    assert _tier_signature({"tiers": ["L1", "L2"]}) == "L1L2"
    assert _tier_signature({"tiers": ["L3", "L4"]}) == "L3L4"


def test_tier_signature_empty_for_ult_plt():
    # ULT/PLT configs have no "tiers" key at all.
    assert _tier_signature({"benchmark": "ult"}) == ""


def _write(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def test_resume_does_not_cross_tier_groups(tmp_path):
    """The exact bug: an L3L4 config's output file must not be picked up
    as the resume target for an L1L2 config on the same (model, instantiation),
    even though both target instantiation_id="4"."""
    l3l4_file = tmp_path / "modelX__dynamic__zero_shot__inst4__tiersL3L4__20260714T141409.jsonl"
    _write(l3l4_file, [
        {"template_id": "L3-bucket-001", "instance_seed": 4101},
    ])

    resume_path, done = _find_resume_file(
        tmp_path, "modelX", "dynamic", "zero_shot", "4",
        n_shards=1, shard_id=0, tier_sig="L1L2",
    )

    assert resume_path is None
    assert done == set()


def test_resume_matches_same_tier_group(tmp_path):
    l1l2_file = tmp_path / "modelX__dynamic__zero_shot__inst4__tiersL1L2__20260714T141406.jsonl"
    _write(l1l2_file, [
        {"template_id": "L1-arithmetic-001", "instance_seed": 4101},
        {"template_id": "L1-arithmetic-001", "instance_seed": 4102},
    ])

    resume_path, done = _find_resume_file(
        tmp_path, "modelX", "dynamic", "zero_shot", "4",
        n_shards=1, shard_id=0, tier_sig="L1L2",
    )

    assert resume_path == l1l2_file
    assert done == {("L1-arithmetic-001", 4101), ("L1-arithmetic-001", 4102)}


def test_resume_backward_compatible_when_tier_sig_empty(tmp_path):
    # ULT/PLT (and any pre-fix file with no __tiers segment) still resume
    # correctly when tier_sig="" (the default).
    ult_file = tmp_path / "modelX__ult__zero_shot__instcore_400__20260713T123923.jsonl"
    _write(ult_file, [{"template_id": "ULT-1", "instance_seed": 1}])

    resume_path, done = _find_resume_file(
        tmp_path, "modelX", "ult", "zero_shot", "core_400",
        n_shards=1, shard_id=0,
    )

    assert resume_path == ult_file
    assert done == {("ULT-1", 1)}
