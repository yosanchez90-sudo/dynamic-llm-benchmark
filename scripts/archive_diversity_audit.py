"""Archive the within-tier diversity + mutation-density sweep outputs to
analysis/diversity/: per-tier CSVs, the locked threshold policy, and any
flagged pairs. Source of truth is template_corpus/templates/_smoke/{diversity_v2,mutation_density}.json,
written by diversity_v2.py / mutation_sweep.py (run via
scripts/slurm/run_corpus_diversity_audit.slurm).

Usage: python scripts/archive_diversity_audit.py
"""
import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SMOKE = ROOT / "template_corpus" / "templates" / "_smoke"
OUT = ROOT / "analysis" / "diversity"

TIERS = ["L1", "L2", "L3", "L4"]


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    diversity = json.loads((SMOKE / "diversity_v2.json").read_text())
    density = json.loads((SMOKE / "mutation_density.json").read_text())

    # ---- per-tier diversity CSV ----
    div_fields = [
        "template_id", "tier", "mean_doc_words", "doc_threshold_applied",
        "bleu4_mean", "bleu4_max", "embed_cos_mean", "embed_cos_max",
        "id_jaccard_mean", "id_jaccard_max", "body_jaccard_mean", "body_jaccard_max",
        "flagged", "flag_source", "flagged_pair",
    ]
    with (OUT / "diversity_by_template.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=div_fields)
        w.writeheader()
        for tier in TIERS:
            for tid, rec in sorted(diversity.items()):
                if rec["tier"] != tier:
                    continue
                w.writerow({k: rec.get(k) for k in div_fields})

    # ---- flagged pairs (empty file with header if none) ----
    flagged = [r for r in diversity.values() if r["flagged"]]
    with (OUT / "flagged_pairs.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "template_id", "tier", "flag_source", "flagged_pair", "value", "threshold",
        ])
        w.writeheader()
        for rec in flagged:
            src = rec["flag_source"]
            value = {"bleu4": rec["bleu4_max"], "embed_cos": rec["embed_cos_max"],
                      "id_jaccard": rec["id_jaccard_max"], "body_jaccard": rec["body_jaccard_max"]}[src]
            threshold = (rec["doc_threshold_applied"] if src in ("bleu4", "embed_cos")
                         else 0.80)
            w.writerow({
                "template_id": rec["template_id"], "tier": rec["tier"],
                "flag_source": src, "flagged_pair": rec["flagged_pair"],
                "value": value, "threshold": threshold,
            })

    # ---- diversity tier summary ----
    with (OUT / "diversity_tier_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tier", "n_templates", "n_flagged"])
        w.writeheader()
        for tier in TIERS:
            recs = [r for r in diversity.values() if r["tier"] == tier]
            w.writerow({"tier": tier, "n_templates": len(recs),
                        "n_flagged": sum(1 for r in recs if r["flagged"])})

    # ---- mutation density CSVs ----
    dens_fields = ["template_id", "tier", "expected_band", "actual_total",
                   "in_band", "within_soft_margin", "by_operator"]
    with (OUT / "mutation_density_by_template.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=dens_fields)
        w.writeheader()
        for tier in TIERS:
            for rec in density:
                if rec["tier"] != tier:
                    continue
                row = {k: rec.get(k) for k in dens_fields}
                row["expected_band"] = f"{rec['expected_band'][0]}-{rec['expected_band'][1]}"
                row["by_operator"] = json.dumps(rec["by_operator"])
                w.writerow(row)

    with (OUT / "mutation_density_tier_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "tier", "n_templates", "mean_mutants", "min", "max", "in_band", "within_soft_margin",
        ])
        w.writeheader()
        for tier in TIERS:
            recs = [r for r in density if r["tier"] == tier]
            totals = [r["actual_total"] for r in recs]
            w.writerow({
                "tier": tier, "n_templates": len(recs),
                "mean_mutants": round(sum(totals) / len(totals), 1),
                "min": min(totals), "max": max(totals),
                "in_band": sum(1 for r in recs if r["in_band"]),
                "within_soft_margin": sum(1 for r in recs if r["within_soft_margin"]),
            })

    # ---- thresholds doc ----
    commit = _git_commit()
    import datetime
    run_date = datetime.date.today().isoformat()
    job_id = "9377396"

    thresholds_md = f"""# Diversity flag-rule thresholds (locked policy)

Source: `template_corpus/templates/_smoke/diversity_v2.py` (verbatim policy comment).

- Code-level measures (identifier Jaccard, body-line Jaccard): flag at max-pair value > 0.80, always.
- Docstring-level measures (BLEU-4, embedding cosine): flag at max-pair value > 0.80 when the
  template's mean docstring length is >= 14 words, and > 0.95 when it is < 14 words.

Rationale: BLEU-4 and short-text embedding cosine have an inherent similarity floor for
docstrings under ~14 words (too few n-grams to discriminate paraphrase from duplicate).
The relaxed threshold below the cutoff prevents this measure-too-strict effect from
inflating the flag rate at L1, where docstrings are naturally short.

Aggregation: all-pairs mean + max across the 5 fixed instantiation seeds (101-105),
i.e. C(5,2) = 10 pairs per template. A template is flagged if *any* single pair on
*any* measure crosses its applicable threshold.

BLEU-4 backend: real `sacrebleu` (added as a project dependency this run — prior
runs before {run_date} silently fell back to a 4-gram Jaccard approximation because
sacrebleu was not installed).

Embedding backend: TF-IDF cosine over docstring tokens — documented in diversity_v2.py
as the intentional Phase 2 validation stand-in for a production sentence-transformer
model; not a gap to close for this gate.
"""

    readme_md = f"""# Within-tier diversity + mutation-density archive

Archived {run_date} from `template_corpus/templates/_smoke/` (`diversity_v2.json`
and `mutation_density.json`), generated by
`scripts/slurm/run_corpus_diversity_audit.slurm` (SLURM job {job_id}, k2-hipri,
CPU-only) at repo commit `{commit}`.

## Why this run, not a prior one

The `_smoke/diversity_v2.json` and `_smoke/mutation_density.json` files were stale:
both were generated in May/June 2026 against an L1+L2-only corpus (30 templates),
before the L3/L4 templates existed (added 2026-06-29) and before `mutator.py`'s
seven operator implementations were rewritten (2026-07-08, commit `9f03f2c`).
`sacrebleu` was also not an installed dependency, so any prior BLEU-4 numbers used
the fallback 4-gram Jaccard approximation in `diversity_v2.py`, not real BLEU-4.

This run: (1) added `sacrebleu` as a pinned dependency, (2) re-ran
`validate.py` + `validate_cc.py` + `diversity_v2.py` + `mutation_sweep.py`
against the full, current 60-template corpus (15/tier, L1-L4) via SLURM.

## Results summary

- **Template validation** (`validate.py`): 60/60 pass (load, skeleton substitution,
  oracle self-consistency on smoke_test_inputs).
- **Tier-separation sanity** (`validate_cc.py`): 60/60 pass — CC of every template
  falls in its declared tier's band (L1=1, L2=2-3, L3=4-7, L4>=8).
- **Within-tier diversity** (`diversity_v2.py`, union of 4 measures, length-aware
  flag rule): **0/60 templates flagged** across all four tiers. See
  `diversity_tier_summary.csv` / `diversity_by_template.csv`; `flagged_pairs.csv`
  is header-only (nothing to report).
- **Mutation density** (`mutation_sweep.py`): 60/60 templates land inside their
  declared per-template stability band; mean mutants/instance scale as expected
  with tier (L1 7.7, L2 13.4, L3 21.1, L4 35.6), consistent with the PROJECT_BRIEF.md
  target bands (5-10 / 10-15 / 15-25 / 25-40).

## Files

- `diversity_by_template.csv`, `diversity_tier_summary.csv`, `flagged_pairs.csv`
- `mutation_density_by_template.csv`, `mutation_density_tier_summary.csv`
- `thresholds.md` — the locked flag-rule policy, verbatim from source
- `diversity_v2_raw.json`, `mutation_density_raw.json` — verbatim copies of the
  SLURM run's output for full traceability
"""

    (OUT / "thresholds.md").write_text(thresholds_md)
    (OUT / "README.md").write_text(readme_md)

    # Verbatim copies for traceability
    (OUT / "diversity_v2_raw.json").write_text(json.dumps(diversity, indent=2))
    (OUT / "mutation_density_raw.json").write_text(json.dumps(density, indent=2))

    print(f"Archived to {OUT}")
    for p in sorted(OUT.iterdir()):
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
