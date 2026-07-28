"""Build Comparison A (Dynamic vs ULT, RQ1/H1) and Comparison B (ULT vs PLT,
observational contamination signal) tables from real result files.

Writes to analysis/:
  comparison_a_paired.csv       per-model mean Mut@K, Dynamic-L4 vs ULT
  comparison_a_wilcoxon.csv     paired Wilcoxon signed-rank across models (H1)
  comparison_b_paired.csv       per-model mean Mut@K, ULT vs PLT
  comparison_b_wilcoxon.csv     paired Wilcoxon signed-rank across models
  comparison_b_matched_cc.csv   per-CC-band ULT vs PLT mean Mut@K
  COMPARISON_PROVENANCE.md      generation timestamp, git commit, data
                                 sources, and which of the 9 canonical
                                 models are still missing from each table
                                 (never zero-filled — see src/Analysis/
                                 comparison.py's module docstring)

Re-running this script after more data lands (e.g. once the GPT batches in
analysis/SUPERVISOR_HANDOFF_*.md are processed) regenerates all outputs from
whatever is on disk at that time — safe to re-run any time, append-only
result files are never modified.

Usage:
    python scripts/build_comparison_tables.py
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd

from coverage_matrix import CANONICAL_MODELS  # noqa: E402
from src.Analysis.comparison import (  # noqa: E402
    DYNAMIC_TIER,
    coverage_stats_table,
    load_cc_bands,
    matched_cc_table,
    paired_model_table,
    paired_wilcoxon,
)
from src.Analysis.loader import load_records  # noqa: E402

ANALYSIS_DIR = ROOT / "analysis"


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def main() -> None:
    # Restrict to the 9 canonical (base, non-adapter) models -- fine-tuned
    # variants (the six supplementary-study adapters, and now the canonical
    # Comparison C adapter) are a different model identity
    # (compute_model_label) and must never silently enter a Comparison A/B
    # mean. Caught 2026-07-27: the Comparison C adapter's ULT/PLT rows (its
    # mutation_score is defined for plenty of rows, unlike its floor-limited
    # Dynamic-L4 rows, which is why this leak only showed up in Comparison B)
    # appeared as an extra row in comparison_b_paired.csv before this filter.
    dynamic = load_records("data/results/dynamic", benchmark="dynamic")
    ult = load_records("data/results/ult", benchmark="ult")
    plt = load_records("data/results/plt", benchmark="plt")
    dynamic = dynamic[dynamic["model_label"].isin(CANONICAL_MODELS)]
    ult = ult[ult["model_label"].isin(CANONICAL_MODELS)]
    plt = plt[plt["model_label"].isin(CANONICAL_MODELS)]

    dynamic_l4 = dynamic[dynamic["tier"] == DYNAMIC_TIER]

    # --- Comparison A: Dynamic (L4) vs ULT ---------------------------------
    a_paired = paired_model_table(dynamic_l4, ult, label_a="dynamic_l4", label_b="ult")
    a_wilcoxon = paired_wilcoxon(a_paired, label_a="dynamic_l4", label_b="ult")

    # --- Comparison A coverage/conditioning audit + adjusted robustness row -
    # Comparison A pairs Mut@K, which is only defined where baseline_passed=True
    # (same conditioning RQ5 diagnosed, analysis/RQ5_DIAGNOSTICS.md sec 3) --
    # each model's paired mean is a different-sized, different subset of
    # problems. Reported explicitly + re-run on the coverage-adjusted score
    # (Mut@K x baseline_pass_rate) as a robustness check, not a replacement.
    a_coverage_dyn = coverage_stats_table(dynamic_l4).add_suffix("_dynamic_l4").rename(
        columns={"model_label_dynamic_l4": "model_label"})
    a_coverage_ult = coverage_stats_table(ult).add_suffix("_ult").rename(
        columns={"model_label_ult": "model_label"})
    a_coverage = a_coverage_dyn.merge(a_coverage_ult, on="model_label", how="outer")

    a_paired_adj = a_paired.merge(
        a_coverage_dyn[["model_label", "baseline_pass_rate_dynamic_l4"]], on="model_label"
    ).merge(
        a_coverage_ult[["model_label", "baseline_pass_rate_ult"]], on="model_label"
    )
    a_paired_adj["dynamic_l4_adj"] = a_paired_adj["dynamic_l4"] * a_paired_adj["baseline_pass_rate_dynamic_l4"]
    a_paired_adj["ult_adj"] = a_paired_adj["ult"] * a_paired_adj["baseline_pass_rate_ult"]
    a_wilcoxon_adj = paired_wilcoxon(a_paired_adj, label_a="dynamic_l4_adj", label_b="ult_adj")

    # --- Comparison B: ULT vs PLT -------------------------------------------
    b_paired = paired_model_table(ult, plt, label_a="ult", label_b="plt")
    b_wilcoxon = paired_wilcoxon(b_paired, label_a="ult", label_b="plt")

    bands_ult = load_cc_bands("ult", tag="core_400")
    bands_plt = load_cc_bands("plt", tag="core_400")
    b_matched_cc = matched_cc_table(ult, plt, bands_ult, bands_plt)

    a_paired.to_csv(ANALYSIS_DIR / "comparison_a_paired.csv", index=False)
    b_paired.to_csv(ANALYSIS_DIR / "comparison_b_paired.csv", index=False)
    b_matched_cc.to_csv(ANALYSIS_DIR / "comparison_b_matched_cc.csv", index=False)
    a_coverage.to_csv(ANALYSIS_DIR / "comparison_a_coverage.csv", index=False)
    a_paired_adj.to_csv(ANALYSIS_DIR / "comparison_a_coverage_adjusted.csv", index=False)

    pd.DataFrame([vars(a_wilcoxon)]).to_csv(ANALYSIS_DIR / "comparison_a_wilcoxon.csv", index=False)
    pd.DataFrame([vars(b_wilcoxon)]).to_csv(ANALYSIS_DIR / "comparison_b_wilcoxon.csv", index=False)
    pd.DataFrame([vars(a_wilcoxon_adj)]).to_csv(
        ANALYSIS_DIR / "comparison_a_coverage_adjusted_wilcoxon.csv", index=False)

    a_missing = sorted(set(CANONICAL_MODELS) - set(a_paired["model_label"]))
    b_missing = sorted(set(CANONICAL_MODELS) - set(b_paired["model_label"]))

    provenance = f"""# Comparison A/B generation provenance

Generated: {datetime.now(timezone.utc).isoformat()}
Git commit: {_git_commit()}

Sources: data/results/dynamic/*.jsonl (tier={DYNAMIC_TIER} only for Comparison A),
data/results/ult/*.jsonl, data/results/plt/*.jsonl.
CC bands: data/raw/ult_plt/subsample_manifest.json (tag=core_400).

## Comparison A (Dynamic-L4 vs ULT) — {len(a_paired)}/{len(CANONICAL_MODELS)} models
Missing (no scorable data on one or both sides — NOT zero-filled, simply
absent from comparison_a_paired.csv): {a_missing or "none"}

## Comparison B (ULT vs PLT) — {len(b_paired)}/{len(CANONICAL_MODELS)} models
Missing: {b_missing or "none"}

Pairing unit and CC-band methodology: see src/Analysis/comparison.py's
module docstring.

## Comparison A conditioning/survivorship audit (added 2026-07-28)

Comparison A pairs Mut@K, which is only defined where baseline_passed=True
(the same conditioning RQ5 diagnosed as the dominant factor behind its low
pooled Dynamic<->ULT rank agreement, `analysis/RQ5_DIAGNOSTICS.md` sec 3) --
each model's paired mean is computed over a DIFFERENT-sized, different
subset of problems, not a shared denominator. Full per-model n_total/
n_defined/baseline_pass_rate for both sides: `analysis/comparison_a_coverage.csv`.

{a_coverage.to_string(index=False)}

**Coverage-adjusted robustness row** (Mut@K x baseline_pass_rate per side,
folds the conditioning back in -- NOT the same estimand as Mut@K itself,
`analysis/comparison_a_coverage_adjusted.csv` /
`analysis/comparison_a_coverage_adjusted_wilcoxon.csv`):

| | n_pairs | mean_a (dynamic_l4) | mean_b (ult) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K (primary) | {a_wilcoxon.n_pairs} | {a_wilcoxon.mean_a:.4f} | {a_wilcoxon.mean_b:.4f} | {a_wilcoxon.effect_r:.3f} | {a_wilcoxon.p_value:.4f} |
| coverage-adjusted (robustness) | {a_wilcoxon_adj.n_pairs} | {a_wilcoxon_adj.mean_a:.4f} | {a_wilcoxon_adj.mean_b:.4f} | {a_wilcoxon_adj.effect_r:.3f} | {a_wilcoxon_adj.p_value:.4f} |

**Does the conclusion change?** {
    "Effect direction FLIPS between raw and coverage-adjusted (sign of effect_r differs) -- treat Comparison A's direction as conditioning-sensitive, not robust."
    if (a_wilcoxon.effect_r is not None and a_wilcoxon_adj.effect_r is not None
        and a_wilcoxon.effect_r * a_wilcoxon_adj.effect_r < 0)
    else f"Effect direction is the SAME sign raw vs coverage-adjusted; magnitude/significance may still differ (see table above), but the qualitative read (which side is higher, and that n={a_wilcoxon.n_pairs} is too small at either p-value to call this a real effect) does not flip."
}

## Dedup-fix status (src/Analysis/loader.py, fixed 2026-07-25)

load_records() dedupes on (model_label, benchmark, instantiation_id,
template_id, instance_seed, tier, K, prompting_condition), keeping the
newest row by timestamp -- see that module's docstring for why. Comparison A
filters to tier=L4 only, and the ~559 duplicate rows found in the
2026-07-26 audit (scripts/audit_result_integrity.py) are entirely
L1/L2/L3-tier stale-retry rows -- none are L4, so Comparison A is unaffected
regardless of whether this table predates or postdates the loader fix.
Comparison B reads data/results/ult|plt/ directly, which the same audit
found have zero duplicate keys. Both tables here are correct independent of
generation order relative to the loader fix.
"""
    (ANALYSIS_DIR / "COMPARISON_PROVENANCE.md").write_text(provenance)

    print(provenance)
    print("Comparison A paired table:")
    print(a_paired.to_string(index=False))
    print("\nComparison A Wilcoxon:", vars(a_wilcoxon))
    print("\nComparison B paired table:")
    print(b_paired.to_string(index=False))
    print("\nComparison B Wilcoxon:", vars(b_wilcoxon))
    print("\nComparison B matched-CC table:")
    print(b_matched_cc.to_string(index=False))


if __name__ == "__main__":
    main()
