"""Condition-aware epoch-performance comparison plot (seen vs unseen, one
colour per fine-tune condition).

Replaces the ad-hoc script that previously produced
analysis/figures/epoch_perf_{qwen1_5b,qwen7b}_bp_comparison.pdf, which had
two bugs:

  1. Drew every row for every epoch, including the 3 extra
     sampling_seed{42,43,44} rows recorded at epoch 30 only (alongside the
     always-present "greedy" row) -- stacking 4 points at x=30 per
     instantiation into a zigzag / spurious drop instead of a single
     point. Fixed here by filtering to one --draw value (default "greedy",
     the only draw present at every epoch).
  2. Reused the same 3 instantiation colours/labels across every
     overlaid condition on one figure, so the 3 conditions (inst1/bp_own/
     bp_gpt5) were visually indistinguishable from each other. Fixed here
     by colouring by CONDITION (one colour per input CSV) and encoding
     seen-vs-unseen within each condition via line style + marker fill:
       - "seen"   = instantiation 1 (the LoRA training split)   -> solid line, filled marker
       - "unseen" = mean(instantiation 2, instantiation 3)      -> dashed line, open marker
     3 conditions x 2 (seen/unseen) = 6 lines total, not 9, and every
     condition keeps a stable colour across the whole figure.

Column names are auto-detected via the candidate lists below rather than
hardcoded, so minor schema drift in eval_checkpoints.py's CSV output
doesn't require a code change here -- extend a list if a real column name
isn't in it yet. tests/test_plot_epoch_perf_comparison.py checks these
lists against the real data/results/finetune_rebuild/epoch_perf_*.csv
schema (skipped if that data isn't present, e.g. a fresh clone -- data/ is
gitignored).

This script is intentionally standalone (no imports from
plot_epoch_perf.py): it reads different CSVs (multi-draw, multi-
instantiation, multi-condition) for a different purpose (cross-condition
comparison, not single-model single-condition curves) and duplicating the
~10 lines of shared logic (CSV read, model shortname) is cheaper than
coupling two independently-evolving plotting scripts.

Usage:
    python scripts/plot_epoch_perf_comparison.py \\
        data/results/finetune_rebuild/epoch_perf_finetune_qwen1_5b_{inst1,bp_own,bp_gpt5}_30ep.csv \\
        --out analysis/figures/epoch_perf_qwen1_5b_bp_comparison.pdf \\
        --also-png \\
        --gap-csv analysis/derived/epoch_perf_qwen1_5b_bp_gap.csv

    # If the greedy draw is labelled differently in some CSV:
    python scripts/plot_epoch_perf_comparison.py ... --draw <real_label>

    # Treat a missing epoch-0 baseline row as an error instead of a warning:
    python scripts/plot_epoch_perf_comparison.py ... --strict

Hardening notes (2026-07-15, external review):
  - load_condition() raises ValueError on a duplicate (epoch, instantiation)
    row instead of silently letting the later row win. The --draw filter is
    the first line of defense against the multi-draw stacking bug (see
    point 1 above), but it only works if DRAW_COLS actually contains the
    real draw-column name; if a CSV ever renames that column to something
    not yet in DRAW_COLS, --draw filtering silently does nothing and a
    zero-valued sampling row would overwrite/stack on the real one. The
    duplicate-row guard is what actually catches that, not the filter.
  - Missing epoch 0 (no pre-fine-tune baseline anchor -- the other symptom
    the old legacy figures had) prints a warning to stderr by default, or
    raises with --strict.
  - main() refuses to plot CSVs that span more than one model value --
    exits with the offending model list rather than silently blending
    them into one "Model A & Model B" title.
  - _pass_rate() raises if a rate-column value exceeds 1.0: PASS_RATE_COLS
    assumes a 0-1 fraction (true of the real 'baseline_pass' column); a
    value >1 means that assumption is violated for this schema (e.g. it
    actually stores a 0-100 percent), not that the value is fine.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ── column auto-detection ──────────────────────────────────────────────────
# Extend these if a real CSV uses a different name than what's already here.
PASS_RATE_COLS = ["baseline_pass", "pass_rate", "baseline_pass_rate", "success_rate"]
N_PASS_COLS = ["n_pass", "num_pass", "n_passed", "passed"]
N_TOTAL_COLS = ["n", "n_total", "total", "num_total"]
INST_COLS = ["instantiation", "inst", "instantiation_id"]
DRAW_COLS = ["draw", "draw_label", "sample_type"]


def _first_present(fieldnames: list[str], candidates: list[str]) -> str | None:
    for c in candidates:
        if c in fieldnames:
            return c
    return None


def _pass_rate(row: dict, fieldnames: list[str]) -> float:
    """Prefer a direct rate column (real schema: 'baseline_pass', already a
    0-1 fraction); fall back to n_pass/n_total division for schemas that
    store raw counts instead."""
    rate_col = _first_present(fieldnames, PASS_RATE_COLS)
    if rate_col is not None and row.get(rate_col) not in (None, ""):
        value = float(row[rate_col])
        if value > 1.0:
            raise ValueError(
                f"{rate_col}={value!r} exceeds 1.0 -- PASS_RATE_COLS assumes a 0-1 "
                f"fraction (true of the real 'baseline_pass' column). This schema "
                f"appears to store percent (0-100) instead, so the column-list "
                f"assumption is violated for {rate_col!r}; fix the source data or "
                f"add a percent-scaled column list before trusting this value."
            )
        return value
    pass_col = _first_present(fieldnames, N_PASS_COLS)
    total_col = _first_present(fieldnames, N_TOTAL_COLS)
    if pass_col and total_col and row.get(total_col):
        total = float(row[total_col])
        return float(row[pass_col]) / total if total else float("nan")
    raise KeyError(
        f"no usable pass-rate column: none of {PASS_RATE_COLS} present with a "
        f"value, and no {N_PASS_COLS} / {N_TOTAL_COLS} pair found in {fieldnames}"
    )


# ── condition detection from filename ──────────────────────────────────────
CONDITION_ORDER = ["inst1", "bp_own", "bp_gpt5"]  # legend/plot order
CONDITION_LABELS = {
    "inst1":   "inst1 (no static leakage)",
    "bp_own":  "bp_own",
    "bp_gpt5": "bp_gpt5 (leaked-twin FT)",
}
CONDITION_COLORS = {
    # Okabe-Ito colourblind-safe palette. The prior green/orange/red set
    # (2026-07-14) made inst1 (control) vs bp_gpt5 (leaked-twin FT) --
    # exactly the two conditions the headline contrast is between --
    # indistinguishable under deuteranopia.
    "inst1":   "#0072B2",  # blue
    "bp_own":  "#009E73",  # green
    "bp_gpt5": "#D55E00",  # vermillion
}


def _condition_from_filename(path: Path) -> str:
    name = path.stem
    # bp_gpt5/bp_own checked before inst1 -- none are substrings of each
    # other in practice, but keep the more specific tokens first anyway.
    for cond in ("bp_gpt5", "bp_own", "inst1"):
        if cond in name:
            return cond
    raise ValueError(
        f"cannot determine condition (one of {CONDITION_ORDER}) from filename: {path.name}"
    )


def _model_shortname(model_id: str) -> str:
    """Qwen/Qwen2.5-Coder-7B-Instruct -> Qwen 7B"""
    last = model_id.split("/")[-1]
    for size in ("1.5B", "7B", "32B", "72B"):
        if size in last:
            return f"Qwen {size}"
    return last


# ── data loading ────────────────────────────────────────────────────────────

def load_condition(path: Path, draw: str, strict: bool = False) -> dict:
    """Returns {"epochs": [...], "seen": [...], "unseen": [...], "model": str},
    sorted by epoch, where seen = instantiation-1 pass rate and unseen =
    mean(instantiation 2, instantiation 3), filtered to a single `draw`
    value (skipped if the CSV has no draw column at all).

    strict: raise instead of warn when epoch 0 (the pre-fine-tune baseline)
    is missing.
    """
    rows = list(csv.DictReader(path.open()))
    if not rows:
        raise ValueError(f"no rows in {path}")
    fieldnames = list(rows[0].keys())

    inst_col = _first_present(fieldnames, INST_COLS)
    if inst_col is None:
        raise KeyError(f"no instantiation column found among {INST_COLS} in {fieldnames}")

    draw_col = _first_present(fieldnames, DRAW_COLS)
    if draw_col is not None and draw:
        available = sorted({r[draw_col] for r in rows})
        rows = [r for r in rows if r[draw_col] == draw]
        if not rows:
            raise ValueError(
                f"no rows with {draw_col}=={draw!r} in {path} (available: {available})"
            )

    by_epoch_inst: dict[int, dict[int, float]] = defaultdict(dict)
    for r in rows:
        epoch = int(r["epoch"])
        inst = int(r[inst_col])
        if inst in by_epoch_inst[epoch]:
            raise ValueError(
                f"duplicate row for (epoch={epoch}, instantiation={inst}) in {path} "
                f"(detected draw column: {draw_col!r}, --draw={draw!r}) -- this is "
                f"the multi-draw stacking bug: more than one row maps to the same "
                f"(epoch, instantiation) point. The duplicate-row guard, not the "
                f"--draw filter, is the real protection here -- it catches a "
                f"draw column renamed past DRAW_COLS (so --draw filtering silently "
                f"does nothing) before a zero-valued sampling row can silently "
                f"overwrite or stack on the real one."
            )
        by_epoch_inst[epoch][inst] = _pass_rate(r, fieldnames)

    if 0 not in by_epoch_inst:
        msg = (f"{path}: no epoch 0 (pre-fine-tune baseline) row -- no baseline "
               f"anchor for the seen/unseen curves (the other symptom the old "
               f"legacy comparison figures had)")
        if strict:
            raise ValueError(msg)
        print(f"WARNING: {msg}", file=sys.stderr)

    epochs = sorted(by_epoch_inst)
    seen, unseen = [], []
    for ep in epochs:
        vals = by_epoch_inst[ep]
        if 1 not in vals:
            raise KeyError(f"epoch {ep} missing instantiation 1 (seen) in {path}")
        seen.append(vals[1])
        unseen_vals = [vals[i] for i in (2, 3) if i in vals]
        if not unseen_vals:
            raise KeyError(f"epoch {ep} missing instantiation 2/3 (unseen) in {path}")
        unseen.append(sum(unseen_vals) / len(unseen_vals))

    return {"epochs": epochs, "seen": seen, "unseen": unseen, "model": rows[0].get("model", "")}


# ── plotting ─────────────────────────────────────────────────────────────────

def plot(conditions: dict[str, dict], title: str, out_path: Path, also_png: bool) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))

    for cond in CONDITION_ORDER:
        if cond not in conditions:
            continue
        data = conditions[cond]
        color = CONDITION_COLORS[cond]
        label = CONDITION_LABELS[cond]
        epochs = data["epochs"]
        ax.plot(
            epochs, [v * 100 for v in data["seen"]],
            color=color, linestyle="-", marker="o", markerfacecolor=color,
            markeredgecolor=color, label=f"{label} — seen (inst1)",
        )
        ax.plot(
            epochs, [v * 100 for v in data["unseen"]],
            color=color, linestyle="--", marker="o", markerfacecolor="none",
            markeredgecolor=color, label=f"{label} — unseen (mean inst2/3)",
        )

    ax.set_xlabel("Training epoch", fontsize=11)
    ax.set_ylabel("Baseline pass rate (%)", fontsize=11)
    ax.set_title(title, fontsize=12)
    ax.set_ylim(0, 105)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize=8, loc="best", framealpha=0.9)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    print(f"Saved: {out_path}")
    if also_png:
        png_path = out_path.with_suffix(".png")
        fig.savefig(png_path, dpi=150)
        print(f"Saved: {png_path}")
    plt.close(fig)


# ── gap table ────────────────────────────────────────────────────────────────

def gap_table(conditions: dict[str, dict]) -> list[dict]:
    """One row per condition, at that condition's final (max) epoch."""
    rows = []
    for cond in CONDITION_ORDER:
        if cond not in conditions:
            continue
        data = conditions[cond]
        final_epoch = data["epochs"][-1]
        seen_pct = data["seen"][-1] * 100
        unseen_pct = data["unseen"][-1] * 100
        rows.append({
            "condition": cond,
            "epoch": final_epoch,
            # Column names spell out the metric explicitly -- this script only
            # ever plots PASS_RATE_COLS (baseline_pass and its aliases, see
            # module docstring), never exec_rate, but the bare "seen_pct" name
            # read ambiguously. Flagged 2026-07-26.
            "seen_baseline_pass_pct": round(seen_pct, 1),
            "unseen_baseline_pass_pct": round(unseen_pct, 1),
            "gap_pp_baseline_pass": round(seen_pct - unseen_pct, 1),
        })
    return rows


def print_gap_table(rows: list[dict]) -> None:
    print(f"{'condition':10s} {'epoch':>6s} {'seen bp%':>9s} {'unseen bp%':>11s} {'gap(pp)':>9s}")
    for r in rows:
        print(f"{r['condition']:10s} {r['epoch']:6d} {r['seen_baseline_pass_pct']:9.1f} "
              f"{r['unseen_baseline_pass_pct']:11.1f} {r['gap_pp_baseline_pass']:9.1f}")


def write_gap_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "condition", "epoch", "seen_baseline_pass_pct",
            "unseen_baseline_pass_pct", "gap_pp_baseline_pass",
        ])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved: {path}")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", type=Path, nargs="+",
                         help="epoch_perf CSV(s), one per condition (inst1/bp_own/bp_gpt5)")
    parser.add_argument("--draw", default="greedy",
                         help="Draw column value to filter to (default: greedy). Pass '' to disable "
                              "filtering for a CSV with no draw column concept at all.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--also-png", action="store_true",
                         help="Also save a .png next to --out for quick visual inspection")
    parser.add_argument("--gap-csv", type=Path, default=None,
                         help="Write the seen/unseen/gap table (at each condition's final epoch) here")
    parser.add_argument("--strict", action="store_true",
                         help="Raise instead of warn when a CSV is missing its epoch-0 baseline row")
    args = parser.parse_args()

    conditions: dict[str, dict] = {}
    for csv_path in args.csv:
        cond = _condition_from_filename(csv_path)
        if cond in conditions:
            print(f"WARNING: multiple input files map to condition {cond!r}; "
                  f"keeping the first, ignoring {csv_path}", file=sys.stderr)
            continue
        conditions[cond] = load_condition(csv_path, args.draw, strict=args.strict)

    if not conditions:
        print("No usable data in the given CSV(s).", file=sys.stderr)
        sys.exit(1)

    model_names = {c["model"] for c in conditions.values() if c["model"]}
    if len(model_names) > 1:
        sys.exit(
            f"ERROR: input CSVs span more than one model: {sorted(model_names)} -- "
            f"pass one model's CSVs per invocation (per-model file lists), not a mix."
        )
    model_label = _model_shortname(next(iter(model_names))) if model_names else "?"
    title = (f"Contamination experiment — {model_label}\n"
             f"Seen (inst1, train) vs unseen (mean inst2/inst3, held-out) by condition")

    plot(conditions, title, args.out, args.also_png)

    rows = gap_table(conditions)
    print()
    print_gap_table(rows)
    if args.gap_csv is not None:
        write_gap_csv(rows, args.gap_csv)


if __name__ == "__main__":
    main()
