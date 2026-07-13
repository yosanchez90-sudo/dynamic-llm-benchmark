"""Unit tests for src/data/ult_plt.py using small synthetic ULT/PLT-shaped
fixtures — fast, deterministic, and independent of the real 48MB vendored
files (see data/raw/ult_plt/PROVENANCE.md for those).
"""
from __future__ import annotations

import json

import pytest

from src.data import ult_plt

# CC>=8 needs real branching; these bodies are hand-picked so their CC under
# this project's own compute_cc() lands on the intended side of the CC_MIN=8
# threshold (see PROVENANCE.md for why we recompute rather than trust the
# vendored `cyclomatic_complexity` field).
HIGH_CC_SOURCE = """def high_cc(a, b, c, d, e, f, g, h):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            if g:
                                if h:
                                    return 1
    return 0
"""

LOW_CC_SOURCE = """def low_cc(a, b):
    return a + b
"""

MULTI_DEF_HIGH_CC_SOURCE = """class Helper:
    def __init__(self, x):
        self.x = x + 1

def high_cc_with_helper(a, b, c, d, e, f, g, h):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            if g:
                                if h:
                                    return 1
    return 0
"""


def _write(path, records):
    path.write_text(json.dumps(records))


@pytest.fixture
def fixture_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(ult_plt, "_DATA_DIR", tmp_path)
    return tmp_path


def test_cc_filter_drops_low_complexity_records(fixture_dir):
    _write(fixture_dir / "ULT.jsonl", [
        {"task_id": "1", "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p1"},
        {"task_id": "2", "func_name": "low_cc", "code": LOW_CC_SOURCE, "prompt": "p2"},
    ])
    problems = ult_plt.load("ult")
    assert len(problems) == 1
    assert problems[0].fn_name == "high_cc"
    assert problems[0].tier == "L4"


def test_template_id_prefixed_by_benchmark(fixture_dir):
    _write(fixture_dir / "ULT.jsonl", [
        {"task_id": "42", "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"},
    ])
    problems = ult_plt.load("ult")
    assert problems[0].template_id == "ULT-42"
    assert problems[0].instance_seed == 42
    assert problems[0].benchmark == "ult"


def test_plt_excludes_ult_overlap_by_default(fixture_dir):
    _write(fixture_dir / "ULT.jsonl", [
        {"task_id": "1", "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"},
    ])
    _write(fixture_dir / "PLT.jsonl", [
        {"task_id": "1", "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"},
        {"task_id": "2", "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"},
    ])
    excluded = ult_plt.load("plt")
    assert {p.template_id for p in excluded} == {"PLT-2"}

    included = ult_plt.load("plt", exclude_ult_overlap=False)
    assert {p.template_id for p in included} == {"PLT-1", "PLT-2"}


def test_invalid_benchmark_raises(fixture_dir):
    with pytest.raises(ValueError):
        ult_plt.load("dynamic")


def test_mutation_scoped_away_from_helper_code(fixture_dir):
    _write(fixture_dir / "ULT.jsonl", [
        {"task_id": "1", "func_name": "high_cc_with_helper",
         "code": MULTI_DEF_HIGH_CC_SOURCE, "prompt": "p"},
    ])
    problems = ult_plt.load("ult")
    assert len(problems) == 1
    for m in problems[0].mutants:
        assert "self.x = x + 1" in m.source  # helper untouched by every mutant


def test_cc_lookup_matches_loaded_tier_filter(fixture_dir):
    _write(fixture_dir / "ULT.jsonl", [
        {"task_id": "1", "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"},
        {"task_id": "2", "func_name": "low_cc", "code": LOW_CC_SOURCE, "prompt": "p"},
    ])
    ccs = ult_plt.cc_lookup("ult")
    assert ccs["ULT-1"] >= ult_plt.CC_MIN
    assert ccs["ULT-2"] < ult_plt.CC_MIN
    loaded_ids = {p.template_id for p in ult_plt.load("ult")}
    assert loaded_ids == {tid for tid, cc in ccs.items() if cc >= ult_plt.CC_MIN}


def test_max_n_subsample_does_not_exceed_pool_or_request(fixture_dir):
    records = [
        {"task_id": str(i), "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"}
        for i in range(1, 11)
    ]
    _write(fixture_dir / "ULT.jsonl", records)
    problems = ult_plt.load("ult", max_n=4, sample_seed=1)
    assert 0 < len(problems) <= 4
    assert len(problems) == len(set(p.template_id for p in problems))


def test_task_ids_restricts_to_exactly_those_ids(fixture_dir):
    records = [
        {"task_id": str(i), "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"}
        for i in range(1, 11)
    ]
    _write(fixture_dir / "ULT.jsonl", records)
    problems = ult_plt.load("ult", task_ids={"2", "5", "9"})
    assert {p.template_id for p in problems} == {"ULT-2", "ULT-5", "ULT-9"}


def test_task_ids_ignores_max_n(fixture_dir):
    records = [
        {"task_id": str(i), "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"}
        for i in range(1, 11)
    ]
    _write(fixture_dir / "ULT.jsonl", records)
    problems = ult_plt.load("ult", max_n=1, task_ids={"2", "5", "9"})
    assert len(problems) == 3


def test_task_ids_raises_on_missing_id(fixture_dir):
    _write(fixture_dir / "ULT.jsonl", [
        {"task_id": "1", "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"},
    ])
    with pytest.raises(ValueError, match="data drift"):
        ult_plt.load("ult", task_ids={"1", "999"})


def test_task_ids_raises_on_cc_filtered_id(fixture_dir):
    _write(fixture_dir / "ULT.jsonl", [
        {"task_id": "1", "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"},
        {"task_id": "2", "func_name": "low_cc", "code": LOW_CC_SOURCE, "prompt": "p"},
    ])
    with pytest.raises(ValueError, match="data drift"):
        ult_plt.load("ult", task_ids={"1", "2"})  # "2" fails CC_MIN, not in pool


def test_load_manifest_subset_reads_pinned_tag(fixture_dir, tmp_path):
    ult_records = [
        {"task_id": str(i), "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"}
        for i in range(1, 11)
    ]
    # Distinct task_id range so PLT has no ULT overlap to exclude.
    plt_records = [
        {"task_id": str(i), "func_name": "high_cc", "code": HIGH_CC_SOURCE, "prompt": "p"}
        for i in range(101, 111)
    ]
    _write(fixture_dir / "ULT.jsonl", ult_records)
    _write(fixture_dir / "PLT.jsonl", plt_records)

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "core_400": {
            "ult": {"problems": [{"task_id": "3"}, {"task_id": "7"}]},
            "plt": {"problems": [{"task_id": "105"}]},
        },
    }))

    ult_problems = ult_plt.load_manifest_subset("ult", "core_400", manifest_path=manifest_path)
    assert {p.template_id for p in ult_problems} == {"ULT-3", "ULT-7"}

    plt_problems = ult_plt.load_manifest_subset("plt", "core_400", manifest_path=manifest_path)
    assert {p.template_id for p in plt_problems} == {"PLT-105"}
