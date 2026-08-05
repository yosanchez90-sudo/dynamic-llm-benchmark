# RQ5 sanitizer sensitivity analysis (post-hoc, zero-compute)

Generated: 2026-08-05T20:33:30.608779+00:00
Git commit: d07d7c8
Script: scripts/analyze_rq5_sanitizer_sensitivity.py

src/eval/test_gen_scorer.py::sanitize_test_file strips a reimplementation of
the function-under-test and/or prepends a missing import before scoring --
recorded per-row in `notes`. This checks whether repairs are evenly
distributed across models and whether excluding repaired rows changes the
RQ5 primary/coverage-adjusted picture. Canonical models only, Dynamic pooled
+ ULT.

## Per-model repair fraction

| Model | dyn n_total | dyn n_repaired | dyn repair% | ult n_total | ult n_repaired | ult repair% |
|---|---|---|---|---|---|---|
| Qwen 1.5B | 1500 | 67 | 4.47% | 400 | 99 | 24.75% |
| Qwen 32B | 1500 | 0 | 0.00% | 400 | 6 | 1.50% |
| Qwen 7B | 1500 | 0 | 0.00% | 400 | 4 | 1.00% |
| claude-haiku-4-5-20251001 | 1343 | 0 | 0.00% | 400 | 46 | 11.50% |
| claude-sonnet-4-6 | 1335 | 0 | 0.00% | 400 | 41 | 10.25% |
| gemini-3.1-flash-lite | 1200 | 0 | 0.00% | 400 | 27 | 6.75% |
| gemini-3.1-pro-preview | 545 | 0 | 0.00% | 101 | 4 | 3.96% |
| gpt-5-2025-08-07 | 294 | 0 | 0.00% | 0 | 0 | nan% |
| gpt-5-mini-2025-08-07 | 299 | 0 | 0.00% | 0 | 0 | nan% |

Total repaired: 67/9516 Dynamic rows, 227/2501 ULT rows.

## Recomputed metrics with repaired rows excluded (dropped, not re-scored)

| Model | dyn Mut@K (as-scored -> excl.) | dyn bp_rate (as-scored -> excl.) | ult Mut@K (as-scored -> excl.) | ult bp_rate (as-scored -> excl.) |
|---|---|---|---|---|
| Qwen 1.5B | 0.813 -> 0.811 | 0.052 -> 0.044 | 0.407 -> 0.288 | 0.020 -> 0.020 |
| Qwen 32B | 0.955 -> 0.955 | 0.291 -> 0.291 | 0.901 -> 0.896 | 0.077 -> 0.071 |
| Qwen 7B | 0.925 -> 0.925 | 0.204 -> 0.204 | 0.894 -> 0.894 | 0.018 -> 0.018 |
| claude-haiku-4-5-20251001 | 0.955 -> 0.955 | 0.494 -> 0.494 | 0.801 -> 0.765 | 0.087 -> 0.076 |
| claude-sonnet-4-6 | 0.955 -> 0.955 | 0.709 -> 0.709 | 0.756 -> 0.740 | 0.195 -> 0.187 |
| gemini-3.1-flash-lite | 0.953 -> 0.953 | 0.652 -> 0.652 | 0.821 -> 0.817 | 0.265 -> 0.241 |
| gemini-3.1-pro-preview | 0.974 -> 0.974 | 0.936 -> 0.936 | 0.888 -> 0.887 | 0.733 -> 0.742 |
| gpt-5-2025-08-07 | 0.963 -> 0.963 | 0.895 -> 0.895 | nan -> nan | nan -> nan |
| gpt-5-mini-2025-08-07 | 0.957 -> 0.957 | 0.836 -> 0.836 | nan -> nan | nan -> nan |

## RQ5 primary correlation, with vs without repaired rows

| Metric | scope | n | Kendall τ | perm p |
|---|---|---|---|---|
| raw Mut@K | Dynamic<->ULT | 7 | 0.143 | 0.7689 |
| raw Mut@K, repaired rows excluded | Dynamic<->ULT | 7 | 0.143 | 0.7689 |
| coverage-adjusted | Dynamic<->ULT | 7 | 0.905 | 0.0034 |
| coverage-adjusted, repaired rows excluded | Dynamic<->ULT | 7 | 0.810 | 0.0103 |

## Do repairs differentially benefit weaker models?

Two ways to check this: (a) the direct distribution -- is repair need
concentrated in specific models rather than spread evenly, (b) a
correlation against baseline_pass_rate. (a) is the more trustworthy read
here since Dynamic's repair distribution is near-degenerate (see table
above) -- most models sit at exactly 0%, which makes a Kendall tau over
9 points essentially a 1-point-vs-8-ties comparison, not a smooth
9-point relationship.

**(a) Direct read**: 1 of 9 canonical models have ANY repaired rows on Dynamic -- repair need is concentrated almost entirely in **Qwen 1.5B** (4.47%, vs 0% for every other model), the smallest/weakest model in this project's own capability ordering. On ULT (where reimplementation is more common across the board -- real-world scraped functions, more naming variety) the same model has the highest rate there too (24.75%). **Yes, sanitization concentrates on and differentially helps the weakest model** -- this is directly visible in the distribution, not just inferred from a correlation coefficient.

**(b) Correlation check**: Kendall τ(repair_frac, baseline_pass_rate) = -0.471 (n=9, perm p=0.2223) -- direction is consistent with (a) (negative: more repairs where baseline_pass_rate is lower), but **not statistically significant at this n** (a near-degenerate 8-zeros-plus-1-outlier distribution is a weak basis for a correlation coefficient regardless of its point estimate) -- treat (a), the direct distribution, as the trustworthy evidence here, not this p-value.
