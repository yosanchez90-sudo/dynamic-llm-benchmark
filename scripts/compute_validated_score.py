"""Compute the sample-validated mutation score (Mut@K_validated) from the
hand-inspected equivalent-mutant sample in inspection_sheet.xlsx.

    Mut@K_validated = mutants_killed / (mutants_total * (1 - equivalent_rate_tier))

equivalent_rate_tier is estimated from that tier's 30-mutant inspection
sample: Wilson 95% CI on equivalent / (equivalent + non-equivalent).
"unsure" verdicts are excluded from that denominator by default. Pass
--unsure-policy to change this (they are a genuine "don't know", not
evidence for either side; folding them into one side without justification
would bias the estimate).

The headline Mut@K_validated is reported with a bootstrap 95% CI that
resamples both the scored problems (with replacement) and the tier's
inspection sample (a fresh binomial draw at the point rate each replicate),
so the interval reflects uncertainty from both sources.

Reads:  analysis/equiv_mutants/inspection_sheet.xlsx (verdict column)
        JSONL result files matching --results-glob (repeatable)
Writes: analysis/equiv_mutants/validated_scores.csv
"""
import argparse
import glob
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
Z95 = 1.959963985469351
TIERS = ["L1", "L2", "L3", "L4"]


def wilson_ci(k: int, n: int, z: float = Z95):
    if n == 0:
        return None
    phat = k / n
    denom = 1 + z ** 2 / n
    center = (phat + z ** 2 / (2 * n)) / denom
    margin = z * math.sqrt(phat * (1 - phat) / n + z ** 2 / (4 * n ** 2)) / denom
    return phat, max(0.0, center - margin), min(1.0, center + margin)


def equivalent_rates(sheet_path: Path, unsure_policy: str) -> dict:
    df = pd.read_excel(sheet_path, sheet_name="Inspection")
    rates = {}
    for tier, g in df.groupby("tier"):
        verdicts = g["verdict"].astype(str).str.strip().str.lower()
        n_equiv = int((verdicts == "equivalent").sum())
        n_non = int((verdicts == "non-equivalent").sum())
        n_unsure = int((verdicts == "unsure").sum())
        n_filled = n_equiv + n_non + n_unsure
        n_unfilled = len(g) - n_filled

        if unsure_policy == "exclude":
            k, n = n_equiv, n_equiv + n_non
        elif unsure_policy == "as_equivalent":
            k, n = n_equiv + n_unsure, n_equiv + n_non + n_unsure
        elif unsure_policy == "as_nonequivalent":
            k, n = n_equiv, n_equiv + n_non + n_unsure
        else:
            raise ValueError(unsure_policy)

        rates[tier] = {
            "n_rows": len(g), "n_equivalent": n_equiv, "n_non_equivalent": n_non,
            "n_unsure": n_unsure, "n_unfilled": n_unfilled,
            "rate_k": k, "rate_n": n,
            "wilson": wilson_ci(k, n) if n else None,
        }
    return rates


def load_problems(results_globs: list[str], tier: str) -> list[tuple[int, int]]:
    problems = []
    for pattern in results_globs:
        for fp in glob.glob(str(ROOT / pattern)):
            for line in Path(fp).read_text().splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get("tier") != tier:
                    continue
                if not r.get("mutants_total"):
                    continue
                if r.get("mutation_score") is None:
                    continue  # gate: only exec-ok, baseline-passed problems are scoreable
                problems.append((r["mutants_killed"], r["mutants_total"]))
    return problems


def bootstrap_validated_score(problems, rate_k, rate_n, n_boot=2000, seed=20260714):
    if not problems or not rate_n:
        return None
    rng = np.random.default_rng(seed)
    killed = np.array([p[0] for p in problems], dtype=float)
    total = np.array([p[1] for p in problems], dtype=float)
    point_rate = rate_k / rate_n
    point = float(killed.sum() / (total.sum() * (1 - point_rate)))

    n_prob = len(problems)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_prob, n_prob)
        k_b, t_b = killed[idx].sum(), total[idx].sum()
        r_b = rng.binomial(rate_n, point_rate) / rate_n
        if t_b == 0 or r_b >= 1:
            continue
        boots.append(k_b / (t_b * (1 - r_b)))
    if not boots:
        return point, None, None
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return point, float(lo), float(hi)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", default="analysis/equiv_mutants/inspection_sheet.xlsx", type=Path)
    ap.add_argument("--results-glob", action="append", default=None,
                     help="Glob(s) of result JSONLs to aggregate, repeatable. "
                          "Default: data/results/dynamic/*.jsonl")
    ap.add_argument("--unsure-policy", choices=["exclude", "as_equivalent", "as_nonequivalent"],
                     default="exclude")
    ap.add_argument("--out", default="analysis/equiv_mutants/validated_scores.csv", type=Path)
    args = ap.parse_args()
    results_globs = args.results_glob or ["data/results/dynamic/*.jsonl"]

    sheet_path = args.sheet if args.sheet.is_absolute() else ROOT / args.sheet
    rates = equivalent_rates(sheet_path, args.unsure_policy)

    rows = []
    for tier in TIERS:
        r = rates.get(tier, {})
        print(f"\n{tier}: {r.get('n_rows', 0)} rows "
              f"(equivalent={r.get('n_equivalent', 0)}, non-equivalent={r.get('n_non_equivalent', 0)}, "
              f"unsure={r.get('n_unsure', 0)}, unfilled={r.get('n_unfilled', 0)})")
        if not r or r.get("n_unfilled", 0) >= r.get("n_rows", 0):
            print("  -> sheet not yet filled for this tier; skipping.")
            continue
        if r.get("n_unfilled", 0) > 0:
            print(f"  -> WARNING: {r['n_unfilled']} of {r['n_rows']} rows still unfilled; "
                  f"rate computed from the {r['rate_n']} filled+applicable rows only.")
        wilson = r["wilson"]
        if wilson is None:
            print("  -> no equivalent/non-equivalent rows to estimate a rate from; skipping.")
            continue

        problems = load_problems(results_globs, tier)
        boot = bootstrap_validated_score(problems, r["rate_k"], r["rate_n"])
        rows.append({
            "tier": tier,
            "n_inspected": r["n_rows"],
            "n_equivalent": r["n_equivalent"],
            "n_non_equivalent": r["n_non_equivalent"],
            "n_unsure": r["n_unsure"],
            "unsure_policy": args.unsure_policy,
            "equivalent_rate": round(wilson[0], 4),
            "equivalent_rate_wilson_lo": round(wilson[1], 4),
            "equivalent_rate_wilson_hi": round(wilson[2], 4),
            "n_problems_scored": len(problems),
            "mut_at_k_validated": round(boot[0], 4) if boot else None,
            "mut_at_k_validated_boot_lo": round(boot[1], 4) if boot and boot[1] is not None else None,
            "mut_at_k_validated_boot_hi": round(boot[2], 4) if boot and boot[2] is not None else None,
        })

    if rows:
        out_path = args.out if args.out.is_absolute() else ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(out_path, index=False)
        print(f"\nWritten: {out_path}")
    else:
        print("\nNo tier had a filled sheet yet -- nothing written. Re-run after "
              "analysis/equiv_mutants/inspection_sheet.xlsx has verdicts filled in.")


if __name__ == "__main__":
    main()
