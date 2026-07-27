"""Unit tests for src/Analysis/correlation.py using small synthetic vectors."""
from __future__ import annotations

import numpy as np
import pytest

from src.Analysis.correlation import compute_correlations


def test_perfect_positive_correlation():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
    res = compute_correlations(x, y, n_boot=200, n_perm=200, seed=0)
    assert res.n == 5
    assert res.pearson_r == pytest.approx(1.0)
    assert res.spearman_rho == pytest.approx(1.0)
    assert res.kendall_tau == pytest.approx(1.0)


def test_perfect_negative_correlation():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    res = compute_correlations(x, y, n_boot=200, n_perm=200, seed=0)
    assert res.pearson_r == pytest.approx(-1.0)
    assert res.kendall_tau == pytest.approx(-1.0)


def test_ci_contains_point_estimate_bounds():
    rng = np.random.default_rng(1)
    x = rng.normal(size=9)
    y = 0.6 * x + rng.normal(scale=0.5, size=9)
    res = compute_correlations(x, y, n_boot=500, n_perm=500, seed=2)
    assert res.pearson_r_ci_lo <= res.pearson_r <= res.pearson_r_ci_hi
    assert res.spearman_rho_ci_lo <= res.spearman_rho <= res.spearman_rho_ci_hi
    assert res.kendall_tau_ci_lo <= res.kendall_tau <= res.kendall_tau_ci_hi
    assert 0.0 <= res.pearson_p_perm <= 1.0
