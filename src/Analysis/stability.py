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


def mut_at_k(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Aggregate Mut@K per group: mean of per-problem `mutation_score` over
    problems where the Exec@K/baseline gate passed (`mutation_score` is not
    None). Gate-failed problems are excluded from the mean, not zero-filled
    — matches the existing convention in scripts/results_to_excel.py's
    Summary sheet. `n_scored` / `n_total` are reported alongside so a group
    with a low scorable fraction is visible rather than hidden in the mean.
    """
    scored = df.dropna(subset=["mutation_score"])
    agg = (
        scored.groupby(group_cols)["mutation_score"]
        .agg(mut_at_k="mean", n_scored="count")
        .reset_index()
    )
    totals = df.groupby(group_cols).size().rename("n_total").reset_index()
    agg = agg.merge(totals, on=group_cols, how="right")
    agg["n_scored"] = agg["n_scored"].fillna(0).astype(int)
    return agg


def stable_mut_at_k(
    df: pd.DataFrame,
    model_col: str = "model_label",
    instantiation_col: str = "instantiation_id",
    extra_group_cols: tuple[str, ...] = (),
) -> pd.DataFrame:
    """StableMut@K: mean Mut@K per model across instantiations, with SD.

    One row per model (or per model x extra_group_cols, e.g. pass
    extra_group_cols=("tier",) for a per-tier breakdown). An instantiation
    that has zero scorable problems for a model is excluded from that
    model's mean/SD rather than counted as 0 — `n_instantiations` reports
    how many instantiations actually contributed.
    """
    group_cols = [model_col, *extra_group_cols, instantiation_col]
    per_inst = mut_at_k(df, group_cols)
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
) -> pd.DataFrame:
    """Pairwise Kendall tau between per-instantiation model rankings.

    For each pair of instantiations, ranks models by their aggregate
    Mut@K within that instantiation and correlates the two rankings.
    A model must have a scorable Mut@K in both instantiations of a pair
    to be included in that pair's ranking; `n_models` reports how many
    qualified (tau is NaN if fewer than 2).
    """
    per_inst = mut_at_k(df, [model_col, instantiation_col])
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
