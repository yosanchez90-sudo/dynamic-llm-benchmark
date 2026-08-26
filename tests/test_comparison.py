"""Unit tests for src/Analysis/comparison.py using synthetic frames with
known ground-truth values, no dependency on real ULT/PLT/Dynamic results.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from src.Analysis.comparison import (
    coverage_stats_table,
    dynamic_l4_for_model,
    load_cc_bands,
    matched_cc_table,
    paired_model_table,
    paired_wilcoxon,
)


def _rows(model_label: str, tier: str, scores: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "model_label": [model_label] * len(scores),
        "tier": [tier] * len(scores),
        "mutation_score": scores,
    })


def test_dynamic_l4_for_model_filters_both_model_and_tier():
    df = pd.concat([
        _rows("m1", "L1", [0.1, 0.2]),
        _rows("m1", "L4", [0.5, 0.6]),
        _rows("m2", "L4", [0.9]),
    ])
    out = dynamic_l4_for_model(df, "m1")
    assert len(out) == 2
    assert set(out["mutation_score"]) == {0.5, 0.6}


def test_paired_model_table_drops_models_missing_from_either_side():
    dynamic = pd.concat([_rows("m1", "L4", [0.4, 0.6]), _rows("m2", "L4", [0.2])])
    ult = pd.concat([_rows("m1", "L4", [0.5, 0.7])])  # m2 missing from ult
    paired = paired_model_table(dynamic, ult, label_a="dynamic", label_b="ult")
    assert list(paired["model_label"]) == ["m1"]
    assert paired.iloc[0]["dynamic"] == pytest.approx(0.5)
    assert paired.iloc[0]["ult"] == pytest.approx(0.6)


def test_paired_model_table_ignores_nan_mutation_scores():
    dynamic = pd.concat([_rows("m1", "L4", [0.4, 0.6]), _rows("m1", "L4", [float("nan")])])
    ult = _rows("m1", "L4", [0.5])
    paired = paired_model_table(dynamic, ult, label_a="dynamic", label_b="ult")
    assert paired.iloc[0]["dynamic"] == pytest.approx(0.5)  # mean of [0.4, 0.6], NaN excluded


def test_coverage_stats_table_reports_n_total_n_defined_and_bp_rate():
    dynamic = pd.concat([
        _rows("m1", "L4", [0.4, 0.6, float("nan")]),  # 2/3 defined
        _rows("m2", "L4", [0.2]),                       # 1/1 defined
    ])
    stats = coverage_stats_table(dynamic).set_index("model_label")
    assert stats.loc["m1", "n_total"] == 3
    assert stats.loc["m1", "n_defined"] == 2
    assert stats.loc["m1", "baseline_pass_rate"] == pytest.approx(2 / 3)
    assert stats.loc["m2", "n_total"] == 1
    assert stats.loc["m2", "n_defined"] == 1
    assert stats.loc["m2", "baseline_pass_rate"] == pytest.approx(1.0)


def test_coverage_stats_table_zero_defined_gives_zero_rate_not_nan():
    dynamic = _rows("m1", "L4", [float("nan"), float("nan")])
    stats = coverage_stats_table(dynamic).set_index("model_label")
    assert stats.loc["m1", "n_defined"] == 0
    assert stats.loc["m1", "baseline_pass_rate"] == pytest.approx(0.0)


def test_paired_wilcoxon_fewer_than_two_pairs_returns_none_stats():
    paired = pd.DataFrame({"model_label": ["m1"], "a": [0.5], "b": [0.6]})
    result = paired_wilcoxon(paired, label_a="a", label_b="b")
    assert result.n_pairs == 1
    assert result.statistic is None
    assert result.p_value is None
    assert result.effect_r is None


def test_paired_wilcoxon_all_b_greater_gives_effect_r_one():
    # b consistently exceeds a for every model -> perfect positive rank-biserial.
    paired = pd.DataFrame({
        "model_label": ["m1", "m2", "m3", "m4"],
        "a": [0.1, 0.2, 0.3, 0.4],
        "b": [0.5, 0.6, 0.7, 0.8],
    })
    result = paired_wilcoxon(paired, label_a="a", label_b="b", n_boot=200, seed=1)
    assert result.n_pairs == 4
    assert result.effect_r == pytest.approx(1.0)
    assert result.effect_ci_lo == pytest.approx(1.0, abs=1e-9)
    assert result.effect_ci_hi == pytest.approx(1.0, abs=1e-9)
    assert result.mean_a == pytest.approx(0.25)
    assert result.mean_b == pytest.approx(0.65)


def test_paired_wilcoxon_identical_sides_gives_p_one_and_zero_effect():
    paired = pd.DataFrame({
        "model_label": ["m1", "m2", "m3"],
        "a": [0.3, 0.4, 0.5],
        "b": [0.3, 0.4, 0.5],
    })
    result = paired_wilcoxon(paired, label_a="a", label_b="b")
    assert result.p_value == pytest.approx(1.0)
    assert result.effect_r == pytest.approx(0.0)


def test_load_cc_bands_reads_manifest_tag(tmp_path):
    manifest = {
        "core_400": {
            "ult": {"problems": [
                {"template_id": "ULT-1", "band": "CC8-9"},
                {"template_id": "ULT-2", "band": "CC16+"},
            ]},
            "plt": {"problems": [
                {"template_id": "PLT-5", "band": "CC10-11"},
            ]},
        },
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    bands = load_cc_bands("ult", tag="core_400", manifest_path=path)
    assert bands == {"ULT-1": "CC8-9", "ULT-2": "CC16+"}


def test_matched_cc_table_computes_per_band_delta():
    ult = pd.DataFrame({
        "template_id": ["ULT-1", "ULT-2"],
        "mutation_score": [0.3, 0.5],
    })
    plt = pd.DataFrame({
        "template_id": ["PLT-1", "PLT-2"],
        "mutation_score": [0.6, 0.5],
    })
    band_ult = {"ULT-1": "CC8-9", "ULT-2": "CC16+"}
    band_plt = {"PLT-1": "CC8-9", "PLT-2": "CC16+"}
    table = matched_cc_table(ult, plt, band_ult, band_plt)
    row = table.set_index("band").loc["CC8-9"]
    assert row["mean_ult"] == pytest.approx(0.3)
    assert row["mean_plt"] == pytest.approx(0.6)
    assert row["delta_plt_minus_ult"] == pytest.approx(0.3)


def test_matched_cc_table_drops_bands_missing_from_either_side():
    ult = pd.DataFrame({"template_id": ["ULT-1"], "mutation_score": [0.3]})
    plt = pd.DataFrame({"template_id": ["PLT-1"], "mutation_score": [0.6]})
    band_ult = {"ULT-1": "CC8-9"}
    band_plt = {"PLT-1": "CC16+"}  # disjoint bands -> no overlap
    table = matched_cc_table(ult, plt, band_ult, band_plt)
    assert table.empty
    assert list(table.columns) == ["band", "mean_ult", "n_ult", "mean_plt", "n_plt", "delta_plt_minus_ult"]
