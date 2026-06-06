"""Mutation density sweep: for each template, generate one instance and
count candidate mutants. Confirm count falls in declared expected_mutant_count
band (Phase 2 Week 6 sub-stage 2.6.b).
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
            tolerant = (lo - 2) <= counts["TOTAL"] <= (hi + 2)  # roomy tolerance
            rec = {
                "template_id": t.template_id,
                "tier": t.declared_tier,
                "expected_band": [lo, hi],
                "actual_total": counts["TOTAL"],
                "by_operator": counts,
                "in_band": in_band,
                "within_tolerance": tolerant,
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
        within_tol = sum(1 for r in recs if r["within_tolerance"])
        mean = sum(totals) / len(totals)
        print(f"  {tier}: n={len(recs)}, mean mutants={mean:.1f}, "
              f"min={min(totals)}, max={max(totals)}, "
              f"in declared band: {in_band}/{len(recs)}, within ±2: {within_tol}/{len(recs)}")

    # Out-of-band detail
    print("\n=== Templates outside declared band (informational, ±2 tolerance also reported) ===\n")
    for r in results:
        if not r["in_band"]:
            tol = "OK ±2" if r["within_tolerance"] else "REVIEW"
            print(f"  {r['template_id']}: actual={r['actual_total']}, "
                  f"declared={r['expected_band']}  [{tol}]")

    # Write JSON
    (ROOT / "_smoke" / "mutation_density.json").write_text(json.dumps(results, indent=2))
    print(f"\nReport written to _smoke/mutation_density.json")
    return results


if __name__ == "__main__":
    sweep()
