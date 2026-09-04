#!/usr/bin/env python3
"""Regenerate the whole evaluation set twice and compare the two versions.

This is the "change one number and you get a different benchmark"
demonstration. It sweeps every template in every tier at two different
instantiation seeds, then reports what changed (every problem) and what did
not (the measurement properties).

    python demo/compare_instantiations.py
    python demo/compare_instantiations.py --instantiation-a 1 --instantiation-b 6

It takes the INSTANTIATION seed -- the single number the claim is about --
and derives the per-instance seeds with the same formula the production
path uses:

    seed = instantiation_seed * 1000 + base_seed
    INSTANCE_BASE_SEEDS = (101, 102, 103, 104, 105)

Both are read straight from scripts/generate_instantiation_manifest.py:43,73
(and the identical derivation in src/data/test_gen.py:130) rather than
restated here, so this cannot drift from what the pipeline actually did.
Verified 2026-09-03: instantiation 1 -> instance seeds 1101..1105, which is
where the demo's own seed 1101 comes from.

Overlap is measured, never assumed. The script prints the shared count and
names the offenders if there are any.
"""

import argparse
import hashlib
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_ROOT = REPO_ROOT / "template_corpus" / "templates"

sys.path.insert(0, str(TEMPLATES_ROOT))
sys.path.insert(0, str(TEMPLATES_ROOT / "_smoke"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from engine import load_template, instantiate  # noqa: E402

# The production constant, imported rather than copied. If the pipeline
# changes its base seeds, this demo changes with it.
from generate_instantiation_manifest import INSTANCE_BASE_SEEDS  # noqa: E402

RULE = "=" * 74


def seeds_for(instantiation_seed: int) -> tuple[int, ...]:
    """The production derivation, generate_instantiation_manifest.py:73."""
    return tuple(instantiation_seed * 1000 + base for base in INSTANCE_BASE_SEEDS)


def sweep(tiers, seeds):
    """Instantiate every template in every tier at every seed."""
    problems = []
    for tier in tiers:
        # {tier}-*.py, matching the production loader's own glob, not *.py
        for path in sorted((TEMPLATES_ROOT / tier).glob(f"{tier}-*.py")):
            template = load_template(path)
            for seed in seeds:
                r = instantiate(template, seed)
                if r.get("validation_errors"):
                    continue
                problems.append({
                    "tier": tier,
                    "template": path.stem,
                    "seed": seed,
                    "cc": r["cc"],
                    "digest": hashlib.sha256(r["source"].encode()).hexdigest(),
                })
    return problems


def shape(problems):
    """The properties that should NOT change between versions."""
    per_tier = defaultdict(list)
    for p in problems:
        per_tier[p["tier"]].append(p["cc"])
    return {
        "n": len(problems),
        "templates": len({p["template"] for p in problems}),
        "tiers": {t: (len(v), min(v), max(v), round(sum(v) / len(v), 2))
                  for t, v in sorted(per_tier.items())},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="L1,L2,L3,L4")
    ap.add_argument("--instantiation-a", type=int, default=1)
    ap.add_argument("--instantiation-b", type=int, default=6)
    args = ap.parse_args()

    tiers = tuple(args.tiers.split(","))
    ia, ib = args.instantiation_a, args.instantiation_b
    seeds_a, seeds_b = seeds_for(ia), seeds_for(ib)

    print(RULE)
    print("  The same benchmark, regenerated -- one number apart")
    print(f"  instantiation seed {ia}  vs  instantiation seed {ib}")
    print(RULE)

    t0 = time.perf_counter()
    a = sweep(tiers, seeds_a)
    t_a = time.perf_counter() - t0

    t0 = time.perf_counter()
    b = sweep(tiers, seeds_b)
    t_b = time.perf_counter() - t0

    sa, sb = shape(a), shape(b)

    print(f"  version A   --instantiation-seed {ia}   seeds {seeds_a[0]}..{seeds_a[-1]}"
          f"   {sa['n']} problems   {t_a:.1f}s")
    print(f"  version B   --instantiation-seed {ib}   seeds {seeds_b[0]}..{seeds_b[-1]}"
          f"   {sb['n']} problems   {t_b:.1f}s")
    print(RULE)

    # --- what did NOT change ------------------------------------------------
    print("  UNCHANGED -- the measurement properties")
    print(f"    templates covered   A {sa['templates']}   B {sb['templates']}")
    print(f"    {'tier':<6}{'n':>6}{'CC min':>9}{'CC max':>9}{'CC mean':>10}")
    for tier in tiers:
        na, mna, mxa, ava = sa["tiers"][tier]
        nb, mnb, mxb, avb = sb["tiers"][tier]
        same = (na, mna, mxa) == (nb, mnb, mxb)
        flag = "" if same else "   <- DIFFERS"
        print(f"    {tier:<6}{na:>6}{mna:>9}{mxa:>9}{ava:>10}{flag}")
        if not same:
            print(f"    {'':<6}{nb:>6}{mnb:>9}{mxb:>9}{avb:>10}   (version B)")
    print(RULE)

    # --- what DID change ----------------------------------------------------
    da = {p["digest"] for p in a}
    db = {p["digest"] for p in b}
    shared = da & db

    print("  CHANGED -- every problem the models actually see")
    print(f"    distinct problems   A {len(da)}   B {len(db)}")
    print(f"    shared between them {len(shared)}")

    if shared:
        print()
        print("    NOT ZERO. Identify these before presenting:")
        by_digest = {p["digest"]: p for p in a}
        for d in sorted(shared)[:8]:
            p = by_digest[d]
            print(f"      {p['template']}  seed {p['seed']}")
        if len(shared) > 8:
            print(f"      ... and {len(shared) - 8} more")
    else:
        print("    -> no problem instance appears in both versions")

    # Overlap within a single version would mean two seeds collapsed onto the
    # same instance -- worth knowing separately from cross-version overlap.
    dupes_a = [d for d, n in Counter(p["digest"] for p in a).items() if n > 1]
    if dupes_a:
        print(f"    NOTE: {len(dupes_a)} instances are duplicated *within* version A")

    print(RULE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
