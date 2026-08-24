"""Plot the end-to-end pipeline flow diagram used in the supporting report
and the slide deck: template corpus through to hypothesis testing, with
the two scoring gates marked and the three consuming experiments shown
branching off the result record.

This diagram is structural, not derived from analysis/*.csv data, so it
carries no PROVENANCE.md sidecar the way a data plot would -- there is no
data population to cite. It still lives in the registered asset pipeline
(scripts/build_thesis_assets.py) so it regenerates from this script, not
from a hand-edited image.

Usage: python scripts/plot_flow_diagram.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "analysis" / "figures" / "flow_diagram.png"

# Colour language: grey = pipeline step, orange = gate, blue = experiment
# that consumes the result record, green = final analysis step.
COLOR_STEP = "#e8ecf1"
COLOR_STEP_EDGE = "#3b4a5a"
COLOR_GATE = "#fde3cf"
COLOR_GATE_EDGE = "#c9601a"
COLOR_EXPERIMENT = "#dbe9fb"
COLOR_EXPERIMENT_EDGE = "#1f5aa8"
COLOR_FINAL = "#dcf3df"
COLOR_FINAL_EDGE = "#217a3a"
COLOR_INPUT = "#f0e6f7"
COLOR_INPUT_EDGE = "#6a3d9a"

FIG_W, FIG_H = 15.5, 8.6


def box(ax, x, y, w, h, text, face, edge, fontsize=10.3, weight="normal", zorder=3):
    b = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.6, edgecolor=edge, facecolor=face, zorder=zorder,
    )
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
             fontsize=fontsize, weight=weight, color="#1a1a1a", zorder=zorder + 1,
             wrap=True)
    return (x, y, w, h)


def arrow(ax, b_from, b_to, side_from="right", side_to="left", color="#3b4a5a",
          style="-|>", lw=1.6, connectionstyle="arc3,rad=0.0"):
    fx, fy, fw, fh = b_from
    tx, ty, tw, th = b_to
    pts = {
        "right": (fx + fw, fy + fh / 2),
        "left": (fx, fy + fh / 2),
        "top": (fx + fw / 2, fy + fh),
        "bottom": (fx + fw / 2, fy),
    }
    tpts = {
        "right": (tx + tw, ty + th / 2),
        "left": (tx, ty + th / 2),
        "top": (tx + tw / 2, ty + th),
        "bottom": (tx + tw / 2, ty),
    }
    a = FancyArrowPatch(pts[side_from], tpts[side_to],
                         arrowstyle=style, mutation_scale=14,
                         linewidth=lw, color=color,
                         connectionstyle=connectionstyle, zorder=2)
    ax.add_patch(a)


def main() -> None:
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    ax.set_xlim(0, FIG_W)
    ax.set_ylim(0, FIG_H)
    ax.axis("off")

    # ---- Row 1: generative pipeline (top) ----
    y1, h1 = 7.0, 1.15
    w_std = 1.85
    gap = 0.28
    x = 0.35

    b_corpus = box(ax, x, y1, w_std, h1,
                    "Template corpus\n60 templates\n4 complexity tiers",
                    COLOR_STEP, COLOR_STEP_EDGE)
    x += w_std + gap
    b_inst = box(ax, x, y1, w_std, h1,
                  "Seeded\ninstantiation\nfresh per evaluation",
                  COLOR_STEP, COLOR_STEP_EDGE)
    x += w_std + gap
    b_problem = box(ax, x, y1, w_std + 0.25, h1,
                     "Problem instance\n+ oracle\n+ precomputed mutants",
                     COLOR_STEP, COLOR_STEP_EDGE)
    x += w_std + 0.25 + gap
    b_prompt = box(ax, x, y1, w_std, h1,
                    "Prompt sent\nto the model",
                    COLOR_STEP, COLOR_STEP_EDGE)
    x += w_std + gap
    b_suite = box(ax, x, y1, w_std, h1,
                   "Generated\ntest suite",
                   COLOR_STEP, COLOR_STEP_EDGE)

    arrow(ax, b_corpus, b_inst)
    arrow(ax, b_inst, b_problem)
    arrow(ax, b_problem, b_prompt)
    arrow(ax, b_prompt, b_suite)

    # Static-benchmark input, merging in above the prompt box.
    b_static = box(ax, b_prompt[0] - 0.05, y1 + h1 + 0.55, w_std + 0.5, 0.85,
                    "ULT / PLT\nreal-world functions,\nposed the same way",
                    COLOR_INPUT, COLOR_INPUT_EDGE, fontsize=9.6)
    arrow(ax, b_static, b_prompt, side_from="bottom", side_to="top",
          color=COLOR_INPUT_EDGE)

    # ---- Row 2: scoring chain ----
    y2 = y1 - 1.85
    h2 = 1.15
    x = b_suite[0]
    b_exec = box(ax, x, y2, w_std, h2,
                  "EXEC GATE\ndoes the suite\nimport and collect?",
                  COLOR_GATE, COLOR_GATE_EDGE, weight="bold")
    x2 = x - (w_std + gap)
    b_base = box(ax, x2, y2, w_std, h2,
                  "BASELINE GATE\ndoes it pass against\nthe real function?",
                  COLOR_GATE, COLOR_GATE_EDGE, weight="bold")
    x3 = x2 - (w_std + gap)
    b_mut = box(ax, x3, y2, w_std, h2,
                 "Mutation scoring\nkilled / survived\nper mutant",
                 COLOR_STEP, COLOR_STEP_EDGE)
    x4 = x3 - (w_std + gap)
    b_record = box(ax, x4, y2, w_std, h2,
                    "Result record\none row per\nproblem attempt",
                    COLOR_STEP, COLOR_STEP_EDGE)

    arrow(ax, b_suite, b_exec, side_from="bottom", side_to="right",
          connectionstyle="arc3,rad=0.35")
    arrow(ax, b_exec, b_base, side_from="left", side_to="right")
    arrow(ax, b_base, b_mut, side_from="left", side_to="right")
    arrow(ax, b_mut, b_record, side_from="left", side_to="right")

    # Gate failure exits: short stubs tucked immediately under each gate,
    # well clear of the fan-out arrows below (row 3 starts much lower).
    for gbox, label in ((b_exec, "fails: not scorable"), (b_base, "fails: Mut@K excluded")):
        gx, gy, gw, gh = gbox
        ax.add_patch(FancyArrowPatch((gx + gw / 2, gy), (gx + gw / 2, gy - 0.28),
                                      arrowstyle="-|>", mutation_scale=10,
                                      linewidth=1.3, color=COLOR_GATE_EDGE,
                                      linestyle="--", zorder=2))
        ax.text(gx + gw / 2, gy - 0.36, label, ha="center", va="top",
                 fontsize=8.0, color=COLOR_GATE_EDGE, style="italic")

    # ---- Row 3: three consuming experiments ----
    y3 = y2 - 2.75
    h3 = 1.05
    w3 = 3.1
    gap3 = 0.4
    total_w3 = 3 * w3 + 2 * gap3
    x_start = (FIG_W - total_w3) / 2

    b_a = box(ax, x_start, y3, w3, h3,
               "Comparison A\nDynamic vs ULT\nobservational, H1 Test 1",
               COLOR_EXPERIMENT, COLOR_EXPERIMENT_EDGE, fontsize=9.6)
    b_b = box(ax, x_start + w3 + gap3, y3, w3, h3,
               "Comparison B\nULT vs its leaked twin PLT\nobservational, H1 Test 2",
               COLOR_EXPERIMENT, COLOR_EXPERIMENT_EDGE, fontsize=9.6)
    b_c = box(ax, x_start + 2 * (w3 + gap3), y3, w3, h3,
               "Fine-tuning probe\nfine-tune on ULT, re-score\ncausal, H2",
               COLOR_EXPERIMENT, COLOR_EXPERIMENT_EDGE, fontsize=9.6)

    for b in (b_a, b_b, b_c):
        arrow(ax, b_record, b, side_from="bottom", side_to="top",
              connectionstyle="arc3,rad=0.0", color=COLOR_EXPERIMENT_EDGE)

    # ---- Row 4: final analysis step ----
    y4 = y3 - 1.55
    h4 = 1.0
    b_final = box(ax, x_start + (total_w3 - 4.3) / 2, y4, 4.3, h4,
                   "Analysis and hypothesis tests\nH1-H6, Holm-Bonferroni corrected",
                   COLOR_FINAL, COLOR_FINAL_EDGE, weight="bold")
    for b in (b_a, b_b, b_c):
        arrow(ax, b, b_final, side_from="bottom", side_to="top",
              color=COLOR_FINAL_EDGE)

    # ---- Legend ----
    legend_elems = [
        Line2D([0], [0], marker="s", color="none", markerfacecolor=COLOR_STEP,
               markeredgecolor=COLOR_STEP_EDGE, markersize=14, label="Pipeline step"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=COLOR_GATE,
               markeredgecolor=COLOR_GATE_EDGE, markersize=14, label="Scoring gate"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=COLOR_INPUT,
               markeredgecolor=COLOR_INPUT_EDGE, markersize=14, label="Static-benchmark input"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=COLOR_EXPERIMENT,
               markeredgecolor=COLOR_EXPERIMENT_EDGE, markersize=14, label="Experiment"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=COLOR_FINAL,
               markeredgecolor=COLOR_FINAL_EDGE, markersize=14, label="Analysis"),
    ]
    ax.legend(handles=legend_elems, loc="lower left", bbox_to_anchor=(0.0, -0.02),
               ncol=5, frameon=False, fontsize=9.5, handletextpad=0.4, columnspacing=1.1)

    ax.set_title(
        "Dynamic benchmark: from template to hypothesis test",
        fontsize=14.5, weight="bold", pad=14, loc="left", x=0.01,
    )

    fig.tight_layout(rect=(0, 0.02, 1, 1))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=200, bbox_inches="tight")
    fig.savefig(OUT_PATH.with_suffix(".pdf"), bbox_inches="tight")
    print(f"Saved: {OUT_PATH} and {OUT_PATH.with_suffix('.pdf').name}")


if __name__ == "__main__":
    main()
