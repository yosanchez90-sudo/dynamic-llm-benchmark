"""Cross-instantiation stability metrics (RQ4.1 / H5): StableMut@K and
pairwise Kendall tau between per-instantiation model rankings.

See PROJECT_BRIEF.md §5.4 (StableMut@K definition) and §3.1 (H5: pairwise
Kendall tau between rankings across instantiations).
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import kendalltau


def mut_at_k(df: pd.DataFrame, group_cols: list[str], metric_col: str = "mutation_score") -> pd.DataFrame:
    """Aggregate a per-problem metric per group: mean of `metric_col` over
    rows where it's defined (not None). Gate-failed problems are excluded
    from the mean, not zero-filled. Matches the existing convention in
    scripts/results_to_excel.py's Summary sheet. `n_scored` / `n_total` are
    reported alongside so a group with a low scorable fraction is visible,
    not hidden in the mean.

    `metric_col` generalises this beyond `mutation_score` (the default,
    used throughout RQ4.1/H5) to any per-row 0/1-or-float column.
    `exec_rate` and `baseline_passed` are both always-defined (never None)
    for every row, so for those two this reduces to a plain mean with no
    conditioning; used by analysis/RANKING_MATRIX.md's per-metric
    reliability table (added 2026-08-04) so every metric shares the exact
    same aggregation/CI machinery, not each being computed ad hoc.
    Boolean columns (e.g. `baseline_passed`) are cast to float first.
    pandas' own bool-mean works fine, but an explicit cast keeps the output
    dtype consistent across metric_col choices.
    """
    working = df.copy()
    if working[metric_col].dtype == bool:
        working[metric_col] = working[metric_col].astype(float)
    scored = working.dropna(subset=[metric_col])
    agg = (
        scored.groupby(group_cols)[metric_col]
        .agg(mut_at_k="mean", n_scored="count")
        .reset_index()
    )
    totals = working.groupby(group_cols).size().rename("n_total").reset_index()
    agg = agg.merge(totals, on=group_cols, how="right")
    agg["n_scored"] = agg["n_scored"].fillna(0).astype(int)
    return agg


def _apply_coverage_adjustment(per_inst: pd.DataFrame) -> pd.DataFrame:
    """mut_at_k -> mut_at_k x (n_scored/n_total) in place on a copy --
    n_scored/n_total equals baseline_pass_rate exactly, since mutation_score
    is only ever defined where baseline_passed=True (RQ5's conditioning/
    survivorship finding, analysis/RQ5_DIAGNOSTICS.md sec 3). Folds the
    conditioning back into the per-instantiation score before it's used for
    stability/reliability, instead of only ever measuring stability of the
    subset that happened to pass."""
    per_inst = per_inst.copy()
    per_inst["mut_at_k"] = per_inst["mut_at_k"] * (per_inst["n_scored"] / per_inst["n_total"])
    return per_inst


def stable_mut_at_k(
    df: pd.DataFrame,
    model_col: str = "model_label",
    instantiation_col: str = "instantiation_id",
    extra_group_cols: tuple[str, ...] = (),
    coverage_adjust: bool = False,
    metric_col: str = "mutation_score",
) -> pd.DataFrame:
    """StableMut@K: mean Mut@K per model across instantiations, with SD.

    One row per model (or per model x extra_group_cols, e.g. pass
    extra_group_cols=("tier",) for a per-tier breakdown). An instantiation
    that has zero scorable problems for a model is excluded from that
    model's mean/SD, not counted as 0. `n_instantiations` reports
    how many instantiations actually contributed.

    coverage_adjust=True computes StableMut@K on the coverage-adjusted score
    (Mut@K x baseline_pass_rate per instantiation) instead of raw Mut@K,
    see _apply_coverage_adjustment. Only meaningful with the default
    metric_col="mutation_score" (coverage_adjust=True with a different
    metric_col raises via _apply_coverage_adjustment's own precondition).

    metric_col: see mut_at_k()'s docstring, generalises this beyond
    mutation_score to exec_rate/baseline_passed for the per-metric
    reliability comparison in analysis/RANKING_MATRIX.md.
    """
    if coverage_adjust and metric_col != "mutation_score":
        raise ValueError(
            "coverage_adjust=True folds in baseline_pass_rate, which is only "
            "meaningful as a correction to mutation_score -- pass "
            "coverage_adjust=False for other metric_col choices."
        )
    group_cols = [model_col, *extra_group_cols, instantiation_col]
    per_inst = mut_at_k(df, group_cols, metric_col=metric_col)
    if coverage_adjust:
        per_inst = _apply_coverage_adjustment(per_inst)
    scorable = per_inst[per_inst["n_scored"] > 0]

    agg_cols = [model_col, *extra_group_cols]
    out = (
        scorable.groupby(agg_cols)["mut_at_k"]
        .agg(stable_mut_at_k="mean", sd_mut_at_k="std", n_instantiations="count")
        .reset_index()
    )
    out["sd_mut_at_k"] = out["sd_mut_at_k"].fillna(0.0)  # single-instantiation groups
    return out.sort_values(agg_cols).reset_index(drop=True)


def pairwise_kendall_tau(
    df: pd.DataFrame,
    model_col: str = "model_label",
    instantiation_col: str = "instantiation_id",
    coverage_adjust: bool = False,
    metric_col: str = "mutation_score",
) -> pd.DataFrame:
    """Pairwise Kendall tau between per-instantiation model rankings.

    For each pair of instantiations, ranks models by their aggregate
    metric (mutation_score by default, see metric_col) within that
    instantiation and correlates the two rankings. A model must have a
    scorable value in both instantiations of a pair to be included in
    that pair's ranking; `n_models` reports how many qualified (tau is
    NaN if fewer than 2).

    coverage_adjust=True ranks models by the coverage-adjusted score
    (Mut@K x baseline_pass_rate per instantiation) instead of raw Mut@K,
    see _apply_coverage_adjustment; only valid with the default metric_col.

    metric_col: see mut_at_k()'s docstring, generalises this beyond
    mutation_score to exec_rate/baseline_passed for the per-metric
    reliability comparison in analysis/RANKING_MATRIX.md.
    """
    if coverage_adjust and metric_col != "mutation_score":
        raise ValueError(
            "coverage_adjust=True folds in baseline_pass_rate, which is only "
            "meaningful as a correction to mutation_score -- pass "
            "coverage_adjust=False for other metric_col choices."
        )
    per_inst = mut_at_k(df, [model_col, instantiation_col], metric_col=metric_col)
    if coverage_adjust:
        per_inst = _apply_coverage_adjustment(per_inst)
    per_inst = per_inst[per_inst["n_scored"] > 0]

    instantiations = sorted(per_inst[instantiation_col].unique())
    rows = []
    for a, b in combinations(instantiations, 2):
        wide = (
            per_inst[per_inst[instantiation_col].isin([a, b])]
            .pivot(index=model_col, columns=instantiation_col, values="mut_at_k")
            .dropna()
        )
        if len(wide) < 2:
            rows.append({
                "instantiation_a": a, "instantiation_b": b,
                "n_models": len(wide), "tau": np.nan, "p_value": np.nan,
            })
            continue
        tau, p = kendalltau(wide[a], wide[b])
        rows.append({
            "instantiation_a": a, "instantiation_b": b,
            "n_models": len(wide), "tau": tau, "p_value": p,
        })
    return pd.DataFrame(rows)


def mean_pairwise_tau(pairwise: pd.DataFrame) -> float | None:
    """Summarise a pairwise_kendall_tau() table into one mean tau, ignoring
    pairs that couldn't be computed (fewer than 2 qualifying models)."""
    valid = pairwise["tau"].dropna()
    return float(valid.mean()) if len(valid) else None


def mean_pairwise_tau_scoped(
    pairwise: pd.DataFrame,
    instantiations: set[str] | None = None,
) -> float | None:
    """mean_pairwise_tau(), restricted to pairs where BOTH instantiations are
    in `instantiations` (None = no restriction, identical to
    mean_pairwise_tau). Exists so callers share one implementation of a named
    scope instead of re-deriving the pair-filter inline, e.g. this
    project's N=4 target scope (PROJECT_BRIEF.md Sec 11, instantiations
    {"1","2","3","4"}, excluding the deferred/partial instantiation 5) is
    used both by analyze_stability.py's own reporting and by
    analyze_rq5_diagnostics.py's attenuation correction; a hard-coded
    constant for the latter went stale the moment new data changed the
    former (confirmed 2026-07-28)."""
    if instantiations is not None:
        pairwise = pairwise[
            pairwise["instantiation_a"].isin(instantiations)
            & pairwise["instantiation_b"].isin(instantiations)
        ]
    return mean_pairwise_tau(pairwise)
