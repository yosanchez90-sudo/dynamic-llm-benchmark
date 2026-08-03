# Comparison A/B generation provenance

Generated: 2026-08-03T00:30:18.323749+00:00
Git commit: 8a5a6e8

Sources: data/results/dynamic/*.jsonl (tier=L4 only for Comparison A),
data/results/ult/*.jsonl, data/results/plt/*.jsonl.
CC bands: data/raw/ult_plt/subsample_manifest.json (tag=core_400).

## Comparison A (Dynamic-L4 vs ULT) — 5/9 models
Missing (no scorable data on one or both sides — NOT zero-filled, simply
absent from comparison_a_paired.csv): ['Qwen__Qwen2.5-Coder-1.5B-Instruct', 'gemini-3.1-pro-preview', 'gpt-5-2025-08-07', 'gpt-5-mini-2025-08-07']

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

**Coverage-adjusted robustness row** (Mut@K x baseline_pass_rate per side,
folds the conditioning back in -- NOT the same estimand as Mut@K itself,
`analysis/comparison_a_coverage_adjusted.csv` /
`analysis/comparison_a_coverage_adjusted_wilcoxon.csv`):

| | n_pairs | mean_a (dynamic_l4) | mean_b (ult) | effect_r | p |
|---|---|---|---|---|---|
| raw Mut@K (primary) | 5 | 0.7333 | 0.8346 | 0.200 | 0.8125 |
| coverage-adjusted (robustness) | 5 | 0.1875 | 0.1041 | -0.600 | 0.3125 |

**Does the conclusion change?** Effect direction FLIPS between raw and coverage-adjusted (sign of effect_r differs) -- treat Comparison A's direction as conditioning-sensitive, not robust.

## Comparison A thin-cell audit (added 2026-07-30)

A model's own paired Mut@K is a shaky point estimate when it's averaged
over very few baseline-passing problems -- n_defined<20 on
either side is flagged thin here, same threshold used in
`analysis/RQ5_DIAGNOSTICS.md`. Per-model n_defined for both sides:

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

## Cross-definition note (added 2026-07-30, see analysis/RQ5_CROSS_DEFINITION_AUDIT.md)

Every Mut@K number in this file uses this project's own EXCLUDE/conditional
definition (mean over baseline-passing rows only). The ULT/PLT paper's own
published mutation score is, by the project's reading of its stated formula
(N = total function count, not passing-only), an INCLUDE-AS-ZERO/
unconditional definition -- a different estimand, even for identical
functions. This does NOT affect the internal validity of Comparison A/B
(both arms use this project's own scorer, so the comparison is
self-consistent) -- it means these numbers should not be read as directly
comparable to the ULT/PLT paper's own reported ~40.21% average mutation
score. Full writeup: `analysis/RQ5_CROSS_DEFINITION_AUDIT.md`.

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
