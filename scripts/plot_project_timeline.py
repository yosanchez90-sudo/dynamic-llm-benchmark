"""Plot the project timeline for the supporting report: the six gated
phases as planned, against the real, dated deviations already described
in prose in section 2.1 (phases brought forward, the fifth-instantiation
cut, the corpus sign-off, the contamination-comparison completion, the
experimental freeze) -- a schedule shown as a figure, not only described
in prose.

Deliberately NOT a precision Gantt chart with invented week boundaries: this
project's own records give six phases in planned order and four specific
dated events, not a day-by-day schedule for phases 1-3. Inventing exact
week numbers for what isn't logged would be exactly the kind of unsourced
figure this project's own citation discipline exists to prevent. The top
row shows the six phases in their PLANNED sequential order (equal-width
bands, no date axis); the bottom row plots the four real, dated events on
an actual calendar axis, with a connecting line showing which planned phase
each belongs to -- this is what actually demonstrates the "brought forward,
out of strict order" deviation section 2.1 describes in prose: the Phase-2
gate (2026-07-25) closes chronologically AFTER the Phase-4-era stability
signal that drove the 2026-07-15 cut decision.

Structural + a handful of real dates, not a data-derived analysis figure;
no PROVENANCE.md sidecar, same reasoning as plot_flow_diagram.py.

Usage: python scripts/plot_project_timeline.py
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "analysis" / "figures" / "project_timeline.png"

PHASES = [
    "Phase 1\nScope freeze",
    "Phase 2\nTemplate corpus\n+ engine",
    "Phase 3\nScoring pipeline\n+ pilot",
    "Phase 4\nComparison A,\nstability, sweep",
    "Phase 5\nContamination\ncomparisons",
    "Phase 6\nWrite-up",
]

# (date, label, which planned phase it belongs to (0-indexed))
EVENTS = [
    (dt.date(2026, 7, 15), "5th-instantiation\ncut decision", 3),
    (dt.date(2026, 7, 25), "Phase 2 gate:\ncorpus sign-off", 1),
    (dt.date(2026, 7, 27), "Phase 5 complete:\nComparisons B, C", 4),
    (dt.date(2026, 8, 12), "Experimental freeze:\nPhase 6 begins", 5),
]

PHASE_COLOR = "#dbe9fb"
PHASE_EDGE = "#1f5aa8"
EVENT_COLOR = "#fbe0d6"
EVENT_EDGE = "#c0392b"


def main() -> None:
    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(7.16, 3.6), gridspec_kw={"height_ratios": [1, 1.3]}
    )

    # --- Top: the six phases, planned sequential order (no date axis) -----
    n = len(PHASES)
    for i, label in enumerate(PHASES):
        b = FancyBboxPatch((i, 0), 0.92, 1, boxstyle="round,pad=0.02,rounding_size=0.05",
                            linewidth=1.4, edgecolor=PHASE_EDGE, facecolor=PHASE_COLOR, zorder=3)
        ax_top.add_patch(b)
        ax_top.text(i + 0.46, 0.5, label, ha="center", va="center", fontsize=6.2, zorder=4)
    ax_top.set_xlim(-0.15, n + 0.05)
    ax_top.set_ylim(0, 1)
    ax_top.axis("off")
    ax_top.set_title("Planned (sixteen weeks, six gated phases, strict order)",
                      fontsize=7, loc="left")

    # --- Bottom: the four real, dated deviation events on a date axis -----
    dates = [e[0] for e in EVENTS]
    xmin = dates[0] - dt.timedelta(days=10)
    xmax = dates[-1] + dt.timedelta(days=6)
    # 2026-07-25 and 2026-07-27 are only two days apart: stagger their label
    # heights so the two annotations don't collide (confirmed at render time).
    stagger_above = [14, 40, 14, 14]
    stagger_below = [-28, -54, -28, -28]
    for (date, label, phase_idx), y_above, y_below in zip(EVENTS, stagger_above, stagger_below):
        ax_bot.axvline(date, color=EVENT_EDGE, linewidth=0.9, alpha=0.5, zorder=1)
        ax_bot.scatter([date], [0], color=EVENT_EDGE, s=28, zorder=3)
        ax_bot.annotate(f"{label}\n{date.isoformat()}", (date, 0), xytext=(0, y_above),
                         textcoords="offset points", ha="center", fontsize=5.6,
                         color="#333333")
        # connector to the planned phase it belongs to, showing out-of-order
        # phase work (FIGURE_TABLE_SPEC.md-style annotation, not a title)
        ax_bot.annotate(f"belongs to Phase {phase_idx + 1}", (date, 0), xytext=(0, y_below),
                         textcoords="offset points", ha="center", fontsize=5.2,
                         color=EVENT_EDGE, style="italic")
    ax_bot.set_xlim(xmin, xmax)
    ax_bot.set_ylim(-1.6, 1.6)
    ax_bot.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax_bot.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    plt.setp(ax_bot.get_xticklabels(), rotation=30, ha="right", fontsize=5.5)
    ax_bot.get_yaxis().set_visible(False)
    for spine in ("top", "left", "right"):
        ax_bot.spines[spine].set_visible(False)
    ax_bot.set_title("Actual: dated deviations (2026-07-15 to 2026-08-12) -- note the "
                      "Phase 2 gate closes chronologically after the Phase-4-era signal "
                      "that drove the 5th-instantiation cut", fontsize=6.3, loc="left")

    fig.tight_layout(pad=0.6)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight", pad_inches=0.03)
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
