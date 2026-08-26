"""Unit tests for src/Analysis/stability.py using small synthetic frames —
no dependency on real result files, so these run anywhere."""
from __future__ import annotations

import pandas as pd
import pytest

from src.Analysis.stability import (
    mut_at_k, pairwise_kendall_tau, stable_mut_at_k,
)


def _row(model, inst, mutation_score):
    return {"model_label": model, "instantiation_id": inst, "mutation_score": mutation_score}


def test_mut_at_k_excludes_gate_failures():
    df = pd.DataFrame([
        _row("m1", "1", 1.0),
        _row("m1", "1", 0.5),
        _row("m1", "1", None),  # Exec@K/baseline gate failed, excluded, not zero
    ])
    agg = mut_at_k(df, ["model_label", "instantiation_id"])
    row = agg.iloc[0]
    assert row["n_scored"] == 2
    assert row["n_total"] == 3
    assert row["mut_at_k"] == pytest.approx(0.75)


def test_stable_mut_at_k_mean_and_sd():
    df = pd.DataFrame([
        _row("m1", "1", 0.8), _row("m1", "1", 0.8),
        _row("m1", "2", 0.6), _row("m1", "2", 0.6),
        _row("m1", "3", 1.0), _row("m1", "3", 1.0),
    ])
    out = stable_mut_at_k(df)
    row = out.iloc[0]
    assert row["n_instantiations"] == 3
    assert row["stable_mut_at_k"] == pytest.approx((0.8 + 0.6 + 1.0) / 3)
    assert row["sd_mut_at_k"] == pytest.approx(pd.Series([0.8, 0.6, 1.0]).std())


def test_stable_mut_at_k_excludes_instantiations_with_no_scorable_problems():
    df = pd.DataFrame([
        _row("m1", "1", 0.8),
        _row("m1", "2", None),  # entirely gated out, must not count as 0
    ])
    out = stable_mut_at_k(df)
    row = out.iloc[0]
    assert row["n_instantiations"] == 1
    assert row["stable_mut_at_k"] == pytest.approx(0.8)


def test_stable_mut_at_k_by_tier_facet():
    df = pd.DataFrame([
        {**_row("m1", "1", 0.9), "tier": "L1"},
        {**_row("m1", "1", 0.3), "tier": "L2"},
        {**_row("m1", "2", 0.9), "tier": "L1"},
        {**_row("m1", "2", 0.3), "tier": "L2"},
    ])
    out = stable_mut_at_k(df, extra_group_cols=("tier",))
    by_tier = dict(zip(out["tier"], out["stable_mut_at_k"]))
    assert by_tier["L1"] == pytest.approx(0.9)
    assert by_tier["L2"] == pytest.approx(0.3)


def test_pairwise_kendall_tau_perfect_agreement():
    df = pd.DataFrame([
        _row("a", "1", 0.9), _row("b", "1", 0.5), _row("c", "1", 0.1),
        _row("a", "2", 0.8), _row("b", "2", 0.4), _row("c", "2", 0.2),
    ])
    out = pairwise_kendall_tau(df)
    assert len(out) == 1
    assert out.iloc[0]["n_models"] == 3
    assert out.iloc[0]["tau"] == pytest.approx(1.0)


def test_pairwise_kendall_tau_perfect_disagreement():
    df = pd.DataFrame([
        _row("a", "1", 0.9), _row("b", "1", 0.5), _row("c", "1", 0.1),
        _row("a", "2", 0.1), _row("b", "2", 0.5), _row("c", "2", 0.9),
    ])
    out = pairwise_kendall_tau(df)
    assert out.iloc[0]["tau"] == pytest.approx(-1.0)


def test_pairwise_kendall_tau_skips_pairs_with_too_few_models():
    df = pd.DataFrame([
        _row("a", "1", 0.9),
        _row("a", "2", 0.1),  # only one model qualifies in both instantiations
    ])
    out = pairwise_kendall_tau(df)
    assert out.iloc[0]["n_models"] == 1
    assert pd.isna(out.iloc[0]["tau"])


def test_stable_mut_at_k_coverage_adjust_scales_by_scored_fraction():
    """coverage_adjust=True: mut_at_k x (n_scored/n_total), not raw mut_at_k --
    2 of 4 rows gated out (None) each instantiation -> adjusted = 0.8*0.5=0.4."""
    df = pd.DataFrame([
        _row("m1", "1", 0.8), _row("m1", "1", None), _row("m1", "1", None), _row("m1", "1", 0.8),
        _row("m1", "2", 0.8), _row("m1", "2", None), _row("m1", "2", None), _row("m1", "2", 0.8),
    ])
    raw = stable_mut_at_k(df)
    adjusted = stable_mut_at_k(df, coverage_adjust=True)
    assert raw.iloc[0]["stable_mut_at_k"] == pytest.approx(0.8)
    assert adjusted.iloc[0]["stable_mut_at_k"] == pytest.approx(0.4)


def test_mut_at_k_generalizes_to_exec_rate_never_conditioned():
    """exec_rate is never None. metric_col='exec_rate' should reduce to a
    plain mean over ALL rows, n_scored == n_total always."""
    df = pd.DataFrame([
        {"model_label": "m1", "instantiation_id": "1", "exec_rate": 1.0, "mutation_score": None},
        {"model_label": "m1", "instantiation_id": "1", "exec_rate": 0.0, "mutation_score": None},
    ])
    agg = mut_at_k(df, ["model_label", "instantiation_id"], metric_col="exec_rate")
    row = agg.iloc[0]
    assert row["n_scored"] == 2
    assert row["n_total"] == 2
    assert row["mut_at_k"] == pytest.approx(0.5)


def test_mut_at_k_generalizes_to_baseline_passed_bool_cast():
    """baseline_passed is a bool column, must average correctly (True=1,
    False=0), not raise or silently misbehave on non-numeric dtype."""
    df = pd.DataFrame([
        {"model_label": "m1", "instantiation_id": "1", "baseline_passed": True},
        {"model_label": "m1", "instantiation_id": "1", "baseline_passed": True},
        {"model_label": "m1", "instantiation_id": "1", "baseline_passed": False},
        {"model_label": "m1", "instantiation_id": "1", "baseline_passed": False},
    ])
    agg = mut_at_k(df, ["model_label", "instantiation_id"], metric_col="baseline_passed")
    assert agg.iloc[0]["mut_at_k"] == pytest.approx(0.5)


def test_stable_mut_at_k_metric_col_propagates():
    df = pd.DataFrame([
        {"model_label": "m1", "instantiation_id": "1", "exec_rate": 1.0},
        {"model_label": "m1", "instantiation_id": "1", "exec_rate": 0.0},
        {"model_label": "m1", "instantiation_id": "2", "exec_rate": 1.0},
        {"model_label": "m1", "instantiation_id": "2", "exec_rate": 1.0},
    ])
    out = stable_mut_at_k(df, metric_col="exec_rate")
    assert out.iloc[0]["stable_mut_at_k"] == pytest.approx((0.5 + 1.0) / 2)


def test_coverage_adjust_rejects_non_default_metric_col():
    df = pd.DataFrame([{"model_label": "m1", "instantiation_id": "1", "exec_rate": 1.0}])
    with pytest.raises(ValueError):
        stable_mut_at_k(df, coverage_adjust=True, metric_col="exec_rate")
    with pytest.raises(ValueError):
        pairwise_kendall_tau(df, coverage_adjust=True, metric_col="exec_rate")


def test_pairwise_kendall_tau_coverage_adjust_can_change_ranking():
    """Raw Mut@K ties b/c ahead of a; coverage-adjusting by a much lower
    baseline_pass_rate for b flips the ranking, proves coverage_adjust
    actually changes which score drives the rank correlation, not just a
    uniform rescale."""
    df = pd.DataFrame([
        _row("a", "1", 0.9), _row("a", "1", 0.9),
        _row("b", "1", 0.95), _row("b", "1", None), _row("b", "1", None), _row("b", "1", None),
        _row("a", "2", 0.8), _row("a", "2", 0.8),
        _row("b", "2", 0.9), _row("b", "2", None), _row("b", "2", None), _row("b", "2", None),
    ])
    raw = pairwise_kendall_tau(df)
    adjusted = pairwise_kendall_tau(df, coverage_adjust=True)
    assert raw.iloc[0]["tau"] == pytest.approx(1.0)   # b > a in both instantiations, raw
    assert adjusted.iloc[0]["n_models"] == 2
    # adjusted: a=0.9*1.0=0.9 vs b=0.95*0.25=0.2375 (inst1); a=0.8 vs b=0.225 (inst2) -> a > b now
    assert adjusted.iloc[0]["tau"] == pytest.approx(1.0)  # still perfectly consistent, just a new ranking direction
    adj_scores = mut_at_k(df, ["model_label", "instantiation_id"])
    adj_scores = adj_scores.assign(cov=adj_scores["mut_at_k"] * adj_scores["n_scored"] / adj_scores["n_total"])
    inst1 = adj_scores[adj_scores["instantiation_id"] == "1"].set_index("model_label")["cov"]
    assert inst1["a"] > inst1["b"]  # ranking flipped vs raw (b > a)
