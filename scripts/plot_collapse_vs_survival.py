"""Collapse vs survival, one argument per figure: raw conditional Mut@K's
correlation with BigCodeBench collapses once family diversity breaks the
all-Qwen n=3 size-sweep confound; the coverage-adjusted score's does not.
Two panels, stacked (rows = metric: raw Mut@K, coverage-adjusted), both at
the cross-family (n=7) scope, DyMuT<->BigCodeBench (Complete-split). The
canonical-only n=3 scope is deliberately not plotted here (dropped
2026-08-27, print-legibility pass): it is uninformative by construction --
only 3!=6 possible orderings exist at n=3, so the minimum achievable
two-sided permutation p-value is 2/6~=0.33 (verified directly against this
project's own permutation test in src/Analysis/correlation.py, NOT 1/6
(~0.167), which would be a one-sided-only floor this project's own
two-sided |stat|>=|observed| test does not implement) -- and the paper's
own caption for this figure only ever describes the cross-family message,
so dropping the n=3 column loses no claim the caption relies on. Panels
are stacked one-per-row, not side by side, and sized close to the paper's
actual single-column print width, so \\includegraphics[width=\\columnwidth]
barely rescales the figure and in-panel text stays close to its authored
size instead of shrinking by the ~3x a wide multi-panel layout would need.

Usage: python scripts/plot_collapse_vs_survival.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.Analysis.provenance import stamp_block
from _figure_style import COL_W, apply_style

RANKING_CSV = ROOT / "analysis" / "rq5_cross_family_model_ranking.csv"
CORR_CSV = ROOT / "analysis" / "rq5_cross_family_correlations.csv"
OUT_PATH = ROOT / "analysis" / "figures" / "collapse_vs_survival.pdf"

FAMILY_STYLE = {
    "Qwen": ("#2ca02c", "o"), "DeepSeek": ("#ff7f0e", "^"), "CodeLlama": ("#8c564b", "^"),
    "StarCoder2": ("#17becf", "^"), "Mistral": ("#e377c2", "^"),
}
MIN_P_AT_N3 = 2 / 6  # exact: only the identity + full-reversal permutation match |tau|>=|observed|=1


def _style(model_short: str) -> tuple[str, str]:
    for key, style in FAMILY_STYLE.items():
        if key.lower() in model_short.lower():
            return style
    return "#7f7f7f", "o"


def _panel(ax, df, col_a, col_b, corr_row, thin_col: str | None, metric_label: str, panel_id: str):
    sub = df.dropna(subset=[col_a, col_b])
    for _, row in sub.iterrows():
        color, marker = _style(row["model_short"])
        is_thin = bool(row.get(thin_col, False)) if thin_col else False
        ax.scatter(row[col_a], row[col_b], color=color, marker=marker,
                   s=45, zorder=3,
                   edgecolor=("#d62728" if is_thin else "white"),
                   linewidth=(1.6 if is_thin else 0.5))
        ax.annotate(row["model_short"], (row[col_a], row[col_b]),
                    fontsize=6, xytext=(5, 4), textcoords="offset points")
    ax.set_xlabel(f"DyMuT (pooled), {metric_label}")
    ax.set_ylabel("BigCodeBench Pass@1\n(Complete-split)")
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.4)
    ax.margins(x=0.22, y=0.14)
    ax.text(0.02, 0.96, panel_id, transform=ax.transAxes, fontsize=7, fontweight="bold", va="top")
    if corr_row is not None:
        n = int(corr_row["n"])
        tau = corr_row["kendall_tau"]
        p = corr_row["kendall_p_perm"]
        ax.text(0.98, 0.04, f"$n$={n}  $\\tau$={tau:.3f}  $p$={p:.4f}",
                transform=ax.transAxes, fontsize=6, ha="right", va="bottom",
                color="#333333")


def main() -> None:
    apply_style()
    ranking = pd.read_csv(RANKING_CSV)
    corr = pd.read_csv(CORR_CSV) if CORR_CSV.exists() else pd.DataFrame()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows_spec = [
        ("raw Mut@K", "dynamic_mutk_pooled", "public_score",
         "Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]", "dynamic_thin", "(a)"),
        ("coverage-adjusted", "dynamic_coverage_adj", "public_score",
         "Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]", "dynamic_thin", "(b)"),
    ]
    # Single column, stacked, at the actual column width (FIGURE_TABLE_SPEC.md
    # G-3): \includegraphics[width=\columnwidth] applies almost no further
    # shrink, so in-panel text stays close to its authored size.
    fig, axes = plt.subplots(2, 1, figsize=(COL_W, 2 * COL_W * 0.52), constrained_layout=True)

    for ax, (metric_label, col_a, col_b, pair_name, thin_col, panel_id) in zip(axes, rows_spec):
        corr_row = None
        if len(corr):
            match = corr[(corr["pair"] == pair_name) & (corr["scope"] == "canonical+cross-family")]
            if len(match):
                corr_row = match.iloc[0]
        _panel(ax, ranking, col_a, col_b, corr_row, thin_col, metric_label, panel_id)

    # red-ringed markers = thin cell (n_defined<20 on the Dynamic side) --
    # same visual convention as the ranking-matrix heatmap / noise-floor
    # figures (analysis/FIGURE_AUDIT.md's visual-grammar section). The
    # argument this figure makes ("raw Mut@K's correlation collapses under
    # added model diversity; coverage-adjusted survives") lives in the
    # paper caption now, not as an in-figure suptitle (FIGURE_TABLE_SPEC.md
    # G-1: a plot title duplicates the caption and wastes vertical space).
    from matplotlib.lines import Line2D
    thin_handle = Line2D([0], [0], marker='o', color='w', markerfacecolor='#7f7f7f',
                         markeredgecolor='#d62728', markeredgewidth=1.6, markersize=6,
                         label='thin cell ($n_{\\mathrm{defined}}$<20)')
    fig.legend(handles=[thin_handle], loc="lower center", ncol=1,
               bbox_to_anchor=(0.5, -0.05), frameon=False)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=400, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(OUT_PATH.with_suffix(".png"), dpi=400, bbox_inches="tight", pad_inches=0.02)

    provenance = f"""# Collapse vs survival figure — provenance

{stamp_block("scripts/plot_collapse_vs_survival.py")}
Sources: {RANKING_CSV.relative_to(ROOT)}, {CORR_CSV.relative_to(ROOT)}.
n=3 minimum achievable two-sided permutation p-value ({MIN_P_AT_N3:.4f})
verified directly against src/Analysis/correlation.py's _permutation_p()
(two-sided |stat|>=|observed| test, not one-sided), NOT the 1/6~=0.167
one-sided figure, which this project's own test does not compute. Thin
cells (n_defined<20) ringed in red, same convention as
analysis/figures/ranking_matrix_heatmap.pdf and noise_floor.pdf.

Output: {OUT_PATH.relative_to(ROOT)} (+ .png).
"""
    PROVENANCE_OUT = ROOT / "analysis" / (OUT_PATH.stem + "_PROVENANCE.md")
    PROVENANCE_OUT.write_text(provenance)
    print(f"Saved: {OUT_PATH} and .png, {PROVENANCE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
