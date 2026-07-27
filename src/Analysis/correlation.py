"""Cross-benchmark correlation helper (RQ5/H6): Pearson r, Spearman rho, and
Kendall tau between two per-model score/ranking vectors, with bootstrap CIs
and permutation p-values -- the small-N (7-9 models) reporting standard
recorded in analysis/RQ5_ANALYSIS_PLAN.md ("bootstrap CI... rather than a
parametric p-value, given N is too small for the normal approximation to be
trustworthy").
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import kendalltau, pearsonr, spearmanr


@dataclass
class CorrelationResult:
    n: int
    pearson_r: float
    pearson_r_ci_lo: float
    pearson_r_ci_hi: float
    pearson_p_perm: float
    spearman_rho: float
    spearman_rho_ci_lo: float
    spearman_rho_ci_hi: float
    spearman_p_perm: float
    kendall_tau: float
    kendall_tau_ci_lo: float
    kendall_tau_ci_hi: float
    kendall_p_perm: float


def _bootstrap_ci(x: np.ndarray, y: np.ndarray, stat_fn, n_boot: int, seed: int,
                   alpha: float = 0.05) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(x)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        xb, yb = x[idx], y[idx]
        if np.std(xb) == 0 or np.std(yb) == 0:
            boots[i] = np.nan
            continue
        boots[i] = stat_fn(xb, yb)
    boots = boots[~np.isnan(boots)]
    if len(boots) == 0:
        return float("nan"), float("nan")
    lo, hi = np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def _permutation_p(x: np.ndarray, y: np.ndarray, stat_fn, observed: float,
                    n_perm: int, seed: int) -> float:
    rng = np.random.default_rng(seed)
    n = len(x)
    count = 0
    for _ in range(n_perm):
        yp = rng.permutation(y)
        stat = stat_fn(x, yp)
        if abs(stat) >= abs(observed):
            count += 1
    return (count + 1) / (n_perm + 1)  # add-one smoothing, avoids p=0


def compute_correlations(
    x: np.ndarray, y: np.ndarray,
    n_boot: int = 2000, n_perm: int = 10000, seed: int = 0,
) -> CorrelationResult:
    """x, y: paired per-model score vectors (same model order). n < ~10 is
    expected and handled (bootstrap/permutation both work at small n, just
    with wide CIs -- that width IS the power-limitation finding, not a bug).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    if n != len(y):
        raise ValueError(f"x and y must be the same length, got {n} and {len(y)}")

    r, _ = pearsonr(x, y)
    rho, _ = spearmanr(x, y)
    tau, _ = kendalltau(x, y)

    r_lo, r_hi = _bootstrap_ci(x, y, lambda a, b: pearsonr(a, b)[0], n_boot, seed)
    rho_lo, rho_hi = _bootstrap_ci(x, y, lambda a, b: spearmanr(a, b)[0], n_boot, seed + 1)
    tau_lo, tau_hi = _bootstrap_ci(x, y, lambda a, b: kendalltau(a, b)[0], n_boot, seed + 2)

    r_p = _permutation_p(x, y, lambda a, b: pearsonr(a, b)[0], r, n_perm, seed + 3)
    rho_p = _permutation_p(x, y, lambda a, b: spearmanr(a, b)[0], rho, n_perm, seed + 4)
    tau_p = _permutation_p(x, y, lambda a, b: kendalltau(a, b)[0], tau, n_perm, seed + 5)

    return CorrelationResult(
        n=n,
        pearson_r=float(r), pearson_r_ci_lo=r_lo, pearson_r_ci_hi=r_hi, pearson_p_perm=r_p,
        spearman_rho=float(rho), spearman_rho_ci_lo=rho_lo, spearman_rho_ci_hi=rho_hi, spearman_p_perm=rho_p,
        kendall_tau=float(tau), kendall_tau_ci_lo=tau_lo, kendall_tau_ci_hi=tau_hi, kendall_p_perm=tau_p,
    )
