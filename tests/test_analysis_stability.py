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
        _row("m1", "1", None),  # Exec@K/baseline gate failed — excluded, not zero
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
        _row("m1", "2", None),  # entirely gated out — must not count as 0
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
