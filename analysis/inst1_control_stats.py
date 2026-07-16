"""Read-only helper for the inst1-control investigation (step F): Wilson 95%
CIs for every seen/unseen cell at epoch 30 (n=150), plus a two-proportion
z-test comparing seen (instantiation 1) vs pooled unseen (instantiation 2+3).

NOTE ON PAIRING: a true McNemar test needs per-problem paired pass/fail for
seen vs unseen on the same template_id. eval_checkpoints.py's
_score_responses() (scripts/eval_checkpoints.py:284) only accumulates
aggregate counts (exec_ok_total, bp_total) and never persists per-problem
results -- by design, to keep runtime tractable (~15 min/checkpoint vs ~6h
with full mutation scoring/per-problem logging). No existing artifact has
per-problem pass/fail for these checkpoint evals, so pairing cannot be
reconstructed without launching a new eval job, which this investigation is
explicitly not allowed to do. Falling back to the unpaired two-proportion
z-test per the investigation brief's own contingency instruction.

Usage:
    python analysis/inst1_control_stats.py \\
        --csv data/results/finetune_rebuild/epoch_perf_finetune_qwen1_5b_inst1_30ep.csv \\
        --epoch 30 --draw greedy
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion, 95% by default."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def two_proportion_z(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float]:
    """Two-sided two-proportion z-test (pooled variance). Returns (z, p)."""
    p1, p2 = k1 / n1, k2 / n2
    p_pool = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return (0.0, 1.0)
    z = (p1 - p2) / se
    # two-sided p-value from the standard normal survival function
    p_value = math.erfc(abs(z) / math.sqrt(2))
    return (z, p_value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--epoch", type=int, default=30)
    parser.add_argument("--draw", default="greedy")
    args = parser.parse_args()

    rows = list(csv.DictReader(args.csv.open()))
    cells = {}
    for r in rows:
        if int(r["epoch"]) == args.epoch and r["draw"] == args.draw:
            inst = int(r["instantiation"])
            n = int(r["n"])
            bp_rate = float(r["baseline_pass"])
            k = round(bp_rate * n)  # baseline_pass is a rounded rate in the CSV; recover the count
            cells[inst] = {"n": n, "k": k, "rate": bp_rate}

    print(f"{args.csv} — epoch {args.epoch}, draw={args.draw}")
    for inst in sorted(cells):
        c = cells[inst]
        lo, hi = wilson_ci(c["k"], c["n"])
        label = "seen (inst1)" if inst == 1 else f"unseen (inst{inst})"
        print(f"  {label:16s} k={c['k']:3d}/{c['n']:3d} rate={c['rate']:.4f}  "
              f"Wilson 95% CI=[{lo:.4f}, {hi:.4f}]")

    if 1 in cells and 2 in cells and 3 in cells:
        seen = cells[1]
        unseen_k = cells[2]["k"] + cells[3]["k"]
        unseen_n = cells[2]["n"] + cells[3]["n"]
        lo, hi = wilson_ci(unseen_k, unseen_n)
        print(f"  {'unseen (pooled 2+3)':16s} k={unseen_k:3d}/{unseen_n:3d} "
              f"rate={unseen_k / unseen_n:.4f}  Wilson 95% CI=[{lo:.4f}, {hi:.4f}]")

        z, p = two_proportion_z(seen["k"], seen["n"], unseen_k, unseen_n)
        print(f"\n  two-proportion z-test, seen (inst1) vs unseen (pooled inst2+3):")
        print(f"    z={z:.4f}  p={p:.4g}  "
              f"({'reject' if p < 0.05 else 'fail to reject'} H0 at alpha=0.05)")
        print(f"  NOTE: unpaired -- see module docstring for why McNemar pairing "
              f"wasn't reconstructable from existing artifacts.")


if __name__ == "__main__":
    main()
