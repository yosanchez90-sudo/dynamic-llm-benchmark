"""Mutation density sweep: for each template, generate one instance and
count candidate mutants. Confirm count falls in declared expected_mutant_count
band (Phase 2 Week 6 sub-stage 2.6.b).

Two-level reporting
-------------------
in_band            — actual total within the declared (lo, hi) band.
                     This is the primary stability check. The band is set at
                     authoring time as (measured ± 3) to guard against
                     seed-to-seed instability in mutant count (e.g. a parameter
                     range that sometimes adds/removes constant-replacement or
                     boundary sites). It is NOT a tier-membership check — tier
                     is defined by CC alone (see validate_cc.py).

within_soft_margin — actual total within ±2 of the declared band (i.e. in
                     [lo-2, hi+2]). Reported as "OK ±2" for awareness; does
                     not constitute a failure. Templates that consistently land
                     here may need their declared band recalibrated.

Templates whose count is outside both levels are flagged REVIEW and should be
investigated — either the template logic has changed or the declared band was
set incorrectly.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_smoke"))

from engine import instantiate, load_template  # noqa: E402
from mutator import count_mutants  # noqa: E402


def sweep():
    results = []
    by_tier = {"L1": [], "L2": [], "L3": [], "L4": []}
    for tier in ["L1", "L2", "L3", "L4"]:
        for path in sorted((ROOT / tier).glob("*.py")):
            t = load_template(path)
            inst = instantiate(t, 42)
            if not inst.get("source"):
                continue
            counts = count_mutants(inst["source"])
            lo, hi = t.expected_mutant_count
            in_band = lo <= counts["TOTAL"] <= hi
            within_soft_margin = (lo - 2) <= counts["TOTAL"] <= (hi + 2)
            rec = {
                "template_id": t.template_id,
                "tier": t.declared_tier,
                "expected_band": [lo, hi],
                "actual_total": counts["TOTAL"],
                "by_operator": counts,
                "in_band": in_band,
                "within_soft_margin": within_soft_margin,
            }
            results.append(rec)
            by_tier[tier].append(rec)

    # Per-tier summary
    print("\n=== Mutation density sanity check ===\n")
    for tier in ["L1", "L2", "L3", "L4"]:
        recs = by_tier[tier]
        if not recs:
            continue
        totals = [r["actual_total"] for r in recs]
        in_band = sum(1 for r in recs if r["in_band"])
        soft_margin = sum(1 for r in recs if r["within_soft_margin"])
        mean = sum(totals) / len(totals)
        print(f"  {tier}: n={len(recs)}, mean mutants={mean:.1f}, "
              f"min={min(totals)}, max={max(totals)}, "
              f"in declared band: {in_band}/{len(recs)}, within soft ±2: {soft_margin}/{len(recs)}")

    # Out-of-band detail
    print("\n=== Templates outside declared band (informational, ±2 tolerance also reported) ===\n")
    for r in results:
        if not r["in_band"]:
            tol = "OK ±2 soft" if r["within_soft_margin"] else "REVIEW"
            print(f"  {r['template_id']}: actual={r['actual_total']}, "
                  f"declared={r['expected_band']}  [{tol}]")

    # Write JSON
    (ROOT / "_smoke" / "mutation_density.json").write_text(json.dumps(results, indent=2))
    print(f"\nReport written to _smoke/mutation_density.json")
    return results


if __name__ == "__main__":
    sweep()
