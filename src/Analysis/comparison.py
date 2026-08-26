"""Comparison A (Dynamic vs ULT, RQ1/H1) and Comparison B (ULT vs PLT,
RQ1 observational contamination signal), see PROJECT_BRIEF.md Sec 7.

PAIRING UNIT (read before trusting a p-value here): PROJECT_BRIEF.md Sec 3.1
specifies H1 as "paired Wilcoxon signed-rank, dynamic vs ULT mutation score
at model-problem level." Dynamic and ULT/PLT share no problem identity
(entirely different templates/task_ids), so there is no literal per-problem
pairing across benchmarks. The pairing implemented here is by MODEL: one
paired observation per model (that model's mean Mut@K on Dynamic-L4 vs its
mean Mut@K on ULT/PLT), Wilcoxon signed-rank across the <=9 model-level
pairs. This is the standard repeated-measures unit for benchmark-vs-benchmark
comparison when items don't correspond across conditions, flagged explicitly
because the brief's wording is genuinely ambiguous, not to hide a shortcut.
With <=9 models this test has very limited power; report the effect size
(matched-pairs rank-biserial correlation) and its CI as primary, per
PROJECT_BRIEF.md Sec 3.1 ("effect sizes with CIs are primary; p-values
support").

Dynamic-side comparison is restricted to tier="L4" (this project's CC>=8
band, matching ULT/PLT exactly). Comparing against ALL Dynamic tiers pooled
would conflate benchmark identity with complexity difference.

Comparison B (ULT vs PLT) additionally reports a CC-band breakdown (from
data/raw/ult_plt/subsample_manifest.json's per-problem `band` field) since
"matched CC" is the whole point of that comparison. The model-paired table
alone doesn't show whether an observed gap holds within each complexity band
or is driven by one band's imbalance.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

DYNAMIC_TIER = "L4"  # the only Dynamic tier comparable to ULT/PLT's CC>=8 band


@dataclass
class PairedWilcoxonResult:
    label_a: str
    label_b: str
    n_pairs: int
    models: list[str]
    mean_a: float
    mean_b: float
    statistic: float | None
    p_value: float | None
    effect_r: float | None        # matched-pairs rank-biserial correlation
    effect_ci_lo: float | None
    effect_ci_hi: float | None


def dynamic_l4_for_model(df: pd.DataFrame, model_label: str) -> pd.DataFrame:
    """Dynamic-benchmark rows for one model, restricted to tier=L4 (see
    module docstring), the only fair comparison set against ULT/PLT.
    """
    return df[(df["model_label"] == model_label) & (df["tier"] == DYNAMIC_TIER)]


def _mean_by_model(df: pd.DataFrame, metric: str, model_col: str = "model_label") -> pd.Series:
    scored = df.dropna(subset=[metric])
    return scored.groupby(model_col)[metric].mean()


def unconditional_mean_by_model(
    df: pd.DataFrame, metric: str = "mutation_score", model_col: str = "model_label",
) -> pd.Series:
    """Zero-filled per-model mean: every row counts, with 0 substituted where
    `metric` is None (baseline_passed=False, or, empirically never observed
    in this project's data, see analysis/RQ5_CROSS_DEFINITION_AUDIT.md, a
    baseline-passing problem with zero scorable mutants). Denominator is
    n_total, not n_defined.

    This is this project's best-effort reading of the ULT/PLT paper's Sec
    3.4.3 formula (Mut@k = sum(Mi)/N, N stated as "the total number of
    functions in the benchmark"), NOT a replacement for the pre-registered
    conditional Mut@K (`_mean_by_model`), see the audit doc for why the
    paper's own published code does not actually match this reading, and
    why it's reported as a labelled co-primary, not a swap.

    PROVEN identical to `mutk * baseline_pass_rate` ("coverage_adjusted" in
    scripts/build_comparison_tables.py and scripts/analyze_rq5_diagnostics.py)
    whenever n_defined == n_baseline_passed for every model, true of every
    cell in this project's data as of 2026-08-03 (verified in
    build_comparison_tables.py's a_defb_max_diff/b_defb_max_diff checks).
    """
    filled = df.copy()
    filled[metric] = filled[metric].fillna(0.0)
    return filled.groupby(model_col)[metric].mean()


def coverage_stats_table(
    df: pd.DataFrame,
    metric: str = "mutation_score",
    model_col: str = "model_label",
) -> pd.DataFrame:
    """Per-model n_total, n_defined, baseline_pass_rate for one benchmark
    side of a comparison. `metric` (Mut@K) is only ever defined where
    baseline_passed=True, so n_defined/n_total == baseline_pass_rate exactly,
    computed that way (instead of requiring a separate baseline_passed
    column) since it's the same invariant src/Analysis/stability.py's
    coverage adjustment relies on.

    Comparison A pairs this same conditioned metric across benchmarks (see
    module docstring), so it inherits RQ5's conditioning/survivorship
    finding (analysis/RQ5_DIAGNOSTICS.md sec 3): each model's paired mean is
    computed over a different-sized, different subset of problems. This
    table makes that visible; see build_comparison_tables.py for the
    coverage-adjusted robustness variant built from it.
    """
    total = df.groupby(model_col).size().rename("n_total")
    defined = df.dropna(subset=[metric]).groupby(model_col).size().rename("n_defined")
    out = pd.concat([total, defined], axis=1)
    out["n_defined"] = out["n_defined"].fillna(0).astype(int)
    out["baseline_pass_rate"] = out["n_defined"] / out["n_total"]
    return out.reset_index().rename(columns={model_col: "model_label"})


def paired_model_table(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    metric: str = "mutation_score",
    model_col: str = "model_label",
    label_a: str = "a",
    label_b: str = "b",
    conditional: bool = True,
) -> pd.DataFrame:
    """One row per model with a scorable mean `metric` on BOTH sides.
    Models missing from either side are dropped, not zero-filled (matches
    src/Contamination/did.py's convention). Reported n_pairs (== len(result))
    makes a short table visible, not implying full 9-model coverage.

    conditional=True (default): pre-registered primary, mean over
    baseline-passing rows only (`_mean_by_model`).
    conditional=False: definition-matched co-primary, zero-filled mean over
    ALL rows (`unconditional_mean_by_model`), see that function's
    docstring. A model only drops out here if it has zero rows at all for
    that benchmark side (never happens for canonical models with a
    completed run), so this variant is far less likely to shrink n_pairs
    than the conditional one.
    """
    mean_fn = _mean_by_model if conditional else unconditional_mean_by_model
    a = mean_fn(df_a, metric, model_col).rename(label_a)
    b = mean_fn(df_b, metric, model_col).rename(label_b)
    out = pd.concat([a, b], axis=1).dropna()
    return out.reset_index().rename(columns={model_col: "model_label"})


def _rank_biserial(diffs: np.ndarray) -> float:
    """Matched-pairs rank-biserial correlation: (sum of positive ranks -
    sum of negative ranks) / total rank sum, the standard effect size for
    a Wilcoxon signed-rank test. Zero-diff pairs are dropped first (standard
    treatment, matches what scipy.stats.wilcoxon does internally).
    """
    diffs = diffs[diffs != 0]
    if len(diffs) == 0:
        return 0.0
    ranks = pd.Series(np.abs(diffs)).rank().to_numpy()
    pos = ranks[diffs > 0].sum()
    neg = ranks[diffs < 0].sum()
    return float((pos - neg) / (pos + neg))


def _bootstrap_rank_biserial_ci(
    diffs: np.ndarray, n_boot: int, seed: int, alpha: float = 0.05,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(diffs)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        sample = diffs[rng.integers(0, n, n)]
        boots[i] = _rank_biserial(sample)
    lo, hi = np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def paired_wilcoxon(
    paired: pd.DataFrame,
    label_a: str = "a",
    label_b: str = "b",
    n_boot: int = 2000,
    seed: int = 0,
) -> PairedWilcoxonResult:
    """Paired Wilcoxon signed-rank across model-level pairs (see module
    docstring for the pairing-unit rationale). Returns None stat/p/effect if
    fewer than 2 pairs. scipy.stats.wilcoxon needs n>=1 but the test and its
    effect size are not meaningfully defined below 2 pairs.
    """
    n = len(paired)
    models = sorted(paired["model_label"].tolist())
    if n < 2:
        return PairedWilcoxonResult(
            label_a=label_a, label_b=label_b, n_pairs=n, models=models,
            mean_a=float(paired[label_a].mean()) if n else float("nan"),
            mean_b=float(paired[label_b].mean()) if n else float("nan"),
            statistic=None, p_value=None,
            effect_r=None, effect_ci_lo=None, effect_ci_hi=None,
        )

    diffs = (paired[label_b] - paired[label_a]).to_numpy()
    if (diffs == 0).all():
        stat, p = None, 1.0
    else:
        stat, p = (float(x) for x in wilcoxon(paired[label_a], paired[label_b]))
    effect = _rank_biserial(diffs)
    ci_lo, ci_hi = _bootstrap_rank_biserial_ci(diffs, n_boot, seed)
    return PairedWilcoxonResult(
        label_a=label_a, label_b=label_b, n_pairs=n, models=models,
        mean_a=float(paired[label_a].mean()), mean_b=float(paired[label_b].mean()),
        statistic=stat, p_value=p,
        effect_r=effect, effect_ci_lo=ci_lo, effect_ci_hi=ci_hi,
    )


def load_cc_bands(
    benchmark: str, tag: str = "core_400",
    manifest_path: str | Path = "data/raw/ult_plt/subsample_manifest.json",
) -> dict[str, str]:
    """{template_id: band_label} for `benchmark` under manifest tag `tag` —
    the CC-quartile bands scripts/generate_ult_plt_subsample.py assigned when
    pinning the subsample. Used to sub-stratify Comparison B by CC.
    """
    manifest = json.loads(Path(manifest_path).read_text())
    block = manifest[tag][benchmark.lower()]
    return {p["template_id"]: p["band"] for p in block["problems"]}


def matched_cc_table(
    ult_df: pd.DataFrame,
    plt_df: pd.DataFrame,
    band_lookup_ult: dict[str, str],
    band_lookup_plt: dict[str, str],
    metric: str = "mutation_score",
) -> pd.DataFrame:
    """Per-CC-band ULT vs PLT mean `metric`, the observational contamination
    signal (PROJECT_BRIEF.md Sec 7): expect PLT systematically higher than
    ULT at matched CC. Bands with no scorable rows on either side are simply
    absent from the result (not zero-filled).
    """
    def _band_means(df: pd.DataFrame, band_lookup: dict[str, str]) -> pd.DataFrame:
        d = df.dropna(subset=[metric]).copy()
        d["band"] = d["template_id"].map(band_lookup)
        d = d.dropna(subset=["band"])
        return d.groupby("band")[metric].agg(mean="mean", n="count")

    ult_b = _band_means(ult_df, band_lookup_ult).add_suffix("_ult")
    plt_b = _band_means(plt_df, band_lookup_plt).add_suffix("_plt")
    # inner join: a band missing scorable rows on either side can't produce
    # a "matched CC" delta, so it's dropped, not left as a NaN row,
    # same "skip, don't zero-fill" convention as src/Contamination/did.py.
    out = pd.concat([ult_b, plt_b], axis=1, join="inner")
    out["delta_plt_minus_ult"] = out["mean_plt"] - out["mean_ult"]
    return out.reset_index().rename(columns={"index": "band"})
