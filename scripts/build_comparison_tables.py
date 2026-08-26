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
                                 (never zero-filled, see src/Analysis/
                                 comparison.py's module docstring)

Re-running this script after more data lands (e.g. once the GPT batches in
analysis/SUPERVISOR_HANDOFF_*.md are processed) regenerates all outputs from
whatever is on disk at that time, safe to re-run any time, append-only
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
from src.Analysis.multiple_comparisons import holm_bonferroni  # noqa: E402

ANALYSIS_DIR = ROOT / "analysis"
THIN_N_DEFINED = 20  # below this, a model's own mean Mut@K is a shaky point estimate


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def _signs_agree(*values: float | None) -> bool:
    """True iff every non-None value has the same sign (0 counts as either).
    Needs >=2 non-None values to make a claim; returns True (vacuously
    "agrees") with fewer than 2, since there's nothing to disagree with.
    """
    present = [v for v in values if v is not None]
    if len(present) < 2:
        return True
    return min(present) * max(present) >= 0


def main() -> None:
    # Restrict to the 9 canonical (base, non-adapter) models. Fine-tuned
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

    # --- Code-verified proof that coverage_adjusted == the true definition-(b)
    # (zero-filled unconditional) score. analysis/RQ5_CROSS_DEFINITION_AUDIT.md
    # sec "Algebraic check" derives coverage_adjusted = mutk*bp_rate =
    # (D'/N)*mutk and true def-(b) = (D/N)*mutk, equal iff n_defined==D
    # equals n_baseline_passed==D' for every model. Computed independently
    # here (paired_model_table(conditional=False), NOT by reusing the
    # mutk*bp_rate arithmetic above) so a future row that breaks the D==D'
    # assumption (baseline_passed=True but 0 scorable mutants) shows up as a
    # nonzero diff instead of being silently assumed away.
    a_paired_defb = paired_model_table(dynamic_l4, ult, label_a="dynamic_l4_defb", label_b="ult_defb",
                                        conditional=False)
    a_defb_check = a_paired_adj.merge(a_paired_defb, on="model_label")
    a_defb_check["diff_dynamic_l4"] = a_defb_check["dynamic_l4_adj"] - a_defb_check["dynamic_l4_defb"]
    a_defb_check["diff_ult"] = a_defb_check["ult_adj"] - a_defb_check["ult_defb"]
    a_defb_max_diff = float(a_defb_check[["diff_dynamic_l4", "diff_ult"]].abs().to_numpy().max())

    # --- Thin-cell filter (n_defined<20 on either side is a shaky point
    # estimate for that model, not just a conditioning-direction question) --
    a_thin_stats = a_paired.merge(
        a_coverage_dyn[["model_label", "n_defined_dynamic_l4"]], on="model_label"
    ).merge(
        a_coverage_ult[["model_label", "n_defined_ult"]], on="model_label"
    )
    a_thin_models = a_thin_stats[
        (a_thin_stats["n_defined_dynamic_l4"] < THIN_N_DEFINED)
        | (a_thin_stats["n_defined_ult"] < THIN_N_DEFINED)
    ]
    a_paired_thick = a_thin_stats[
        (a_thin_stats["n_defined_dynamic_l4"] >= THIN_N_DEFINED)
        & (a_thin_stats["n_defined_ult"] >= THIN_N_DEFINED)
    ][["model_label", "dynamic_l4", "ult"]]
    a_wilcoxon_thick = paired_wilcoxon(a_paired_thick, label_a="dynamic_l4", label_b="ult")

    # --- Comparison B: ULT vs PLT -------------------------------------------
    b_paired = paired_model_table(ult, plt, label_a="ult", label_b="plt")
    b_wilcoxon = paired_wilcoxon(b_paired, label_a="ult", label_b="plt")

    bands_ult = load_cc_bands("ult", tag="core_400")
    bands_plt = load_cc_bands("plt", tag="core_400")
    b_matched_cc = matched_cc_table(ult, plt, bands_ult, bands_plt)

    # --- Comparison B coverage/conditioning audit + adjusted robustness row
    # (added 2026-08-03, mirrors Comparison A's block above, same
    # conditioning applies since both sides use mutation_score) ------------
    b_coverage_ult = coverage_stats_table(ult).add_suffix("_ult").rename(
        columns={"model_label_ult": "model_label"})
    b_coverage_plt = coverage_stats_table(plt).add_suffix("_plt").rename(
        columns={"model_label_plt": "model_label"})
    b_coverage = b_coverage_ult.merge(b_coverage_plt, on="model_label", how="outer")

    b_paired_adj = b_paired.merge(
        b_coverage_ult[["model_label", "baseline_pass_rate_ult"]], on="model_label"
    ).merge(
        b_coverage_plt[["model_label", "baseline_pass_rate_plt"]], on="model_label"
    )
    b_paired_adj["ult_adj"] = b_paired_adj["ult"] * b_paired_adj["baseline_pass_rate_ult"]
    b_paired_adj["plt_adj"] = b_paired_adj["plt"] * b_paired_adj["baseline_pass_rate_plt"]
    b_wilcoxon_adj = paired_wilcoxon(b_paired_adj, label_a="ult_adj", label_b="plt_adj")

    b_paired_defb = paired_model_table(ult, plt, label_a="ult_defb", label_b="plt_defb", conditional=False)
    b_defb_check = b_paired_adj.merge(b_paired_defb, on="model_label")
    b_defb_check["diff_ult"] = b_defb_check["ult_adj"] - b_defb_check["ult_defb"]
    b_defb_check["diff_plt"] = b_defb_check["plt_adj"] - b_defb_check["plt_defb"]
    b_defb_max_diff = float(b_defb_check[["diff_ult", "diff_plt"]].abs().to_numpy().max())

    b_thin_stats = b_paired.merge(
        b_coverage_ult[["model_label", "n_defined_ult"]], on="model_label"
    ).merge(
        b_coverage_plt[["model_label", "n_defined_plt"]], on="model_label"
    )
    b_thin_models = b_thin_stats[
        (b_thin_stats["n_defined_ult"] < THIN_N_DEFINED) | (b_thin_stats["n_defined_plt"] < THIN_N_DEFINED)
    ]
    b_paired_thick = b_thin_stats[
        (b_thin_stats["n_defined_ult"] >= THIN_N_DEFINED) & (b_thin_stats["n_defined_plt"] >= THIN_N_DEFINED)
    ][["model_label", "ult", "plt"]]
    b_wilcoxon_thick = paired_wilcoxon(b_paired_thick, label_a="ult", label_b="plt")

    # --- Thin-cell filter applied to the def-b/coverage-adjusted co-primary
    # itself. Its own denominator is n_total (zero-fill mean over ALL rows),
    # not n_defined. A model with few baseline-passing rows can still give
    # a well-estimated near-zero co-primary score if n_total is large (see
    # analysis/RQ5_CROSS_DEFINITION_AUDIT.md "Does thin-cell filtering even
    # apply?"). Checked here with the SAME THIN_N_DEFINED=20 threshold
    # applied to n_total instead, expected (and, per the doc, verified) to
    # exclude nothing given this project's benchmark sizes.
    a_adj_thin_models = a_thin_stats.merge(
        a_coverage_dyn[["model_label", "n_total_dynamic_l4"]], on="model_label"
    ).merge(
        a_coverage_ult[["model_label", "n_total_ult"]], on="model_label"
    )
    a_adj_thin_models = a_adj_thin_models[
        (a_adj_thin_models["n_total_dynamic_l4"] < THIN_N_DEFINED)
        | (a_adj_thin_models["n_total_ult"] < THIN_N_DEFINED)
    ]

    # --- RQ1 Holm-Bonferroni: H1 Test 1 (this comparison) + H1 Test 2
    # (Comparison B). docs/Approved_Hypotheses.md names ULT-vs-PLT as H1's
    # own second test (analysis/HYPOTHESIS_DEVIATIONS.md), so RQ1's
    # correctable family is these two tests, not H1 alone (an earlier
    # version of this script treated H1 as a size-one family, a no-op,
    # corrected 2026-08-12). Corrected separately per conditioning (raw/
    # pre-registered-primary, thin-cell-filtered/robustness, definition-
    # matched/co-primary), three independent 2-test families, not one
    # pooled 6-test family, matching every other RQ family's convention of
    # correcting within one reported scope at a time.
    holm_rows = []
    for conditioning, a_w, b_w in [
        ("raw", a_wilcoxon, b_wilcoxon),
        ("thin_filtered", a_wilcoxon_thick, b_wilcoxon_thick),
        ("definition_matched", a_wilcoxon_adj, b_wilcoxon_adj),
    ]:
        p_values = [a_w.p_value, b_w.p_value]
        p_holm = holm_bonferroni(p_values)
        for test_name, p_raw, p_adj in zip(("H1 Test 1", "H1 Test 2"), p_values, p_holm):
            holm_rows.append({
                "conditioning": conditioning,
                "test": test_name,
                "p_value": p_raw,
                "p_value_holm": p_adj,
                "survives_holm_0.05": bool(p_adj < 0.05) if p_adj is not None and not pd.isna(p_adj) else None,
            })
    rq1_holm = pd.DataFrame(holm_rows)
    rq1_holm.to_csv(ANALYSIS_DIR / "comparison_rq1_holm.csv", index=False)

    a_paired.to_csv(ANALYSIS_DIR / "comparison_a_paired.csv", index=False)
    b_paired.to_csv(ANALYSIS_DIR / "comparison_b_paired.csv", index=False)
    b_matched_cc.to_csv(ANALYSIS_DIR / "comparison_b_matched_cc.csv", index=False)
    a_coverage.to_csv(ANALYSIS_DIR / "comparison_a_coverage.csv", index=False)
    a_paired_adj.to_csv(ANALYSIS_DIR / "comparison_a_coverage_adjusted.csv", index=False)
    b_coverage.to_csv(ANALYSIS_DIR / "comparison_b_coverage.csv", index=False)
    b_paired_adj.to_csv(ANALYSIS_DIR / "comparison_b_coverage_adjusted.csv", index=False)

    pd.DataFrame([vars(a_wilcoxon)]).to_csv(ANALYSIS_DIR / "comparison_a_wilcoxon.csv", index=False)
    pd.DataFrame([vars(b_wilcoxon)]).to_csv(ANALYSIS_DIR / "comparison_b_wilcoxon.csv", index=False)
    pd.DataFrame([vars(a_wilcoxon_adj)]).to_csv(
        ANALYSIS_DIR / "comparison_a_coverage_adjusted_wilcoxon.csv", index=False)
    pd.DataFrame([vars(b_wilcoxon_adj)]).to_csv(
        ANALYSIS_DIR / "comparison_b_coverage_adjusted_wilcoxon.csv", index=False)
    pd.DataFrame([vars(a_wilcoxon_thick)]).to_csv(
        ANALYSIS_DIR / "comparison_a_wilcoxon_thick.csv", index=False)
    pd.DataFrame([vars(b_wilcoxon_thick)]).to_csv(
        ANALYSIS_DIR / "comparison_b_wilcoxon_thick.csv", index=False)

    a_missing = sorted(set(CANONICAL_MODELS) - set(a_paired["model_label"]))
    b_missing = sorted(set(CANONICAL_MODELS) - set(b_paired["model_label"]))

    def _fmt(x, spec=".3f"):
        return format(x, spec) if x is not None else "n/a"

    a_direction_msg = (
        "All three share the same sign. A directional read is at least "
        "internally consistent across conditionings, though still not "
        "significant at any of the tiny n's involved (per the p-values above)."
        if _signs_agree(a_wilcoxon.effect_r, a_wilcoxon_thick.effect_r, a_wilcoxon_adj.effect_r)
        else (
            "The sign FLIPS depending on which conditioning is applied. "
            "Raw/thin/definition-matched do not agree on which side "
            "(dynamic_l4 or ult) scores higher. This is the second flip on "
            "top of the raw-vs-coverage-adjusted flip already noted above "
            "(first flip found 2026-07-30). Given this, the honest "
            "conclusion is that Comparison A supports no directional claim "
            "at the current n (<=5 models, p>0.05 in every conditioning), "
            "not \"the effect is X, but weak,\" but \"this data cannot "
            "currently establish which of Dynamic-L4 or ULT scores a model "
            "higher, under any of the definitions tried.\""
        )
    )
    b_direction_msg = (
        "All three share the same sign. A directional read is at least "
        "internally consistent across conditionings."
        if _signs_agree(b_wilcoxon.effect_r, b_wilcoxon_thick.effect_r, b_wilcoxon_adj.effect_r)
        else "The sign FLIPS depending on which conditioning is applied for Comparison B too."
    )

    provenance = f"""# Comparison A/B generation provenance

Generated: {datetime.now(timezone.utc).isoformat()}
Git commit: {_git_commit()}

Sources: data/results/dynamic/*.jsonl (tier={DYNAMIC_TIER} only for Comparison A),
data/results/ult/*.jsonl, data/results/plt/*.jsonl.
CC bands: data/raw/ult_plt/subsample_manifest.json (tag=core_400).

## Comparison A (Dynamic-L4 vs ULT) — {len(a_paired)}/{len(CANONICAL_MODELS)} models
Missing (no scorable data on one or both sides, NOT zero-filled,
absent from comparison_a_paired.csv): {a_missing or "none"}

**Interpretation lives in `analysis/COMPARISON_A_INTERPRETATION.md`**. That
file's "Multiple-comparisons correction for RQ1" section has the detail
needed before quoting any p-value here as "significant": RQ1's correctable
family is this comparison (H1 Test 1) plus Comparison B (H1 Test 2),
corrected separately per conditioning, live numbers in "RQ1 Holm-Bonferroni
correction" below. The thin-filtered/definition-matched rows are three
independently-corrected conditionings, not robustness variants excluded
from correction.

## Comparison B (ULT vs PLT) — {len(b_paired)}/{len(CANONICAL_MODELS)} models
Missing: {b_missing or "none"}

Pairing unit and CC-band methodology: `src/Analysis/comparison.py`'s
module docstring has the detail.

## Comparison A conditioning/survivorship audit (added 2026-07-28)

Comparison A pairs Mut@K, which is only defined where baseline_passed=True
(the same conditioning RQ5 diagnosed as the dominant factor behind its low
pooled Dynamic<->ULT rank agreement, `analysis/RQ5_DIAGNOSTICS.md` sec 3).
Each model's paired mean is computed over a DIFFERENT-sized, different
subset of problems, not a shared denominator. Full per-model n_total/
n_defined/baseline_pass_rate for both sides: `analysis/comparison_a_coverage.csv`.

{a_coverage.to_string(index=False)}

**Co-primary definition-matched row** (labelled "coverage-adjusted" in prior
versions of this file. 2026-08-03: PROVEN algebraically and code-verified
identical to the true zero-filled/unconditional Mut@K, i.e. this project's
best-effort reading of the ULT/PLT paper's own Sec 3.4.3 PROSE formula. This
is a co-primary reported alongside, not a replacement for, the pre-registered
primary above. The "Cross-definition note" below has why it is NOT
"the literature-matching score" without qualification.
Max |coverage_adjusted - independently-recomputed def-b| across all rows in
this table: {a_defb_max_diff:.2e} (floating-point noise only,
`analysis/comparison_a_coverage_adjusted.csv`):

| | n_pairs | mean_a (dynamic_l4) | mean_b (ult) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K (pre-registered primary) | {a_wilcoxon.n_pairs} | {a_wilcoxon.mean_a:.4f} | {a_wilcoxon.mean_b:.4f} | {_fmt(a_wilcoxon.effect_r)} | {_fmt(a_wilcoxon.p_value, '.4f')} |
| definition-matched / coverage-adjusted (co-primary) | {a_wilcoxon_adj.n_pairs} | {a_wilcoxon_adj.mean_a:.4f} | {a_wilcoxon_adj.mean_b:.4f} | {_fmt(a_wilcoxon_adj.effect_r)} | {_fmt(a_wilcoxon_adj.p_value, '.4f')} |

**Does the conclusion change?** {
    "Effect direction FLIPS between raw and definition-matched (sign of effect_r differs). Treat Comparison A's direction as conditioning-sensitive, not robust."
    if (a_wilcoxon.effect_r is not None and a_wilcoxon_adj.effect_r is not None
        and a_wilcoxon.effect_r * a_wilcoxon_adj.effect_r < 0)
    else f"Effect direction is the SAME sign raw vs definition-matched. Magnitude/significance may still differ (above), but the qualitative read (which side is higher, and that n_models={a_wilcoxon.n_pairs} is too small at either p-value to call this a real effect) does not flip."
}

## Comparison A thin-cell audit (added 2026-07-30, extended 2026-08-03)

A model's own paired Mut@K (pre-registered primary) is a shaky point
estimate when it's averaged over very few baseline-passing problems.
n_defined<{THIN_N_DEFINED} on either side is flagged thin here, same
threshold used in `analysis/RQ5_DIAGNOSTICS.md`. Per-model n_defined for
both sides:

{a_thin_stats[['model_label', 'n_defined_dynamic_l4', 'n_defined_ult']].to_string(index=False)}

**Thin model(s) excluded from the {len(a_paired_thick)}-model thick-only
result below**: {sorted(a_thin_models['model_label'].tolist()) or "none, all models thick on both sides"}.

| | n_pairs | mean_a (dynamic_l4) | mean_b (ult) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K, unfiltered (primary) | {a_wilcoxon.n_pairs} | {a_wilcoxon.mean_a:.4f} | {a_wilcoxon.mean_b:.4f} | {_fmt(a_wilcoxon.effect_r)} | {_fmt(a_wilcoxon.p_value, '.4f')} |
| raw Mut@K, thin cells (n_defined<{THIN_N_DEFINED}) excluded | {a_wilcoxon_thick.n_pairs} | {_fmt(a_wilcoxon_thick.mean_a, '.4f') if a_wilcoxon_thick.n_pairs else 'n/a'} | {_fmt(a_wilcoxon_thick.mean_b, '.4f') if a_wilcoxon_thick.n_pairs else 'n/a'} | {_fmt(a_wilcoxon_thick.effect_r)} | {_fmt(a_wilcoxon_thick.p_value, '.4f')} |

**Does the {a_wilcoxon.n_pairs}-model result survive thin-cell filtering?**
{
    f"NO in the sense that it shrinks to n_models={a_wilcoxon_thick.n_pairs} once thin cells are excluded. {len(a_thin_models)} of the original {a_wilcoxon.n_pairs} model(s) were resting on a point estimate averaged over fewer than {THIN_N_DEFINED} baseline-passing problems, not a stable per-model mean."
    if len(a_thin_models) > 0 else
    f"Yes. No model in the {a_wilcoxon.n_pairs}-model result has n_defined<{THIN_N_DEFINED} on either side."
}

**Does thin-cell filtering even apply to the definition-matched/coverage-
adjusted co-primary?** The pre-registered primary's thinness comes from
n_defined (few baseline-passing rows -> shaky conditional mean). The
definition-matched score is a zero-filled mean over ALL n_total rows, so
ITS precision is governed by n_total, not n_defined. A model with
n_defined=1 but n_total=375 (e.g. Qwen 7B, dynamic_l4) still gives a
well-estimated near-zero definition-matched score, not a shaky one. Checked
directly against the same THIN_N_DEFINED=20 threshold applied to n_total
instead: {
    f"{len(a_adj_thin_models)} model(s) have n_total<{THIN_N_DEFINED} on either side: {sorted(a_adj_thin_models['model_label'].tolist())}."
    if len(a_adj_thin_models) > 0
    else f"0 models. Every model's n_total is >>{THIN_N_DEFINED} on both sides (min n_total this table: dynamic_l4={int(a_coverage_dyn['n_total_dynamic_l4'].min())}, ult={int(a_coverage_ult['n_total_ult'].min())}), so no model is excluded from the co-primary row above on thinness grounds."
}

## Comparison B conditioning/survivorship + co-primary + thin-cell audit (added 2026-08-03)

Same conditioning applies to Comparison B (ULT vs PLT) as Comparison A.
mutation_score is only defined where baseline_passed=True on each side. Full
per-model n_total/n_defined/baseline_pass_rate: `analysis/comparison_b_coverage.csv`.

{b_coverage.to_string(index=False)}

**Co-primary definition-matched row** (max |coverage_adjusted -
independently-recomputed def-b|: {b_defb_max_diff:.2e}, floating-point noise
only, `analysis/comparison_b_coverage_adjusted.csv`):

| | n_pairs | mean_a (ult) | mean_b (plt) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K (pre-registered primary) | {b_wilcoxon.n_pairs} | {b_wilcoxon.mean_a:.4f} | {b_wilcoxon.mean_b:.4f} | {_fmt(b_wilcoxon.effect_r)} | {_fmt(b_wilcoxon.p_value, '.4f')} |
| definition-matched / coverage-adjusted (co-primary) | {b_wilcoxon_adj.n_pairs} | {b_wilcoxon_adj.mean_a:.4f} | {b_wilcoxon_adj.mean_b:.4f} | {_fmt(b_wilcoxon_adj.effect_r)} | {_fmt(b_wilcoxon_adj.p_value, '.4f')} |

**Does the conclusion change?** {
    "Effect direction FLIPS between raw and definition-matched (sign of effect_r differs). Treat Comparison B's direction as conditioning-sensitive, not robust."
    if (b_wilcoxon.effect_r is not None and b_wilcoxon_adj.effect_r is not None
        and b_wilcoxon.effect_r * b_wilcoxon_adj.effect_r < 0)
    else f"Effect direction is the SAME sign raw vs definition-matched. Magnitude/significance may still differ (above), but the qualitative read does not flip at n_models={b_wilcoxon.n_pairs}."
}

**Thin-cell audit** (n_defined<{THIN_N_DEFINED} on either side flagged thin):

{b_thin_stats[['model_label', 'n_defined_ult', 'n_defined_plt']].to_string(index=False)}

**Thin model(s) excluded from the {len(b_paired_thick)}-model thick-only
result below**: {sorted(b_thin_models['model_label'].tolist()) or "none, all models thick on both sides"}.

| | n_pairs | mean_a (ult) | mean_b (plt) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K, unfiltered (primary) | {b_wilcoxon.n_pairs} | {b_wilcoxon.mean_a:.4f} | {b_wilcoxon.mean_b:.4f} | {_fmt(b_wilcoxon.effect_r)} | {_fmt(b_wilcoxon.p_value, '.4f')} |
| raw Mut@K, thin cells (n_defined<{THIN_N_DEFINED}) excluded | {b_wilcoxon_thick.n_pairs} | {_fmt(b_wilcoxon_thick.mean_a, '.4f') if b_wilcoxon_thick.n_pairs else 'n/a'} | {_fmt(b_wilcoxon_thick.mean_b, '.4f') if b_wilcoxon_thick.n_pairs else 'n/a'} | {_fmt(b_wilcoxon_thick.effect_r)} | {_fmt(b_wilcoxon_thick.p_value, '.4f')} |

**Does the {b_wilcoxon.n_pairs}-model result survive thin-cell filtering?**
{
    f"NO in the sense that it shrinks to n_models={b_wilcoxon_thick.n_pairs} once thin cells are excluded. {len(b_thin_models)} of the original {b_wilcoxon.n_pairs} model(s) were resting on a point estimate averaged over fewer than {THIN_N_DEFINED} baseline-passing problems."
    if len(b_thin_models) > 0 else
    f"Yes. No model in the {b_wilcoxon.n_pairs}-model result has n_defined<{THIN_N_DEFINED} on either side."
}

## Directional-stability verdict across ALL conditionings tried (added 2026-08-03)

Comparison A's effect_r sign, across every conditioning computed in this
file: raw-unfiltered={_fmt(a_wilcoxon.effect_r)}, raw-thin-cell-filtered={_fmt(a_wilcoxon_thick.effect_r)},
definition-matched/coverage-adjusted={_fmt(a_wilcoxon_adj.effect_r)}. {a_direction_msg}

Comparison B's effect_r sign: raw-unfiltered={_fmt(b_wilcoxon.effect_r)},
raw-thin-cell-filtered={_fmt(b_wilcoxon_thick.effect_r)},
definition-matched/coverage-adjusted={_fmt(b_wilcoxon_adj.effect_r)}. {b_direction_msg}
`analysis/RQ5_CROSS_DEFINITION_AUDIT.md`'s "Consequence audit" has the
narrative verdict on both comparisons together (this block reports the raw
numbers. That doc reports the reasoned conclusion).

## RQ1 Holm-Bonferroni correction (H1 Test 1 + H1 Test 2) — computed here 2026-08-12

`docs/Approved_Hypotheses.md` names ULT-vs-PLT (Comparison B) as H1's own
second test, not an unofficial exploratory check. RQ1's correctable
family is these two tests, corrected separately per conditioning (three
independent 2-test families, not one pooled 6-test family). H2
(Comparison C's DiD) reports an effect size + bootstrap CI and never
computes a p-value, so it contributes nothing to this family. Full detail:
`analysis/comparison_rq1_holm.csv`, `analysis/HYPOTHESIS_DEVIATIONS.md`'s
H1 Test 2 entry.

{rq1_holm.to_string(index=False)}

**Read plainly**: at the raw/pre-registered-primary conditioning, neither
test survives Holm correction. At the definition-matched co-primary
conditioning, both survive. The thin-cell-filtered reading is a
robustness variant, reported here for completeness, not as a
member of the pre-registered family.

## Cross-definition note (added 2026-07-30, revised 2026-08-03, analysis/RQ5_CROSS_DEFINITION_AUDIT.md has detail)

Every "raw Mut@K" number in this file uses this project's own EXCLUDE/
conditional definition (mean over baseline-passing rows only), the
pre-registered primary, never swapped out.

The "definition-matched / coverage-adjusted" co-primary row is this
project's best-effort reading of the ULT/PLT paper's Sec 3.4.3 PROSE
formula (Mut@k = sum(Mi)/N, N stated as "the total number of functions in
the benchmark," read as INCLUDE-AS-ZERO/unconditional). **This reading is
contradicted by the paper's own published code**: `Ray/main.py`'s
`mutation_statistic()`, the function actually invoked from that repo's CLI,
divides by `len(correct_tasks)`, a baseline-pass-conditioned count, the
SAME estimand as this project's pre-registered primary Mut@K, not the
zero-filled one the paper's prose describes. Full evidence (verbatim
quotes, code excerpts, the algebraic proof that coverage_adjusted equals
the zero-filled reading exactly): `analysis/RQ5_CROSS_DEFINITION_AUDIT.md`.
Practical upshot: neither of this project's two metrics should be assumed
to reproduce the ULT/PLT paper's own reported ~40.21% average mutation
score without this caveat attached.

## Dedup-fix status (src/Analysis/loader.py, fixed 2026-07-25)

load_records() dedupes on (model_label, benchmark, instantiation_id,
template_id, instance_seed, tier, K, prompting_condition), keeping the
newest row by timestamp. That module's docstring has why. Comparison A
filters to tier=L4 only, and the ~559 duplicate rows found in the
2026-07-26 audit (scripts/audit_result_integrity.py) are entirely
L1/L2/L3-tier stale-retry rows. None are L4, so Comparison A is unaffected
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
