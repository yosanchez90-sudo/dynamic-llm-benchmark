"""Difference-in-differences (DiD) estimator for Comparison C (RQ1 / H2):
the 2x3 design — pre/post fine-tune x {Dynamic, ULT, PLT}.

Dynamic is the control benchmark (fine-tuning data is never drawn from a
fresh Dynamic instantiation); ULT/PLT are the "treatment" benchmarks the
fine-tune data is drawn from or overlaps with. For each treatment benchmark
B:

    delta_B       = mean_post(B) - mean_pre(B)
    control_delta = mean_post(Dynamic) - mean_pre(Dynamic)
    DiD_B         = delta_B - control_delta

A DiD_B reliably above zero (CI excludes 0) is the contamination signal
PROJECT_BRIEF.md §7 describes: gain on B beyond what's explained by the
general improvement fine-tuning gives on the control benchmark.

This module is deliberately source-agnostic — it only needs two tidy,
problem-level frames (`pre`, `post`) with a benchmark column and a metric
column. See src/Contamination/data.py for assembling those frames from this
project's actual result files.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

CONTROL_BENCHMARK = "dynamic"
DEFAULT_TREATMENT_BENCHMARKS = ("ult", "plt")


@dataclass
class DiDResult:
    benchmark: str
    pre_mean: float
    post_mean: float
    delta: float             # post - pre, this benchmark
    control_delta: float     # post - pre, control benchmark
    did: float                # delta - control_delta
    did_ci_lo: float
    did_ci_hi: float
    n_pre: int
    n_post: int
    n_pre_control: int
    n_post_control: int


def _mean(df: pd.DataFrame, metric: str) -> float:
    return float(df[metric].dropna().mean())


def _bootstrap_did_ci(
    pre_b: np.ndarray, post_b: np.ndarray, pre_c: np.ndarray, post_c: np.ndarray,
    n_boot: int, seed: int, alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap CI for (post_b-pre_b) - (post_c-pre_c), resampling
    each of the 4 cells independently with replacement (problems are treated
    as exchangeable within a cell — no paired-problem structure is assumed,
    since pre/post problem sets aren't guaranteed to be the same size).
    """
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    n1, n2, n3, n4 = len(pre_b), len(post_b), len(pre_c), len(post_c)
    for i in range(n_boot):
        s1 = pre_b[rng.integers(0, n1, n1)].mean()
        s2 = post_b[rng.integers(0, n2, n2)].mean()
        s3 = pre_c[rng.integers(0, n3, n3)].mean()
        s4 = post_c[rng.integers(0, n4, n4)].mean()
        boots[i] = (s2 - s1) - (s4 - s3)
    lo, hi = np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def compute_did(
    pre: pd.DataFrame,
    post: pd.DataFrame,
    metric: str,
    benchmark_col: str = "benchmark",
    treatment_benchmarks: tuple[str, ...] = DEFAULT_TREATMENT_BENCHMARKS,
    control_benchmark: str = CONTROL_BENCHMARK,
    n_boot: int = 2000,
    seed: int = 0,
) -> list[DiDResult]:
    """Compute DiD for each treatment benchmark vs the control benchmark.

    A treatment benchmark (or the control) missing from EITHER `pre` or
    `post` is silently skipped, not zero-filled — check which benchmarks
    came back (`[r.benchmark for r in results]`) before treating a table as
    complete; a short list means real data is still missing, not that the
    effect is zero.
    """
    results: list[DiDResult] = []
    pre_c = pre[pre[benchmark_col] == control_benchmark]
    post_c = post[post[benchmark_col] == control_benchmark]
    if pre_c.empty or post_c.empty:
        return results

    pre_c_vals = pre_c[metric].dropna().to_numpy()
    post_c_vals = post_c[metric].dropna().to_numpy()
    control_delta = float(post_c_vals.mean() - pre_c_vals.mean())

    for b in treatment_benchmarks:
        pre_b = pre[pre[benchmark_col] == b]
        post_b = post[post[benchmark_col] == b]
        if pre_b.empty or post_b.empty:
            continue
        pre_b_vals = pre_b[metric].dropna().to_numpy()
        post_b_vals = post_b[metric].dropna().to_numpy()
        pre_mean, post_mean = float(pre_b_vals.mean()), float(post_b_vals.mean())
        delta = post_mean - pre_mean
        did = delta - control_delta
        ci_lo, ci_hi = _bootstrap_did_ci(
            pre_b_vals, post_b_vals, pre_c_vals, post_c_vals, n_boot, seed
        )
        results.append(DiDResult(
            benchmark=b, pre_mean=pre_mean, post_mean=post_mean, delta=delta,
            control_delta=control_delta, did=did, did_ci_lo=ci_lo, did_ci_hi=ci_hi,
            n_pre=len(pre_b_vals), n_post=len(post_b_vals),
            n_pre_control=len(pre_c_vals), n_post_control=len(post_c_vals),
        ))
    return results


def did_table(results: list[DiDResult]) -> pd.DataFrame:
    """Tabulate compute_did()'s output; empty (not error) if results is []."""
    cols = ["benchmark", "pre_mean", "post_mean", "delta", "control_delta",
            "did", "did_ci_lo", "did_ci_hi", "n_pre", "n_post",
            "n_pre_control", "n_post_control"]
    if not results:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame([vars(r) for r in results])[cols]
