"""Collapse vs survival -- one argument per figure: raw conditional Mut@K's
correlation with BigCodeBench collapses once family diversity breaks the
all-Qwen n=3 size-sweep confound; the coverage-adjusted score's does not.
2x2 panels: rows = metric (raw Mut@K, coverage-adjusted), columns = scope
(canonical-only n=3, canonical+cross-family n=7), Dynamic<->BigCodeBench
(Complete-split). The n=3 columns are marked uninformative-by-construction:
only 3!=6 possible orderings exist at n=3, so the minimum achievable
two-sided permutation p-value is 2/6~=0.33 (verified directly against this
project's own permutation test in src/Analysis/correlation.py -- NOT 1/6
(~0.167), which would be a one-sided-only floor this project's own
two-sided |stat|>=|observed| test does not implement).

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


def _panel(ax, df, col_a, col_b, corr_row, is_n3: bool, thin_col: str | None):
    sub = df.dropna(subset=[col_a, col_b])
    for _, row in sub.iterrows():
        color, marker = _style(row["model_short"])
        is_thin = bool(row.get(thin_col, False)) if thin_col else False
        ax.scatter(row[col_a], row[col_b], color=color, marker=marker,
                   s=90 if not is_thin else 90, zorder=3,
                   edgecolor=("#d62728" if is_thin else "white"),
                   linewidth=(1.6 if is_thin else 0.6))
        ax.annotate(row["model_short"], (row[col_a], row[col_b]),
                    fontsize=7.5, xytext=(5, 4), textcoords="offset points")
    ax.set_xlabel("Dynamic (pooled)", fontsize=9.5)
    ax.set_ylabel("BigCodeBench Pass@1 (Complete-split)", fontsize=9.5)
    ax.grid(True, linestyle="--", alpha=0.4)
    if corr_row is not None:
        n = int(corr_row["n"])
        tau = corr_row["kendall_tau"]
        p = corr_row["kendall_p_perm"]
        title = f"n_models={n}  Kendall τ={tau:.3f}  p={p:.4f}"
        ax.set_title(title, fontsize=9.5)
    if is_n3:
        ax.text(0.03, 0.03,
                f"n_models=3: uninformative by construction\n(only 6 possible orderings;\nmin two-sided perm. p={MIN_P_AT_N3:.3f})",
                transform=ax.transAxes, fontsize=7.5, color="#d62728", ha="left", va="bottom",
                bbox=dict(boxstyle="round,pad=0.3", fc="#fff0f0", ec="#d62728", alpha=0.9, linewidth=0.6))


def main() -> None:
    ranking = pd.read_csv(RANKING_CSV)
    corr = pd.read_csv(CORR_CSV) if CORR_CSV.exists() else pd.DataFrame()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    canonical_only = ranking[ranking["family"] == "canonical"]

    rows_spec = [
        ("raw Mut@K", "dynamic_mutk_pooled", "public_score",
         "Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]", "dynamic_thin"),
        ("coverage-adjusted", "dynamic_coverage_adj", "public_score",
         "Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]", "dynamic_thin"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))

    for r, (metric_label, col_a, col_b, pair_name, thin_col) in enumerate(rows_spec):
        for c, (scope_df, scope_label, is_n3) in enumerate([
            (canonical_only, "canonical-only", True),
            (ranking, "canonical+cross-family", False),
        ]):
            ax = axes[r][c]
            corr_row = None
            if len(corr):
                match = corr[(corr["pair"] == pair_name) & (corr["scope"] == scope_label)]
                if len(match):
                    corr_row = match.iloc[0]
            _panel(ax, scope_df, col_a, col_b, corr_row, is_n3, thin_col)
            ax.text(0.03, 0.97, f"{metric_label} | {scope_label}", transform=ax.transAxes,
                    fontsize=8.5, color="dimgray", ha="left", va="top", style="italic")

    # red-ringed markers = thin cell (n_defined<20 on the Dynamic side) --
    # same visual convention as the ranking-matrix heatmap / noise-floor
    # figures (analysis/FIGURE_AUDIT.md's visual-grammar section).
    from matplotlib.lines import Line2D
    thin_handle = Line2D([0], [0], marker='o', color='w', markerfacecolor='#7f7f7f',
                         markeredgecolor='#d62728', markeredgewidth=1.6, markersize=9,
                         label='thin cell (n_defined<20)')
    fig.legend(handles=[thin_handle], loc="lower center", fontsize=8.5, ncol=1, bbox_to_anchor=(0.5, -0.01))

    fig.suptitle(
        "Collapse vs survival: raw Mut@K's BigCodeBench correlation collapses once\n"
        "cross-family diversity breaks the all-Qwen size-sweep confound; coverage-adjusted survives",
        fontsize=11.5,
    )
    fig.tight_layout(rect=[0, 0.02, 1, 0.90])
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_PATH.with_suffix(".png"), dpi=150, bbox_inches="tight")

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
