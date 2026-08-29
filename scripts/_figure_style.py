"""Shared matplotlib style for every figure registered in
scripts/build_thesis_assets.py, implementing paper/FIGURE_TABLE_SPEC.md's
global rules (G-3 column width, G-4 typography) in one place so they are
a property of the pipeline, not of each individual plotting script.

Usage:
    from _figure_style import COL_W, FULL_W, apply_style
    apply_style()
    fig, ax = plt.subplots(figsize=(COL_W, COL_W * 0.72), constrained_layout=True)
    ...
    fig.savefig(path, dpi=400, bbox_inches="tight", pad_inches=0.02)
"""
from __future__ import annotations

import matplotlib.pyplot as plt

# IEEE column measures, inches (FIGURE_TABLE_SPEC.md G-3).
COL_W = 3.5
FULL_W = 7.16

# Red-ringed marker convention for a thin cell (n_defined < 20), shared by
# every figure/table that needs it (FIGURE_TABLE_SPEC.md G-5).
THIN_RING_COLOR = "#d62728"
THIN_RING_KW = dict(edgecolor=THIN_RING_COLOR, facecolor="none",
                     linewidth=1.8, zorder=5)


def apply_style() -> None:
    """Call once at the top of a plotting script's main(), before creating
    any figure. One font-size scheme across every figure (FIGURE_TABLE_SPEC.md
    G-4): axis labels 7pt, tick labels 6pt, annotations/legend 6pt (reduced
    one point project-wide per author request, 2026-08-29)."""
    plt.rcParams.update({
        "font.size": 7,
        "axes.titlesize": 7,
        "axes.labelsize": 7,
        "xtick.labelsize": 6,
        "ytick.labelsize": 6,
        "legend.fontsize": 6,
        "figure.titlesize": 7,
    })
