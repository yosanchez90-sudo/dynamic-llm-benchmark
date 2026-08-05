# Comparison A/B generation provenance

Generated: 2026-08-05T20:27:18.410491+00:00
Git commit: d07d7c8

Sources: data/results/dynamic/*.jsonl (tier=L4 only for Comparison A),
data/results/ult/*.jsonl, data/results/plt/*.jsonl.
CC bands: data/raw/ult_plt/subsample_manifest.json (tag=core_400).

## Comparison A (Dynamic-L4 vs ULT) — 5/9 models
Missing (no scorable data on one or both sides — NOT zero-filled, simply
absent from comparison_a_paired.csv): ['Qwen__Qwen2.5-Coder-1.5B-Instruct', 'gemini-3.1-pro-preview', 'gpt-5-2025-08-07', 'gpt-5-mini-2025-08-07']

**Interpretation lives in `analysis/COMPARISON_A_INTERPRETATION.md`** — headline:
no directional claim survives at the current n under any Mut@K definition tried.

## Comparison B (ULT vs PLT) — 7/9 models
Missing: ['gpt-5-2025-08-07', 'gpt-5-mini-2025-08-07']

Pairing unit and CC-band methodology: see src/Analysis/comparison.py's
module docstring.

## Comparison A conditioning/survivorship audit (added 2026-07-28)

Comparison A pairs Mut@K, which is only defined where baseline_passed=True
(the same conditioning RQ5 diagnosed as the dominant factor behind its low
pooled Dynamic<->ULT rank agreement, `analysis/RQ5_DIAGNOSTICS.md` sec 3) --
each model's paired mean is computed over a DIFFERENT-sized, different
subset of problems, not a shared denominator. Full per-model n_total/
n_defined/baseline_pass_rate for both sides: `analysis/comparison_a_coverage.csv`.

                      model_label  n_total_dynamic_l4  n_defined_dynamic_l4  baseline_pass_rate_dynamic_l4  n_total_ult  n_defined_ult  baseline_pass_rate_ult
Qwen__Qwen2.5-Coder-1.5B-Instruct               375.0                   0.0                       0.000000        400.0            8.0                0.020000
 Qwen__Qwen2.5-Coder-32B-Instruct               375.0                  13.0                       0.034667        400.0           31.0                0.077500
  Qwen__Qwen2.5-Coder-7B-Instruct               375.0                   1.0                       0.002667        400.0            7.0                0.017500
        claude-haiku-4-5-20251001               300.0                  77.0                       0.256667        400.0           35.0                0.087500
                claude-sonnet-4-6               300.0                  97.0                       0.323333        400.0           78.0                0.195000
            gemini-3.1-flash-lite               300.0                 145.0                       0.483333        400.0          106.0                0.265000
           gemini-3.1-pro-preview                 NaN                   NaN                            NaN        101.0           74.0                0.732673
                 gpt-5-2025-08-07                70.0                  67.0                       0.957143          NaN            NaN                     NaN
            gpt-5-mini-2025-08-07                74.0                  62.0                       0.837838          NaN            NaN                     NaN

**Co-primary definition-matched row** (labelled "coverage-adjusted" in prior
versions of this file -- 2026-08-03: PROVEN algebraically and code-verified
identical to the true zero-filled/unconditional Mut@K, i.e. this project's
best-effort reading of the ULT/PLT paper's own Sec 3.4.3 PROSE formula. This
is a co-primary reported alongside, not a replacement for, the pre-registered
primary above -- see "Cross-definition note" below for why it is NOT simply
"the literature-matching score" without qualification.
Max |coverage_adjusted - independently-recomputed def-b| across all rows in
this table: 5.55e-17 (floating-point noise only --
`analysis/comparison_a_coverage_adjusted.csv`):

| | n_pairs | mean_a (dynamic_l4) | mean_b (ult) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K (pre-registered primary) | 5 | 0.7333 | 0.8346 | 0.200 | 0.8125 |
| definition-matched / coverage-adjusted (co-primary) | 5 | 0.1875 | 0.1041 | -0.600 | 0.3125 |

**Does the conclusion change?** Effect direction FLIPS between raw and definition-matched (sign of effect_r differs) -- treat Comparison A's direction as conditioning-sensitive, not robust.

## Comparison A thin-cell audit (added 2026-07-30, extended 2026-08-03)

A model's own paired Mut@K (pre-registered primary) is a shaky point
estimate when it's averaged over very few baseline-passing problems --
n_defined<20 on either side is flagged thin here, same
threshold used in `analysis/RQ5_DIAGNOSTICS.md`. Per-model n_defined for
both sides:

                     model_label  n_defined_dynamic_l4  n_defined_ult
Qwen__Qwen2.5-Coder-32B-Instruct                    13             31
 Qwen__Qwen2.5-Coder-7B-Instruct                     1              7
       claude-haiku-4-5-20251001                    77             35
               claude-sonnet-4-6                    97             78
           gemini-3.1-flash-lite                   145            106

**Thin model(s) excluded from the 3-model thick-only
result below**: ['Qwen__Qwen2.5-Coder-32B-Instruct', 'Qwen__Qwen2.5-Coder-7B-Instruct'].

| | n_pairs | mean_a (dynamic_l4) | mean_b (ult) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K, unfiltered (primary) | 5 | 0.7333 | 0.8346 | 0.200 | 0.8125 |
| raw Mut@K, thin cells (n_defined<20) excluded | 3 | 0.8598 | 0.7928 | -1.000 | 0.2500 |

**Does the 5-model result survive thin-cell filtering?**
NO in the sense that it shrinks to n=3 once thin cells are excluded -- 2 of the original 5 model(s) were resting on a point estimate averaged over fewer than 20 baseline-passing problems, not a stable per-model mean.

**Does thin-cell filtering even apply to the definition-matched/coverage-
adjusted co-primary?** The pre-registered primary's thinness comes from
n_defined (few baseline-passing rows -> shaky conditional mean); the
definition-matched score is a zero-filled mean over ALL n_total rows, so
ITS precision is governed by n_total, not n_defined -- a model with
n_defined=1 but n_total=375 (e.g. Qwen 7B, dynamic_l4) still gives a
well-estimated near-zero definition-matched score, not a shaky one. Checked
directly against the same THIN_N_DEFINED=20 threshold applied to n_total
instead: 0 models -- every model's n_total is >>20 on both sides (min n_total this table: dynamic_l4=70, ult=101), so no model is excluded from the co-primary row above on thinness grounds.

## Comparison B conditioning/survivorship + co-primary + thin-cell audit (added 2026-08-03)

Same conditioning applies to Comparison B (ULT vs PLT) as Comparison A --
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

**Co-primary definition-matched row** (max |coverage_adjusted -
independently-recomputed def-b|: 5.55e-17, floating-point noise
only -- `analysis/comparison_b_coverage_adjusted.csv`):

| | n_pairs | mean_a (ult) | mean_b (plt) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K (pre-registered primary) | 7 | 0.7811 | 0.8346 | 0.714 | 0.1094 |
| definition-matched / coverage-adjusted (co-primary) | 7 | 0.1685 | 0.2287 | 0.929 | 0.0312 |

**Does the conclusion change?** Effect direction is the SAME sign raw vs definition-matched; magnitude/significance may still differ (see table above), but the qualitative read does not flip at n=7.

**Thin-cell audit** (n_defined<20 on either side flagged thin):

                      model_label  n_defined_ult  n_defined_plt
Qwen__Qwen2.5-Coder-1.5B-Instruct              8             30
 Qwen__Qwen2.5-Coder-32B-Instruct             31             52
  Qwen__Qwen2.5-Coder-7B-Instruct              7             26
        claude-haiku-4-5-20251001             35             71
                claude-sonnet-4-6             78            107
            gemini-3.1-flash-lite            106            169
           gemini-3.1-pro-preview             74             82

**Thin model(s) excluded from the 5-model thick-only
result below**: ['Qwen__Qwen2.5-Coder-1.5B-Instruct', 'Qwen__Qwen2.5-Coder-7B-Instruct'].

| | n_pairs | mean_a (ult) | mean_b (plt) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K, unfiltered (primary) | 7 | 0.7811 | 0.8346 | 0.714 | 0.1094 |
| raw Mut@K, thin cells (n_defined<20) excluded | 5 | 0.8335 | 0.8775 | 0.867 | 0.1250 |

**Does the 7-model result survive thin-cell filtering?**
NO in the sense that it shrinks to n=5 once thin cells are excluded -- 2 of the original 7 model(s) were resting on a point estimate averaged over fewer than 20 baseline-passing problems.

## Directional-stability verdict across ALL conditionings tried (added 2026-08-03)

Comparison A's effect_r sign, across every conditioning computed in this
file: raw-unfiltered=0.200, raw-thin-cell-filtered=-1.000,
definition-matched/coverage-adjusted=-0.600. The sign FLIPS depending on which conditioning is applied -- raw/thin/definition-matched do not agree on which side (dynamic_l4 or ult) scores higher. This is the second flip on top of the raw-vs-coverage-adjusted flip already noted above (first flip found 2026-07-30). Given this, the honest conclusion is that Comparison A supports no directional claim at the current n (<=5 models, p>0.05 in every conditioning) -- not "the effect is X, but weak," but "this data cannot currently establish which of Dynamic-L4 or ULT scores a model higher, under any of the definitions tried."

Comparison B's effect_r sign: raw-unfiltered=0.714,
raw-thin-cell-filtered=0.867,
definition-matched/coverage-adjusted=0.929. All three share the same sign -- a directional read is at least internally consistent across conditionings. See
`analysis/RQ5_CROSS_DEFINITION_AUDIT.md` "Consequence audit" for the
narrative verdict on both comparisons together (this block reports the raw
numbers; that doc reports the reasoned conclusion).

## Cross-definition note (added 2026-07-30, revised 2026-08-03 -- see analysis/RQ5_CROSS_DEFINITION_AUDIT.md)

Every "raw Mut@K" number in this file uses this project's own EXCLUDE/
conditional definition (mean over baseline-passing rows only) -- the
pre-registered primary, never swapped out.

The "definition-matched / coverage-adjusted" co-primary row is this
project's best-effort reading of the ULT/PLT paper's Sec 3.4.3 PROSE
formula (Mut@k = sum(Mi)/N, N stated as "the total number of functions in
the benchmark," read as INCLUDE-AS-ZERO/unconditional). **This reading is
contradicted by the paper's own published code**: `Ray/main.py`'s
`mutation_statistic()`, the function actually invoked from that repo's CLI,
divides by `len(correct_tasks)` -- a baseline-pass-conditioned count, the
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
newest row by timestamp -- see that module's docstring for why. Comparison A
filters to tier=L4 only, and the ~559 duplicate rows found in the
2026-07-26 audit (scripts/audit_result_integrity.py) are entirely
L1/L2/L3-tier stale-retry rows -- none are L4, so Comparison A is unaffected
regardless of whether this table predates or postdates the loader fix.
Comparison B reads data/results/ult|plt/ directly, which the same audit
found have zero duplicate keys. Both tables here are correct independent of
generation order relative to the loader fix.
