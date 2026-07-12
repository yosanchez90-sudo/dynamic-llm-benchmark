"""Unit tests for src/Contamination/did.py using synthetic frames with known
ground-truth DiD values — no dependency on real fine-tuning results.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.Contamination.did import compute_did, did_table


def _frame(benchmark: str, value: float, n: int) -> pd.DataFrame:
    return pd.DataFrame({"benchmark": [benchmark] * n, "score": [value] * n})


def test_known_did_with_constant_cells_is_exact():
    # All values constant within each cell -> bootstrap resampling can only
    # ever reproduce the same mean, so the CI collapses to a point at the
    # true DiD. This exercises the full pipeline (including the bootstrap)
    # with a value we can check exactly, not just approximately.
    pre = pd.concat([_frame("dynamic", 0.5, 100), _frame("ult", 0.4, 50)])
    post = pd.concat([_frame("dynamic", 0.6, 100), _frame("ult", 0.7, 50)])

    results = compute_did(pre, post, metric="score", treatment_benchmarks=("ult",), n_boot=200)
    assert len(results) == 1
    r = results[0]
    assert r.benchmark == "ult"
    assert r.control_delta == pytest.approx(0.1)
    assert r.delta == pytest.approx(0.3)
    assert r.did == pytest.approx(0.2)
    assert r.did_ci_lo == pytest.approx(0.2, abs=1e-9)
    assert r.did_ci_hi == pytest.approx(0.2, abs=1e-9)
    assert r.n_pre == 50 and r.n_post == 50
    assert r.n_pre_control == 100 and r.n_post_control == 100


def test_did_ci_brackets_point_estimate_with_real_variance():
    import numpy as np
    rng = np.random.default_rng(0)
    pre = pd.concat([
        pd.DataFrame({"benchmark": "dynamic", "score": rng.binomial(1, 0.5, 300)}),
        pd.DataFrame({"benchmark": "plt", "score": rng.binomial(1, 0.3, 300)}),
    ])
    post = pd.concat([
        pd.DataFrame({"benchmark": "dynamic", "score": rng.binomial(1, 0.55, 300)}),
        pd.DataFrame({"benchmark": "plt", "score": rng.binomial(1, 0.7, 300)}),
    ])
    results = compute_did(pre, post, metric="score", treatment_benchmarks=("plt",), n_boot=1000, seed=1)
    r = results[0]
    assert r.did_ci_lo <= r.did <= r.did_ci_hi


def test_missing_treatment_benchmark_is_skipped_not_zero_filled():
    pre = _frame("dynamic", 0.5, 20)
    post = _frame("dynamic", 0.6, 20)
    # no "ult" or "plt" rows anywhere
    results = compute_did(pre, post, metric="score")
    assert results == []


def test_missing_control_yields_no_results_at_all():
    pre = _frame("ult", 0.4, 20)
    post = _frame("ult", 0.7, 20)
    # control ("dynamic") missing entirely
    results = compute_did(pre, post, metric="score")
    assert results == []


def test_partial_treatment_availability_only_computes_what_exists():
    # ult has both pre and post; plt only has pre (post never scored yet) —
    # exactly today's real situation once model evaluation starts on one
    # benchmark before the other.
    pre = pd.concat([_frame("dynamic", 0.5, 20), _frame("ult", 0.4, 20), _frame("plt", 0.3, 20)])
    post = pd.concat([_frame("dynamic", 0.6, 20), _frame("ult", 0.7, 20)])
    results = compute_did(pre, post, metric="score", n_boot=200)
    assert {r.benchmark for r in results} == {"ult"}


def test_did_table_empty_is_well_formed():
    df = did_table([])
    assert list(df.columns) == [
        "benchmark", "pre_mean", "post_mean", "delta", "control_delta",
        "did", "did_ci_lo", "did_ci_hi", "n_pre", "n_post",
        "n_pre_control", "n_post_control",
    ]
    assert len(df) == 0


def test_did_table_matches_compute_did():
    pre = pd.concat([_frame("dynamic", 0.5, 30), _frame("ult", 0.4, 30), _frame("plt", 0.2, 30)])
    post = pd.concat([_frame("dynamic", 0.5, 30), _frame("ult", 0.9, 30), _frame("plt", 0.9, 30)])
    results = compute_did(pre, post, metric="score", n_boot=200)
    df = did_table(results)
    assert set(df["benchmark"]) == {"ult", "plt"}
    assert df.set_index("benchmark").loc["ult", "did"] == pytest.approx(0.5)
    assert df.set_index("benchmark").loc["plt", "did"] == pytest.approx(0.7)
