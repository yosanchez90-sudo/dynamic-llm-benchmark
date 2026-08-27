"""Plot H5's score-level stability result (RUBRIC_ACTION_PLAN.md PA-3):
each canonical model's StableMut@K, mean +/- SD across benchmark
re-instantiations, as a point-with-error-bar plot. Makes the paper's own
"SD is tiny, but rank agreement (tau) is not" argument (Section 4.6)
visible directly: every error bar is a sliver relative to the score axis,
while Figure 3's pairwise tau values are far from 1.0.

Read live from analysis/stability_stablemut.csv (itself produced by
scripts/analyze_stability.py), the same source Section 4.6's prose draws on.

Usage: python scripts/plot_h5_stability.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from _figure_style import COL_W, apply_style  # noqa: E402

STABLE = ROOT / "analysis" / "stability_stablemut.csv"
OUT_PATH = ROOT / "analysis" / "figures" / "h5_stability.pdf"

SHORT_NAME = {
    "gpt-5-2025-08-07": "GPT-5",
    "gpt-5-mini-2025-08-07": "GPT-5-mini",
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro Preview",
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite",
    "Qwen__Qwen2.5-Coder-32B-Instruct": "Qwen 32B",
    "Qwen__Qwen2.5-Coder-7B-Instruct": "Qwen 7B",
    "Qwen__Qwen2.5-Coder-1.5B-Instruct": "Qwen 1.5B",
}


def main() -> None:
    apply_style()
    df = pd.read_csv(STABLE)
    df["short"] = df["model_label"].map(SHORT_NAME)
    df = df.sort_values("stable_mut_at_k", ascending=True).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(COL_W, COL_W * 0.85), constrained_layout=True)
    y = range(len(df))
    ax.errorbar(df["stable_mut_at_k"], y, xerr=df["sd_mut_at_k"],
                fmt="o", color="#1f77b4", ecolor="#1f77b4", elinewidth=1.3,
                capsize=2.5, markersize=4, linewidth=0)
    ax.set_yticks(list(y))
    ax.set_yticklabels(df["short"])
    ax.set_xlabel("StableMut@K (mean $\\pm$ SD)")
    ax.set_xlim(0, 1.18)
    ax.grid(True, axis="x", linewidth=0.4, alpha=0.5)
    for yi, (_, row) in zip(y, df.iterrows()):
        ax.annotate(f"n={int(row['n_instantiations'])}",
                     (row["stable_mut_at_k"] + row["sd_mut_at_k"] + 0.03, yi),
                     va="center", fontsize=7, color="#555555")
    fig.savefig(OUT_PATH, dpi=400, bbox_inches="tight", pad_inches=0.02)
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
