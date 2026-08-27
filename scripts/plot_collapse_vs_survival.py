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


def _panel(ax, df, col_a, col_b, corr_row, thin_col: str | None, metric_label: str):
    sub = df.dropna(subset=[col_a, col_b])
    for _, row in sub.iterrows():
        color, marker = _style(row["model_short"])
        is_thin = bool(row.get(thin_col, False)) if thin_col else False
        ax.scatter(row[col_a], row[col_b], color=color, marker=marker,
                   s=110, zorder=3,
                   edgecolor=("#d62728" if is_thin else "white"),
                   linewidth=(1.8 if is_thin else 0.6))
        ax.annotate(row["model_short"], (row[col_a], row[col_b]),
                    fontsize=10, xytext=(6, 5), textcoords="offset points")
    ax.set_xlabel("DyMuT (pooled)", fontsize=12)
    ax.set_ylabel("BigCodeBench Pass@1\n(Complete-split)", fontsize=12)
    ax.tick_params(axis="both", labelsize=10.5)
    ax.grid(True, linestyle="--", alpha=0.4)
    if corr_row is not None:
        n = int(corr_row["n"])
        tau = corr_row["kendall_tau"]
        p = corr_row["kendall_p_perm"]
        title = f"{metric_label}\nn_models={n}  Kendall τ={tau:.3f}  p={p:.4f}"
        ax.set_title(title, fontsize=12, pad=8)


def main() -> None:
    ranking = pd.read_csv(RANKING_CSV)
    corr = pd.read_csv(CORR_CSV) if CORR_CSV.exists() else pd.DataFrame()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows_spec = [
        ("raw Mut@K", "dynamic_mutk_pooled", "public_score",
         "Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]", "dynamic_thin"),
        ("coverage-adjusted", "dynamic_coverage_adj", "public_score",
         "Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]", "dynamic_thin"),
    ]
    # Single column, stacked: figsize width is close to the paper's actual
    # printed column width, so \includegraphics[width=\columnwidth] applies
    # almost no further shrink and in-panel text (10-12pt here) stays well
    # above the ~7pt print-legibility floor instead of the ~3x shrink a
    # side-by-side multi-panel layout at this same content size would need.
    fig, axes = plt.subplots(2, 1, figsize=(3.6, 6.3))

    for r, (metric_label, col_a, col_b, pair_name, thin_col) in enumerate(rows_spec):
        ax = axes[r]
        corr_row = None
        if len(corr):
            match = corr[(corr["pair"] == pair_name) & (corr["scope"] == "canonical+cross-family")]
            if len(match):
                corr_row = match.iloc[0]
        _panel(ax, ranking, col_a, col_b, corr_row, thin_col, metric_label)

    # red-ringed markers = thin cell (n_defined<20 on the Dynamic side) --
    # same visual convention as the ranking-matrix heatmap / noise-floor
    # figures (analysis/FIGURE_AUDIT.md's visual-grammar section).
    from matplotlib.lines import Line2D
    thin_handle = Line2D([0], [0], marker='o', color='w', markerfacecolor='#7f7f7f',
                         markeredgecolor='#d62728', markeredgewidth=1.8, markersize=10,
                         label='thin cell (n_defined<20)')
    fig.legend(handles=[thin_handle], loc="lower center", fontsize=10, ncol=1, bbox_to_anchor=(0.5, -0.06))

    fig.suptitle(
        "Cross-family: raw Mut@K's BigCodeBench\ncorrelation collapses; coverage-adjusted survives",
        fontsize=12.5, y=0.995,
    )
    fig.subplots_adjust(top=0.87, bottom=0.13, hspace=0.55)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=200, bbox_inches="tight")
    fig.savefig(OUT_PATH.with_suffix(".png"), dpi=200, bbox_inches="tight")

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
