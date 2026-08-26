"""RQ5 cross-family extension scatter figure(s), shows raw Mut@K vs the
coverage-adjusted score side by side, canonical models vs the 4 cross-family
candidates distinguished by marker, for both Dynamic<->ULT and
Dynamic<->public (BigCodeBench). The panel layout is chosen to
make the finding visible: the raw metric's correlation collapses once
cross-family points are added, the coverage-adjusted one does not.

Usage: python scripts/plot_rq5_cross_family_correlation.py
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
OUT_PATH = ROOT / "analysis" / "figures" / "rq5_cross_family_correlation.pdf"

FAMILY_STYLE = {
    "Qwen": ("#2ca02c", "o"), "gpt": ("#d62728", "o"), "claude": ("#1f77b4", "o"),
    "gemini": ("#9467bd", "o"), "DeepSeek": ("#ff7f0e", "^"), "CodeLlama": ("#8c564b", "^"),
    "StarCoder2": ("#17becf", "^"), "Mistral": ("#e377c2", "^"),
}


def _style(model_short: str) -> tuple[str, str]:
    for key, style in FAMILY_STYLE.items():
        if key.lower() in model_short.lower():
            return style
    return "#7f7f7f", "o"


def _scatter_panel(ax, df, col_a, col_b, label_a, label_b, corr_row):
    sub = df.dropna(subset=[col_a, col_b])
    for _, row in sub.iterrows():
        color, marker = _style(row["model_short"])
        ax.scatter(row[col_a], row[col_b], color=color, marker=marker,
                   s=70, zorder=3, edgecolor="white", linewidth=0.6)
        ax.annotate(row["model_short"], (row[col_a], row[col_b]),
                    fontsize=7, xytext=(4, 3), textcoords="offset points")
    ax.set_xlabel(label_a, fontsize=9.5)
    ax.set_ylabel(label_b, fontsize=9.5)
    ax.grid(True, linestyle="--", alpha=0.4)
    if corr_row is not None:
        n = int(corr_row["n"])
        tau = corr_row["kendall_tau"]
        p = corr_row["kendall_p_perm"]
        ax.set_title(f"n={n}  Kendall τ={tau:.3f}  p={p:.4f}", fontsize=9)


def main() -> None:
    ranking = pd.read_csv(RANKING_CSV)
    corr = pd.read_csv(CORR_CSV) if CORR_CSV.exists() else pd.DataFrame()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    canonical_only = ranking[ranking["family"] == "canonical"]

    # Panels: (df, col_a, col_b, label_a, label_b, pair_name, scope)
    panels = [
        (canonical_only, "dynamic_mutk_pooled", "ult_mutk", "Dynamic Mut@K", "ULT Mut@K",
         "Dynamic(pooled) <-> ULT [raw Mut@K]", "canonical-only"),
        (ranking, "dynamic_mutk_pooled", "ult_mutk", "Dynamic Mut@K", "ULT Mut@K",
         "Dynamic(pooled) <-> ULT [raw Mut@K]", "canonical+cross-family"),
        (canonical_only, "dynamic_coverage_adj", "ult_coverage_adj", "Dynamic coverage-adj.", "ULT coverage-adj.",
         "Dynamic(pooled) <-> ULT [coverage-adjusted]", "canonical-only"),
        (ranking, "dynamic_coverage_adj", "ult_coverage_adj", "Dynamic coverage-adj.", "ULT coverage-adj.",
         "Dynamic(pooled) <-> ULT [coverage-adjusted]", "canonical+cross-family"),
    ]
    if "public_score" in ranking.columns:
        panels += [
            (canonical_only, "dynamic_mutk_pooled", "public_score", "Dynamic Mut@K", "BigCodeBench (Instruct)",
             "Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]", "canonical-only"),
            (ranking, "dynamic_mutk_pooled", "public_score", "Dynamic Mut@K", "BigCodeBench (Instruct)",
             "Dynamic(pooled) <-> public (Complete-split/Instruct) [raw Mut@K]", "canonical+cross-family"),
            (canonical_only, "dynamic_coverage_adj", "public_score", "Dynamic coverage-adj.", "BigCodeBench (Instruct)",
             "Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]", "canonical-only"),
            (ranking, "dynamic_coverage_adj", "public_score", "Dynamic coverage-adj.", "BigCodeBench (Instruct)",
             "Dynamic(pooled) <-> public (Complete-split/Instruct) [coverage-adjusted]", "canonical+cross-family"),
        ]

    ncols = 4
    nrows = (len(panels) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(6.0 * ncols, 5.0 * nrows), squeeze=False)
    flat_axes = axes.flatten()

    for ax, (df, col_a, col_b, label_a, label_b, pair_name, scope) in zip(flat_axes, panels):
        corr_row = None
        if len(corr):
            match = corr[(corr["pair"] == pair_name) & (corr["scope"] == scope)]
            if len(match):
                corr_row = match.iloc[0]
        _scatter_panel(ax, df, col_a, col_b, label_a, label_b, corr_row)
        ax.text(0.02, 0.98, scope, transform=ax.transAxes, fontsize=8, color="dimgray",
                ha="left", va="top", style="italic")
    for ax in flat_axes[len(panels):]:
        ax.set_visible(False)

    fig.suptitle(
        "RQ5 cross-family extension: raw Mut@K's cross-benchmark agreement collapses "
        "once family diversity is added; the coverage-adjusted score's does not",
        fontsize=11,
    )
    fig.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_PATH.with_suffix(".png"), dpi=150, bbox_inches="tight")

    provenance = f"""# RQ5 cross-family correlation scatter figure(s) — provenance

{stamp_block("scripts/plot_rq5_cross_family_correlation.py")}
Sources: {RANKING_CSV.relative_to(ROOT)}, {CORR_CSV.relative_to(ROOT)}.
Panels plotted this run ({len(panels)}): canonical-only vs canonical+cross-family,
raw Mut@K vs coverage-adjusted, for Dynamic<->ULT and Dynamic<->public
(BigCodeBench Complete-split/Instruct-prompt).

Output: {OUT_PATH.relative_to(ROOT)} (+ .png).
"""
    PROVENANCE_OUT = ROOT / "analysis" / (OUT_PATH.stem + "_PROVENANCE.md")
    PROVENANCE_OUT.write_text(provenance)
    print(f"Saved: {OUT_PATH} and .png, {PROVENANCE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
