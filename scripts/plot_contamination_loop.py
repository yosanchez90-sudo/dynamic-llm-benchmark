"""Plot a simple three-step contamination-loop diagram for the slide deck
and, optionally, the supporting report: a benchmark is published, its
content is scraped or logged into a future training corpus, and a model
evaluated on that benchmark later scores on recall rather than the
capability the benchmark was meant to measure.

Structural, not data-derived; no PROVENANCE.md sidecar, same reasoning
as scripts/plot_flow_diagram.py.

Usage: python scripts/plot_contamination_loop.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "analysis" / "figures" / "contamination_loop.png"

FACE = "#dbe9fb"
EDGE = "#1f5aa8"
FACE_WARN = "#fbe0d6"
EDGE_WARN = "#c0392b"


def box(ax, x, y, w, h, text, face, edge, fontsize=15):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                        linewidth=2.2, edgecolor=edge, facecolor=face, zorder=3)
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
             fontsize=fontsize, weight="bold", color="#1a1a1a", zorder=4)


def curved_arrow(ax, start, end, color, rad):
    a = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=26,
                         linewidth=2.4, color=color,
                         connectionstyle=f"arc3,rad={rad}", zorder=2)
    ax.add_patch(a)


def main() -> None:
    fig, ax = plt.subplots(figsize=(9, 7.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 9)
    ax.axis("off")

    box(ax, 3.1, 6.4, 3.8, 1.5, "Benchmark\npublished", FACE, EDGE)
    box(ax, 0.3, 2.6, 4.0, 1.5, "Scraped, or logged\nfrom API use", FACE, EDGE)
    box(ax, 5.7, 2.6, 4.0, 1.5, "Absorbed into a\nfuture training run", FACE, EDGE)
    box(ax, 3.0, -0.65 + 0.9, 4.0, 1.5, "Model scores\non recall, not\ncapability", FACE_WARN, EDGE_WARN)

    curved_arrow(ax, (3.9, 6.5), (2.4, 4.15), EDGE, 0.25)
    curved_arrow(ax, (4.4, 2.85), (5.6, 2.85), EDGE, -0.2)
    curved_arrow(ax, (7.3, 2.55), (5.9, 1.25), EDGE_WARN, 0.25)
    curved_arrow(ax, (3.0, 1.35), (3.5, 6.3), color="#888888", rad=-0.55)
    ax.text(1.05, 4.6, "next\nevaluation", ha="center", fontsize=10.5, color="#666666", style="italic")

    ax.set_title("The contamination loop", fontsize=19, weight="bold", pad=16)
    fig.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=200, bbox_inches="tight")
    fig.savefig(OUT_PATH.with_suffix(".pdf"), bbox_inches="tight")
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
