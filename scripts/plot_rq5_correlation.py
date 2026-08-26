"""RQ5/H6 correlation scatter figure(s), one panel per benchmark pair
that has data (analysis/rq5_model_ranking.csv), each point labelled with
its model's short name. Styled consistent with this project's other
figures (scripts/plot_epoch_perf.py, scripts/plot_comparison_c_onset_curve.py).

Usage: python scripts/plot_rq5_correlation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.Analysis.provenance import stamp_block

RANKING_CSV = ROOT / "analysis" / "rq5_model_ranking.csv"
CORR_CSV = ROOT / "analysis" / "rq5_correlations.csv"
OUT_PATH = ROOT / "analysis" / "figures" / "rq5_correlation.pdf"

PROVIDER_COLOR = {
    "Qwen": "#2ca02c", "gpt": "#d62728", "claude": "#1f77b4", "gemini": "#9467bd",
}


def _provider_color(model_label: str) -> str:
    for key, color in PROVIDER_COLOR.items():
        if key.lower() in model_label.lower():
            return color
    return "#7f7f7f"


def _scatter_panel(ax, df, col_a, col_b, label_a, label_b, corr_row):
    sub = df.dropna(subset=[col_a, col_b])
    for _, row in sub.iterrows():
        ax.scatter(row[col_a], row[col_b], color=_provider_color(row["model_label"]),
                   s=70, zorder=3, edgecolor="white", linewidth=0.6)
        ax.annotate(row["model_short"], (row[col_a], row[col_b]),
                    fontsize=7.5, xytext=(4, 3), textcoords="offset points")
    ax.set_xlabel(label_a, fontsize=10)
    ax.set_ylabel(label_b, fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.4)
    if corr_row is not None:
        n = int(corr_row["n"])
        r = corr_row["pearson_r"]
        rho = corr_row["spearman_rho"]
        tau = corr_row["kendall_tau"]
        ax.set_title(f"n={n}  Pearson r={r:.2f}  Spearman ρ={rho:.2f}  Kendall τ={tau:.2f}",
                     fontsize=9.5)


def main() -> None:
    ranking = pd.read_csv(RANKING_CSV)
    corr = pd.read_csv(CORR_CSV) if CORR_CSV.exists() else pd.DataFrame()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pairs = [
        ("dynamic_mutk_pooled", "ult_mutk", "Dynamic Mut@K (pooled, all tiers)", "ULT Mut@K (core_400)",
         "Dynamic(pooled) <-> ULT"),
    ]
    if "public_score" in ranking.columns:
        pairs.append(("dynamic_mutk_pooled", "public_score", "Dynamic Mut@K (pooled)",
                      "BigCodeBench Pass@1 (Complete-split)", "Dynamic(pooled) <-> public (Complete-split)"))
        pairs.append(("ult_mutk", "public_score", "ULT Mut@K (core_400)",
                      "BigCodeBench Pass@1 (Complete-split)", "ULT <-> public (Complete-split)"))

    fig, axes = plt.subplots(1, len(pairs), figsize=(6.5 * len(pairs), 5.5), squeeze=False)
    axes = axes[0]

    for ax, (col_a, col_b, label_a, label_b, pair_name) in zip(axes, pairs):
        corr_row = corr[corr["pair"] == pair_name].iloc[0] if (len(corr) and pair_name in corr["pair"].values) else None
        _scatter_panel(ax, ranking, col_a, col_b, label_a, label_b, corr_row)

    fig.suptitle("RQ5: cross-benchmark score correlation (one point per model)", fontsize=12)
    fig.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_PATH.with_suffix(".png"), dpi=150, bbox_inches="tight")

    provenance = f"""# RQ5 correlation scatter figure(s) — provenance

{stamp_block("scripts/plot_rq5_correlation.py")}
Sources: {RANKING_CSV.relative_to(ROOT)}, {CORR_CSV.relative_to(ROOT)}.
Panels plotted this run: {[p[4] for p in pairs]}.

Output: {OUT_PATH.relative_to(ROOT)} (+ .png).
"""
    # NOT alongside the figure: analysis/figures/ is entirely gitignored
    # (.gitignore:49), so a sidecar written there would never be committed --
    # defeating the point of stamping it. Root of analysis/, like every other
    # *_PROVENANCE.md, is only ignored for .csv/.xlsx (.gitignore:47-48).
    PROVENANCE_OUT = ROOT / "analysis" / (OUT_PATH.stem + "_PROVENANCE.md")
    PROVENANCE_OUT.write_text(provenance)
    print(f"Saved: {OUT_PATH} and .png, {PROVENANCE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
