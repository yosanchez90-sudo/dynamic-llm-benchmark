"""Generate a benchmark instantiation and record a post-hoc validation manifest.

For a given instantiation (id + seed), runs the deterministic template engine
over all 60 templates (15/tier x 4 tiers) x 5 instance seeds = 300 instances,
recomputing:
  - V1/V2 (CC-in-band + AST-depth check), already done inside engine.instantiate().
  - An oracle smoke test using the template's static smoke_test_inputs (the
    same check template_corpus/templates/_smoke/validate.py performs at
    template-authoring time). This is NOT run against each
    instance's sampled `params`: for IdentifierBank-typed parameters (e.g.
    `x`, `y`, `fn_name`) the sampled value is a variable *name* used for
    codegen substitution into body_skeleton, not a numeric test value. The
    oracle lambda's same-named arguments expect actual numbers. The oracle
    is a template-level artefact tested once against its fixed
    smoke_test_inputs; that result is recorded against every instance row
    generated from that template in this instantiation, for traceability.

Writes one row per instance to template_corpus/manifests/inst<N>_manifest.csv
(not under data/ or analysis/*.csv. Both are gitignored; this file is meant
to be committed as the record of what got generated).

Usage:
    python scripts/generate_instantiation_manifest.py --instantiation-id 4 --instantiation-seed 4
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_TEMPLATE_ROOT = ROOT / "template_corpus" / "templates"
sys.path.insert(0, str(_TEMPLATE_ROOT))
sys.path.insert(0, str(_TEMPLATE_ROOT / "_smoke"))

from engine import instantiate, load_template, TIER_CC_BANDS  # noqa: E402

TIERS = ("L1", "L2", "L3", "L4")
INSTANCE_BASE_SEEDS = (101, 102, 103, 104, 105)

MANIFEST_DIR = ROOT / "template_corpus" / "manifests"


def _oracle_smoke_test(oracle, smoke_test_inputs: tuple[dict, ...]) -> tuple[str, str]:
    """Run oracle against the template's fixed smoke_test_inputs (same
    convention as validate.py): TypeError is a real bug (the domain and the
    oracle signature disagree); any other exception is allowed (the oracle
    raising on a deliberately-chosen edge case is legitimate)."""
    for smoke in smoke_test_inputs:
        try:
            oracle(**smoke)
        except TypeError as e:
            return "type_error", f"{smoke}: {e}"
        except Exception:
            pass  # raising on an edge case is allowed, per validate.py
    return "ok", ""


def generate_manifest(instantiation_id: str, instantiation_seed: int) -> list[dict]:
    rows: list[dict] = []
    for tier in TIERS:
        tier_dir = _TEMPLATE_ROOT / tier
        for tmpl_path in sorted(tier_dir.glob(f"{tier}-*.py")):
            template = load_template(tmpl_path)
            # Oracle smoke test is a template-level property (fixed numeric
            # inputs), computed once per template, not re-derived per seed.
            oracle_status, oracle_detail = _oracle_smoke_test(
                template.oracle, template.smoke_test_inputs)
            for base_seed in INSTANCE_BASE_SEEDS:
                seed = instantiation_seed * 1000 + base_seed
                inst = instantiate(template, seed)
                lo, hi = TIER_CC_BANDS[tier]
                v1_v2_errors = inst.get("validation_errors", [])

                source = inst.get("source") or ""
                rows.append({
                    "template_id": template.template_id,
                    "tier": tier,
                    "instantiation_id": instantiation_id,
                    "instantiation_seed": instantiation_seed,
                    "instance_seed": seed,
                    "cc": inst.get("cc", ""),
                    "cc_band": f"{lo}-{hi}",
                    "ast_depth": inst.get("ast_depth", ""),
                    "validation_errors": " | ".join(v1_v2_errors),
                    "oracle_smoke_status": oracle_status,
                    "oracle_smoke_detail": oracle_detail,
                    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                })
    return rows


def write_manifest(rows: list[dict], instantiation_id: str) -> Path:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    out_path = MANIFEST_DIR / f"inst{instantiation_id}_manifest.csv"
    if out_path.exists():
        raise FileExistsError(
            f"{out_path} already exists — manifests are append-only artefacts, "
            f"not regenerated in place. Remove it manually first if you intend "
            f"to regenerate (the engine is deterministic, so a regenerated file "
            f"should be byte-identical anyway)."
        )
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instantiation-id", required=True)
    parser.add_argument("--instantiation-seed", required=True, type=int)
    args = parser.parse_args()

    rows = generate_manifest(args.instantiation_id, args.instantiation_seed)

    total = len(rows)
    v1v2_failures = [r for r in rows if r["validation_errors"]]
    oracle_failures = [r for r in rows if r["oracle_smoke_status"] == "type_error"]

    out_path = write_manifest(rows, args.instantiation_id)

    print(f"instantiation {args.instantiation_id} (seed={args.instantiation_seed}): "
          f"{total} instances generated -> {out_path}")
    print(f"  CC-in-band/AST-depth (V1/V2) failures: {len(v1v2_failures)}")
    for r in v1v2_failures:
        print(f"    {r['template_id']} seed={r['instance_seed']}: {r['validation_errors']}")
    print(f"  Oracle smoke TypeErrors: {len(oracle_failures)}")
    for r in oracle_failures:
        print(f"    {r['template_id']} seed={r['instance_seed']}: {r['oracle_smoke_detail']}")
    if not v1v2_failures and not oracle_failures:
        print("  All instances pass post-hoc validation.")


if __name__ == "__main__":
    main()
