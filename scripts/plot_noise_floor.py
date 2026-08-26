"""Noise floor, one argument per figure: which metrics can resolve model
differences at all, and does this hold within every Dynamic tier or just
pooled? Between-model score spread (max-min across the 9 canonical models)
vs the mean within-model between-instantiation SD, per metric per tier
(L1-L4) plus pooled. A metric/tier cell whose spread is smaller than its
own noise floor cannot reliably rank models there, independent of
cross-benchmark agreement (analysis/RANKING_MATRIX.md Table 3 is the
pooled-only version of this; this figure adds the per-tier breakdown).

The specific 4-model unresolvable cluster found in
analysis/RQ5_DIAGNOSTICS.md (Claude Haiku > Claude Sonnet > Qwen 32B >
Gemini Flash-Lite, pooled conditional Mut@K spread 0.002 vs individual
SDs 0.003-0.005) is annotated by name on the conditional-Mut@K/pooled bar.
It is a pooled-conditional-Mut@K-specific finding, not something this
figure re-derives generically for every cell.

Usage: python scripts/plot_noise_floor.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
import pandas as pd

from coverage_matrix import CANONICAL_MODELS  # noqa: E402
from src.Analysis.loader import load_records  # noqa: E402
from src.Analysis.provenance import stamp_block  # noqa: E402
from src.Analysis.stability import stable_mut_at_k  # noqa: E402

OUT_PATH = ROOT / "analysis" / "figures" / "noise_floor.pdf"
METRICS = ["exec_rate", "baseline_pass_rate", "conditional_mutk", "coverage_adjusted"]
METRIC_LABELS = {
    "exec_rate": "exec_rate", "baseline_pass_rate": "baseline_pass_rate",
    "conditional_mutk": "conditional Mut@K", "coverage_adjusted": "coverage-adjusted Mut@K",
}
METRIC_COLORS = {
    "exec_rate": "#7f7f7f", "baseline_pass_rate": "#ff7f0e",
    "conditional_mutk": "#1f77b4", "coverage_adjusted": "#2ca02c",
}
METRIC_COL = {"exec_rate": "exec_rate", "baseline_pass_rate": "baseline_passed", "conditional_mutk": "mutation_score"}
TIERS = ["L1", "L2", "L3", "L4"]
CATEGORIES = TIERS + ["pooled"]
UNRESOLVABLE_CLUSTER = ["Claude Haiku", "Claude Sonnet", "Qwen 32B", "Gemini Flash-Lite"]


def _cell(dyn: pd.DataFrame, metric: str, tier: str | None) -> tuple[float | None, float | None]:
    """(between_model_spread, mean_within_model_sd) for one metric x tier
    (tier=None -> pooled, all tiers)."""
    view = dyn if tier is None else dyn[dyn["tier"] == tier]
    if metric == "coverage_adjusted":
        stable = stable_mut_at_k(view, coverage_adjust=True)
    else:
        stable = stable_mut_at_k(view, metric_col=METRIC_COL[metric])
    stable_2plus = stable[stable["n_instantiations"] >= 2]
    mean_sd = float(stable_2plus["sd_mut_at_k"].mean()) if len(stable_2plus) else None

    # between-model spread: per-model mean of the metric over `view`, then max-min
    per_model_scores = []
    for label in CANONICAL_MODELS:
        sub = view[view["model_label"] == label]
        if len(sub) == 0:
            continue
        if metric == "exec_rate":
            val = float(sub["exec_rate"].mean())
        elif metric == "baseline_pass_rate":
            val = float(sub["baseline_passed"].astype(float).mean())
        elif metric == "conditional_mutk":
            defined = sub.dropna(subset=["mutation_score"])
            val = float(defined["mutation_score"].mean()) if len(defined) else None
        else:  # coverage_adjusted
            defined = sub.dropna(subset=["mutation_score"])
            if len(defined) == 0:
                val = None
            else:
                cond = float(defined["mutation_score"].mean())
                bp = float(sub["baseline_passed"].astype(float).mean())
                val = cond * bp
        if val is not None:
            per_model_scores.append(val)
    spread = (max(per_model_scores) - min(per_model_scores)) if len(per_model_scores) >= 2 else None
    return spread, mean_sd


def main() -> None:
    dynamic = load_records("data/results/dynamic", benchmark="dynamic")
    dynamic = dynamic[dynamic["model_label"].isin(CANONICAL_MODELS)]

    rows = []
    for metric in METRICS:
        for cat in CATEGORIES:
            tier = None if cat == "pooled" else cat
            spread, sd = _cell(dynamic, metric, tier)
            ratio = (spread / sd) if (spread is not None and sd) else None
            rows.append({"metric": metric, "category": cat, "spread": spread, "mean_sd": sd, "ratio": ratio})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "analysis" / "noise_floor_by_tier.csv", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(CATEGORIES))
    width = 0.2
    for k, metric in enumerate(METRICS):
        sub = df[df["metric"] == metric].set_index("category").reindex(CATEGORIES)
        offsets = x + (k - 1.5) * width
        vals = sub["ratio"].to_numpy(dtype=float)
        bars = ax.bar(offsets, np.nan_to_num(vals, nan=0.0), width=width,
                      color=METRIC_COLORS[metric], label=METRIC_LABELS[metric],
                      edgecolor="white", linewidth=0.6, zorder=3)
        for xi, v in zip(offsets, vals):
            if np.isnan(v):
                ax.text(xi, 0.5, "n/a", ha="center", va="bottom", fontsize=6.5, color="dimgray", rotation=90)

    ax.axhline(1.0, color="#d62728", linestyle="--", linewidth=1.2, alpha=0.8, zorder=2,
               label="ratio=1 (cannot resolve model differences)")

    ax.set_ylim(0, 62)  # headroom above the tallest bar (~45) for the annotation below

    # Annotate the specific 4-model unresolvable cluster on conditional
    # Mut@K's pooled bar (analysis/RQ5_DIAGNOSTICS.md), a real, named
    # finding, not re-derived generically here. Box placed entirely above
    # the tallest bar (headroom reserved via ylim above) so it never
    # overlaps plotted data.
    cond_pooled_idx = CATEGORIES.index("pooled")
    cond_x = cond_pooled_idx + (METRICS.index("conditional_mutk") - 1.5) * width
    cond_ratio = df[(df["metric"] == "conditional_mutk") & (df["category"] == "pooled")]["ratio"].iloc[0]
    ax.annotate(
        "4-model unresolvable cluster (RQ5_DIAGNOSTICS.md):\n" + " > ".join(UNRESOLVABLE_CLUSTER)
        + "\npooled spread=0.002 vs individual SDs 0.003-0.005",
        xy=(cond_x, cond_ratio), xytext=(2.0, 54),
        fontsize=7.8, color="#1f77b4", ha="center", va="center",
        arrowprops=dict(arrowstyle="->", color="#1f77b4", alpha=0.85, connectionstyle="arc3,rad=0.15"),
        bbox=dict(boxstyle="round,pad=0.4", fc="#eef5ff", ec="#1f77b4", alpha=0.95, linewidth=0.8),
    )

    ax.set_xticks(x)
    ax.set_xticklabels([f"Dynamic {t}" for t in TIERS] + ["Dynamic\npooled"], fontsize=9.5)
    ax.set_ylabel("Between-model spread / mean within-model SD (ratio)", fontsize=10.5)
    ax.set_title("Noise floor by metric and Dynamic tier — which metrics can resolve model differences?", fontsize=11.5)
    ax.legend(fontsize=8.5, loc="upper left", ncol=3)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35, zorder=0)
    fig.tight_layout()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_PATH.with_suffix(".png"), dpi=150, bbox_inches="tight")

    provenance = f"""# Noise floor by metric and tier — provenance

{stamp_block("scripts/plot_noise_floor.py")}
Computed directly from data/results/dynamic/*.jsonl (canonical 9 models),
using src.Analysis.stability.stable_mut_at_k per tier (extra_group_cols
not used here, filtered per tier instead, then aggregated). Raw table:
analysis/noise_floor_by_tier.csv.

4-model unresolvable-cluster annotation is a named citation of
analysis/RQ5_DIAGNOSTICS.md's finding (pooled conditional Mut@K only), not
re-derived generically for every metric/tier cell in this figure.

Output: {OUT_PATH.relative_to(ROOT)} (+ .png).
"""
    PROVENANCE_OUT = ROOT / "analysis" / (OUT_PATH.stem + "_PROVENANCE.md")
    PROVENANCE_OUT.write_text(provenance)
    print(f"Saved: {OUT_PATH} and .png, {PROVENANCE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
