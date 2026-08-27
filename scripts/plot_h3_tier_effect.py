"""Plot H3's tier-effect result (RUBRIC_ACTION_PLAN.md PA-3): conditional
Mut@K by complexity tier (L1-L4), one line per canonical model. The
monotone-decline pattern is currently reported only as a sentence
(paper/sections/04_results.tex Section 4.5); this figure makes it visible
directly, following paper/FIGURE_TABLE_SPEC.md's per-figure checklist
(no title, axis-label units, in-figure model labels via a legend since
nine lines have no natural in-axes annotation space).

Read live from analysis/h3_tier_gradient_tier_means.csv (itself produced
by scripts/analyze_h3_tier_gradient.py), the same source Section 4.5's
prose statistics draw on.

Usage: python scripts/plot_h3_tier_effect.py
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

TIER_MEANS = ROOT / "analysis" / "h3_tier_gradient_tier_means.csv"
OUT_PATH = ROOT / "analysis" / "figures" / "h3_tier_effect.pdf"

TIERS = ["L1", "L2", "L3", "L4"]

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

# Colour + marker + linestyle per model, distinguishable in greyscale
# (FIGURE_TABLE_SPEC.md G-5), matching Fig. 1's established convention of
# pairing every colour with a distinct marker/linestyle rather than colour
# alone.
STYLE = {
    "gpt-5-2025-08-07":                  dict(color="#1f77b4", marker="o", ls="-"),
    "gpt-5-mini-2025-08-07":             dict(color="#1f77b4", marker="s", ls="--"),
    "claude-sonnet-4-6":                 dict(color="#d62728", marker="o", ls="-"),
    "claude-haiku-4-5-20251001":         dict(color="#d62728", marker="s", ls="--"),
    "gemini-3.1-pro-preview":            dict(color="#2ca02c", marker="o", ls="-"),
    "gemini-3.1-flash-lite":             dict(color="#2ca02c", marker="s", ls="--"),
    "Qwen__Qwen2.5-Coder-32B-Instruct":  dict(color="#7f3f98", marker="^", ls="-"),
    "Qwen__Qwen2.5-Coder-7B-Instruct":   dict(color="#7f3f98", marker="v", ls="--"),
    "Qwen__Qwen2.5-Coder-1.5B-Instruct": dict(color="#7f3f98", marker="D", ls=":"),
}


def main() -> None:
    apply_style()
    df = pd.read_csv(TIER_MEANS)

    fig, ax = plt.subplots(figsize=(COL_W, COL_W * 0.78), constrained_layout=True)
    for _, row in df.iterrows():
        style = STYLE.get(row["model_label"])
        if style is None:
            continue
        ys = [row.get(f"{t}_mutk") for t in TIERS]
        xs = [i for i, y in enumerate(ys) if pd.notna(y)]
        ys = [y for y in ys if pd.notna(y)]
        ax.plot(xs, ys, label=SHORT_NAME[row["model_label"]], markersize=4, linewidth=1.2, **style)

    ax.set_xticks(range(len(TIERS)))
    ax.set_xticklabels(TIERS)
    ax.set_xlabel("Complexity tier")
    ax.set_ylabel("Conditional Mut@K")
    ax.set_ylim(0, 1.05)
    ax.grid(True, axis="y", linewidth=0.4, alpha=0.5)
    ax.legend(loc="lower left", ncol=2, frameon=False, handlelength=1.6,
               columnspacing=0.8, labelspacing=0.3)
    fig.savefig(OUT_PATH, dpi=400, bbox_inches="tight", pad_inches=0.02)
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
