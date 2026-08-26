"""Ranking-matrix heatmap, one argument per figure: does the low
Dynamic<->ULT rank agreement generalise across metrics, or is it specific
to conditional Mut@K? Rows = the 4 metrics (exec_rate, baseline_pass_rate,
conditional Mut@K, coverage-adjusted Mut@K), columns = the 3 benchmark
pairs (Dynamic<->ULT, Dynamic<->BigCodeBench, ULT<->BigCodeBench), cells =
Kendall tau, colour-scaled on a diverging map centred at tau=0 (tau is a
genuinely bipolar statistic, see dataviz skill's diverging-data rule).
Two panels: canonical-9 and canonical+cross-family-13, side by side, same
colour scale, so the two scopes are directly comparable by eye.

Usage: python scripts/plot_ranking_matrix_heatmap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.Analysis.provenance import stamp_block

CORR_CSV = ROOT / "analysis" / "ranking_matrix_correlations.csv"
OUT_PATH = ROOT / "analysis" / "figures" / "ranking_matrix_heatmap.pdf"

METRICS = ["exec_rate", "baseline_pass_rate", "conditional_mutk", "coverage_adjusted"]
METRIC_LABELS = {
    "exec_rate": "exec_rate", "baseline_pass_rate": "baseline_pass_rate",
    "conditional_mutk": "conditional Mut@K", "coverage_adjusted": "coverage-adjusted Mut@K",
}
PAIRS = ["Dynamic<->ULT", "Dynamic<->BigCodeBench", "ULT<->BigCodeBench"]
# "(pooled)" is load-bearing, not decorative: the Dynamic side of every pair
# here is pooled across all four CC tiers, not the CC-matched Dynamic-L4
# slice Comparison A uses, see analysis/TIER_SYMMETRY_AUDIT.md's reverse
# check (defect #1). Every other RQ5 figure in this project states this in
# its axis label; this one didn't, and a reader who only ever sees this
# figure standalone (e.g. pasted into a chapter with its own caption) had no
# way to know from the artifact alone.
PAIR_LABELS = ["Dynamic (pooled)\n↔ ULT", "Dynamic (pooled)\n↔ BigCodeBench", "ULT\n↔ BigCodeBench"]


def _heatmap_panel(ax, sub_df, scope_label, cmap, norm):
    grid = np.full((len(METRICS), len(PAIRS)), np.nan)
    annotations = np.empty((len(METRICS), len(PAIRS)), dtype=object)
    for i, metric in enumerate(METRICS):
        for j, pair in enumerate(PAIRS):
            row = sub_df[(sub_df["metric"] == metric) & (sub_df["pair"] == pair)]
            if len(row) == 0 or pd.isna(row.iloc[0]["kendall_tau"]):
                n = int(row.iloc[0]["n"]) if len(row) else 0
                annotations[i, j] = f"n={n}\n(too few)"
                continue
            r = row.iloc[0]
            tau = r["kendall_tau"]
            grid[i, j] = tau
            p_raw = r["kendall_p_perm"]
            p_holm = r["kendall_p_holm"]
            # different markers for raw-significant vs Holm-significant vs
            # neither, per the dataviz skill's "identity never colour-alone"
            # rule. Significance is encoded in the annotation text/symbol,
            # not inferred from colour intensity alone.
            if p_holm < 0.05:
                sig = "**"  # survives Holm correction
            elif p_raw < 0.05:
                sig = "*"   # raw-significant only, not after Holm
            else:
                sig = ""
            annotations[i, j] = f"τ={tau:.3f}{sig}\nn={int(r['n'])}"

    im = ax.imshow(grid, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(range(len(PAIRS)))
    ax.set_xticklabels(PAIR_LABELS, fontsize=8.5)
    ax.set_yticks(range(len(METRICS)))
    ax.set_yticklabels([METRIC_LABELS[m] for m in METRICS], fontsize=9)
    ax.set_title(scope_label, fontsize=10.5)
    for i in range(len(METRICS)):
        for j in range(len(PAIRS)):
            val = grid[i, j]
            # contrast-aware label colour: dark text on light cells, light
            # text on dark/saturated cells (dataviz skill's label-contrast rule)
            text_color = "white" if (not np.isnan(val) and abs(val) > 0.55) else "#222222"
            ax.text(j, i, annotations[i, j], ha="center", va="center",
                     fontsize=8, color=text_color, linespacing=1.4)
    ax.set_xticks(np.arange(-0.5, len(PAIRS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(METRICS), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="minor", length=0)
    return im


def main() -> None:
    corr = pd.read_csv(CORR_CSV)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    cmap = plt.get_cmap("RdBu_r")  # diverging: red=negative/no agreement, blue=strong agreement, white=0
    norm = TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0)

    fig, axes = plt.subplots(1, 2, figsize=(15.5, 5.5))
    scopes = [("canonical", "Canonical (9 models)"), ("canonical_plus_cross_family", "Canonical + cross-family (13 models)")]
    im = None
    for ax, (scope_key, scope_label) in zip(axes, scopes):
        sub = corr[corr["scope"] == scope_key]
        im = _heatmap_panel(ax, sub, scope_label, cmap, norm)

    cbar = fig.colorbar(im, ax=axes, orientation="vertical", fraction=0.025, pad=0.03)
    cbar.set_label("Kendall τ (rank agreement)", fontsize=9.5)

    fig.suptitle(
        "Ranking matrix: cross-benchmark rank agreement by metric\n"
        "** = significant after Holm-Bonferroni (within-scope, 12-test family)   "
        "* = significant raw p<0.05 only, not after correction",
        fontsize=10.5,
    )
    fig.subplots_adjust(top=0.80, wspace=0.55)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_PATH.with_suffix(".png"), dpi=150, bbox_inches="tight")

    provenance = f"""# Ranking matrix heatmap — provenance

{stamp_block("scripts/plot_ranking_matrix_heatmap.py")}
Source: {CORR_CSV.relative_to(ROOT)} (both scopes; Holm-Bonferroni applied
separately per scope, 12-test family each, computed in
scripts/build_ranking_matrix.py).

Output: {OUT_PATH.relative_to(ROOT)} (+ .png).
"""
    PROVENANCE_OUT = ROOT / "analysis" / (OUT_PATH.stem + "_PROVENANCE.md")
    PROVENANCE_OUT.write_text(provenance)
    print(f"Saved: {OUT_PATH} and .png, {PROVENANCE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
