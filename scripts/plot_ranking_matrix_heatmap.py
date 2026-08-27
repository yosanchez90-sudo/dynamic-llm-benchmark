"""Ranking-matrix heatmap, one argument per figure: does the low
Dynamic<->ULT rank agreement generalise across metrics, or is it specific
to conditional Mut@K? Rows = the 4 metrics (exec_rate, baseline_pass_rate,
conditional Mut@K, coverage-adjusted Mut@K), columns = the 3 benchmark
pairs (Dynamic<->ULT, Dynamic<->BigCodeBench, ULT<->BigCodeBench), cells =
Kendall tau, colour-scaled on a diverging map centred at tau=0 (tau is a
genuinely bipolar statistic, see dataviz skill's diverging-data rule).
Two panels: canonical-9 and canonical+cross-family-13, stacked one above
the other (not side by side, changed 2026-08-27 in a print-legibility
pass), same colour scale, so the two scopes are directly comparable by
eye. Stacking keeps each panel close to the paper's actual single-column
print width, so \includegraphics[width=\columnwidth] applies almost no
further shrink and the cell annotations stay readable in print instead of
shrinking by the ~2x a side-by-side layout at this same content size would
need.

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
from _figure_style import COL_W, apply_style

CORR_CSV = ROOT / "analysis" / "ranking_matrix_correlations.csv"
OUT_PATH = ROOT / "analysis" / "figures" / "ranking_matrix_heatmap.pdf"

METRICS = ["exec_rate", "baseline_pass_rate", "conditional_mutk", "coverage_adjusted"]
METRIC_LABELS = {
    "exec_rate": "exec_rate", "baseline_pass_rate": "baseline_pass_rate",
    "conditional_mutk": "conditional Mut@K", "coverage_adjusted": "coverage-adjusted Mut@K",
}
PAIRS = ["Dynamic<->ULT", "Dynamic<->BigCodeBench", "ULT<->BigCodeBench"]
# "(pooled)" is load-bearing, not decorative: the DyMuT side of every pair
# here is pooled across all four CC tiers, not the CC-matched DyMuT-L4
# slice Comparison A uses, see analysis/TIER_SYMMETRY_AUDIT.md's reverse
# check (defect #1). Every other RQ5 figure in this project states this in
# its axis label; this one didn't, and a reader who only ever sees this
# figure standalone (e.g. pasted into a chapter with its own caption) had no
# way to know from the artifact alone.
PAIR_LABELS = ["DyMuT\n↔ ULT", "DyMuT\n↔ BCB", "ULT\n↔ BCB"]


def _heatmap_panel(ax, sub_df, scope_label, cmap, norm, panel_id):
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
    ax.set_xticklabels(PAIR_LABELS)
    ax.set_yticks(range(len(METRICS)))
    ax.set_yticklabels([METRIC_LABELS[m] for m in METRICS])
    # Panel identity is (a)/(b); the model count moves to the caption
    # (FIGURE_TABLE_SPEC.md G-1: a plot title duplicates what the caption
    # already needs to say). Placed just above the grid, inside the axes
    # (not above it): a colorbar shared across both stacked panels leaves
    # too little vertical gap between panels for an above-axes title.
    ax.set_ylim(len(METRICS) - 0.5, -1.05)
    ax.text(-0.5, -0.85, f"{panel_id} {scope_label}", fontsize=8, fontweight="bold", ha="left", va="top")
    for i in range(len(METRICS)):
        for j in range(len(PAIRS)):
            val = grid[i, j]
            # contrast-aware label colour: dark text on light cells, light
            # text on dark/saturated cells (dataviz skill's label-contrast rule)
            text_color = "white" if (not np.isnan(val) and abs(val) > 0.55) else "#222222"
            ax.text(j, i, annotations[i, j], ha="center", va="center",
                     fontsize=7, color=text_color, linespacing=1.5)
    ax.set_xticks(np.arange(-0.5, len(PAIRS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(METRICS), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="minor", length=0)
    return im


def main() -> None:
    apply_style()
    corr = pd.read_csv(CORR_CSV)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    # RdBu_r: diverging, legible in greyscale as light-to-dark on both arms
    # away from the white midpoint (FIGURE_TABLE_SPEC.md G-5); significance
    # is carried by the **/* text annotations, not colour alone.
    cmap = plt.get_cmap("RdBu_r")
    norm = TwoSlopeNorm(vmin=-1.0, vcenter=0.0, vmax=1.0)

    # Single column, stacked (see module docstring), at the actual column
    # width (FIGURE_TABLE_SPEC.md G-3). Manual layout, not constrained_layout:
    # a colorbar shared across both axes collapses constrained_layout's
    # sizing when combined with an axes-relative text label placed above the
    # plot box (confirmed: axes shrank to zero, cell text overlapped).
    fig, axes = plt.subplots(2, 1, figsize=(COL_W, 2 * COL_W * 1.15))
    scopes = [("canonical", "Canonical (9 models)"), ("canonical_plus_cross_family", "Canonical + cross-family (13 models)")]
    im = None
    for ax, (panel_id, (scope_key, scope_label)) in zip(axes, zip(["(a)", "(b)"], scopes)):
        sub = corr[corr["scope"] == scope_key]
        im = _heatmap_panel(ax, sub, scope_label, cmap, norm, panel_id)

    fig.subplots_adjust(top=0.92, bottom=0.06, hspace=0.7, right=0.86, left=0.30)
    cbar = fig.colorbar(im, ax=axes, orientation="vertical", fraction=0.06, pad=0.12, shrink=0.82)
    cbar.set_label("Kendall $\\tau$ (rank agreement)")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=400, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(OUT_PATH.with_suffix(".png"), dpi=400, bbox_inches="tight", pad_inches=0.02)

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
