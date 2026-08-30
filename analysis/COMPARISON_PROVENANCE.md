# Comparison A/B generation provenance

Generated: 2026-08-29T23:30:24.100606+00:00
Git commit: 9cdef55

Sources: data/results/dynamic/*.jsonl (tier=L4 only for Comparison A),
data/results/ult/*.jsonl, data/results/plt/*.jsonl.
CC bands: data/raw/ult_plt/subsample_manifest.json (tag=core_400).

## Comparison A (Dynamic-L4 vs ULT) — 8/9 models
Missing (no scorable data on one or both sides, NOT zero-filled,
absent from comparison_a_paired.csv): ['Qwen__Qwen2.5-Coder-1.5B-Instruct']

**Interpretation lives in `analysis/COMPARISON_A_INTERPRETATION.md`**. That
file's "Multiple-comparisons correction for RQ1" section has the detail
needed before quoting any p-value here as "significant": RQ1's correctable
family is this comparison (H1 Test 1) plus Comparison B (H1 Test 2),
corrected separately per conditioning, live numbers in "RQ1 Holm-Bonferroni
correction" below. The thin-filtered/definition-matched rows are three
independently-corrected conditionings, not robustness variants excluded
from correction.

## Comparison B (ULT vs PLT) — 9/9 models
Missing: none

Pairing unit and CC-band methodology: `src/Analysis/comparison.py`'s
module docstring has the detail.

## Comparison A conditioning/survivorship audit (added 2026-07-28)

Comparison A pairs Mut@K, which is only defined where baseline_passed=True
(the same conditioning RQ5 diagnosed as the dominant factor behind its low
pooled Dynamic<->ULT rank agreement, `analysis/RQ5_DIAGNOSTICS.md` sec 3).
Each model's paired mean is computed over a DIFFERENT-sized, different
subset of problems, not a shared denominator. Full per-model n_total/
n_defined/baseline_pass_rate for both sides: `analysis/comparison_a_coverage.csv`.

                      model_label  n_total_dynamic_l4  n_defined_dynamic_l4  baseline_pass_rate_dynamic_l4  n_total_ult  n_defined_ult  baseline_pass_rate_ult
Qwen__Qwen2.5-Coder-1.5B-Instruct                 375                     0                       0.000000          400              8                0.020000
 Qwen__Qwen2.5-Coder-32B-Instruct                 375                    13                       0.034667          400             31                0.077500
  Qwen__Qwen2.5-Coder-7B-Instruct                 375                     1                       0.002667          400              7                0.017500
        claude-haiku-4-5-20251001                 375                    98                       0.261333          400             35                0.087500
                claude-sonnet-4-6                 375                   123                       0.328000          400             78                0.195000
            gemini-3.1-flash-lite                 300                   145                       0.483333          400            106                0.265000
           gemini-3.1-pro-preview                 300                   292                       0.973333          101             74                0.732673
                 gpt-5-2025-08-07                 375                   361                       0.962667          400            279                0.697500
            gpt-5-mini-2025-08-07                 375                   306                       0.816000          400            219                0.547500

**Co-primary definition-matched row** (labelled "coverage-adjusted" in prior
versions of this file. 2026-08-03: PROVEN algebraically and code-verified
identical to the true zero-filled/unconditional Mut@K, i.e. this project's
best-effort reading of the ULT/PLT paper's own Sec 3.4.3 PROSE formula. This
is a co-primary reported alongside, not a replacement for, the pre-registered
primary above. The "Cross-definition note" below has why it is NOT
"the literature-matching score" without qualification.
Max |coverage_adjusted - independently-recomputed def-b| across all rows in
this table: 5.55e-17 (floating-point noise only,
`analysis/comparison_a_coverage_adjusted.csv`):

| | n_pairs | mean_a (dynamic_l4) | mean_b (ult) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K (pre-registered primary) | 8 | 0.7996 | 0.8477 | -0.167 | 0.7422 |
| definition-matched / coverage-adjusted (co-primary) | 8 | 0.4312 | 0.2804 | -0.833 | 0.0391 |

**Does the conclusion change?** Effect direction is the SAME sign raw vs definition-matched. Magnitude/significance may still differ (above), but the qualitative read (which side is higher, and that n_models=8 is too small at either p-value to call this a real effect) does not flip.

## Comparison A thin-cell audit (added 2026-07-30, extended 2026-08-03)

A model's own paired Mut@K (pre-registered primary) is a shaky point
estimate when it's averaged over very few baseline-passing problems.
n_defined<20 on either side is flagged thin here, same
threshold used in `analysis/RQ5_DIAGNOSTICS.md`. Per-model n_defined for
both sides:

                     model_label  n_defined_dynamic_l4  n_defined_ult
Qwen__Qwen2.5-Coder-32B-Instruct                    13             31
 Qwen__Qwen2.5-Coder-7B-Instruct                     1              7
       claude-haiku-4-5-20251001                    98             35
               claude-sonnet-4-6                   123             78
           gemini-3.1-flash-lite                   145            106
          gemini-3.1-pro-preview                   292             74
                gpt-5-2025-08-07                   361            279
           gpt-5-mini-2025-08-07                   306            219

**Thin model(s) excluded from the 6-model thick-only
result below**: ['Qwen__Qwen2.5-Coder-32B-Instruct', 'Qwen__Qwen2.5-Coder-7B-Instruct'].

| | n_pairs | mean_a (dynamic_l4) | mean_b (ult) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K, unfiltered (primary) | 8 | 0.7996 | 0.8477 | -0.167 | 0.7422 |
| raw Mut@K, thin cells (n_defined<20) excluded | 6 | 0.8849 | 0.8311 | -1.000 | 0.0312 |

**Does the 8-model result survive thin-cell filtering?**
NO in the sense that it shrinks to n_models=6 once thin cells are excluded. 2 of the original 8 model(s) were resting on a point estimate averaged over fewer than 20 baseline-passing problems, not a stable per-model mean.

**Does thin-cell filtering even apply to the definition-matched/coverage-
adjusted co-primary?** The pre-registered primary's thinness comes from
n_defined (few baseline-passing rows -> shaky conditional mean). The
definition-matched score is a zero-filled mean over ALL n_total rows, so
ITS precision is governed by n_total, not n_defined. A model with
n_defined=1 but n_total=375 (e.g. Qwen 7B, dynamic_l4) still gives a
well-estimated near-zero definition-matched score, not a shaky one. Checked
directly against the same THIN_N_DEFINED=20 threshold applied to n_total
instead: 0 models. Every model's n_total is >>20 on both sides (min n_total this table: dynamic_l4=300, ult=101), so no model is excluded from the co-primary row above on thinness grounds.

## Comparison B conditioning/survivorship + co-primary + thin-cell audit (added 2026-08-03)

Same conditioning applies to Comparison B (ULT vs PLT) as Comparison A.
mutation_score is only defined where baseline_passed=True on each side. Full
per-model n_total/n_defined/baseline_pass_rate: `analysis/comparison_b_coverage.csv`.

                      model_label  n_total_ult  n_defined_ult  baseline_pass_rate_ult  n_total_plt  n_defined_plt  baseline_pass_rate_plt
Qwen__Qwen2.5-Coder-1.5B-Instruct          400              8                0.020000          400             30                0.075000
 Qwen__Qwen2.5-Coder-32B-Instruct          400             31                0.077500          400             52                0.130000
  Qwen__Qwen2.5-Coder-7B-Instruct          400              7                0.017500          400             26                0.065000
        claude-haiku-4-5-20251001          400             35                0.087500          400             71                0.177500
                claude-sonnet-4-6          400             78                0.195000          400            107                0.267500
            gemini-3.1-flash-lite          400            106                0.265000          400            169                0.422500
           gemini-3.1-pro-preview          101             74                0.732673          116             82                0.706897
                 gpt-5-2025-08-07          400            279                0.697500          400            291                0.727500
            gpt-5-mini-2025-08-07          400            219                0.547500          400            236                0.590000

**Co-primary definition-matched row** (max |coverage_adjusted -
independently-recomputed def-b|: 1.11e-16, floating-point noise
only, `analysis/comparison_b_coverage_adjusted.csv`):

| | n_pairs | mean_a (ult) | mean_b (plt) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K (pre-registered primary) | 9 | 0.7987 | 0.8468 | 0.778 | 0.0391 |
| definition-matched / coverage-adjusted (co-primary) | 9 | 0.2502 | 0.3081 | 0.956 | 0.0078 |

**Does the conclusion change?** Effect direction is the SAME sign raw vs definition-matched. Magnitude/significance may still differ (above), but the qualitative read does not flip at n_models=9.

**Thin-cell audit** (n_defined<20 on either side flagged thin):

                      model_label  n_defined_ult  n_defined_plt
Qwen__Qwen2.5-Coder-1.5B-Instruct              8             30
 Qwen__Qwen2.5-Coder-32B-Instruct             31             52
  Qwen__Qwen2.5-Coder-7B-Instruct              7             26
        claude-haiku-4-5-20251001             35             71
                claude-sonnet-4-6             78            107
            gemini-3.1-flash-lite            106            169
           gemini-3.1-pro-preview             74             82
                 gpt-5-2025-08-07            279            291
            gpt-5-mini-2025-08-07            219            236

**Thin model(s) excluded from the 7-model thick-only
result below**: ['Qwen__Qwen2.5-Coder-1.5B-Instruct', 'Qwen__Qwen2.5-Coder-7B-Instruct'].

| | n_pairs | mean_a (ult) | mean_b (plt) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K, unfiltered (primary) | 9 | 0.7987 | 0.8468 | 0.778 | 0.0391 |
| raw Mut@K, thin cells (n_defined<20) excluded | 7 | 0.8411 | 0.8810 | 0.929 | 0.0312 |

**Does the 9-model result survive thin-cell filtering?**
NO in the sense that it shrinks to n_models=7 once thin cells are excluded. 2 of the original 9 model(s) were resting on a point estimate averaged over fewer than 20 baseline-passing problems.

## Directional-stability verdict across ALL conditionings tried (added 2026-08-03)

Comparison A's effect_r sign, across every conditioning computed in this
file: raw-unfiltered=-0.167, raw-thin-cell-filtered=-1.000,
definition-matched/coverage-adjusted=-0.833. All three share the same sign. A directional read is at least internally consistent across conditionings, though still not significant at any of the tiny n's involved (per the p-values above).

Comparison B's effect_r sign: raw-unfiltered=0.778,
raw-thin-cell-filtered=0.929,
definition-matched/coverage-adjusted=0.956. All three share the same sign. A directional read is at least internally consistent across conditionings.
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

      conditioning      test  p_value  p_value_holm  survives_holm_0.05
               raw H1 Test 1 0.742188      0.742188               False
               raw H1 Test 2 0.039062      0.078125               False
     thin_filtered H1 Test 1 0.031250      0.062500               False
     thin_filtered H1 Test 2 0.031250      0.062500               False
definition_matched H1 Test 1 0.039062      0.039062                True
definition_matched H1 Test 2 0.007812      0.015625                True

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
