# Ranking matrix — every metric, every benchmark, side by side

Generated: 2026-08-05T13:02:04.341314+00:00
Git commit: 09a8b99
Script: scripts/build_ranking_matrix.py

Supervisor reframe (2026-08-04): the ranking exercise is metric-agnostic --
this file reports model rankings under exec_rate, baseline_pass_rate,
conditional Mut@K, and coverage-adjusted Mut@K side by side, rather than
arguing which Mut@K definition is canonical. Full per-cell data:
`analysis/ranking_matrix_scores.csv`. Hand-written interpretation, if any,
belongs in a separate file -- this one is auto-generated raw tables only.

## Table 1: per-metric scores and ranks

(a) Dynamic pooled, (b) Dynamic L4, (c) ULT core_400, (d) BigCodeBench
(published Complete-split Pass@1 -- not a per-row metric, so the SAME
BigCodeBench number/rank is shown under every metric block below; this is
noted, not an oversight). Canonical (9) and canonical+cross-family (13)
scopes shown separately.

### Scope: canonical (9 models)

**exec_rate**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 1.000 | 1 | 294/263 | 1.000 | 1 | 70/67 | n/a | n/a | 0/0 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.997 | 4 | 299/250 | 1.000 | 1 | 74/62 | n/a | n/a | 0/0 | n/a | n/a |
| claude-sonnet-4-6 | 0.814 | 8 | 1335/946 | 0.377 | 8 | 300/97 | 0.453 | 6 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.946 | 6 | 1343/663 | 0.807 | 5 | 300/77 | 0.393 | 7 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 1.000 | 1 | 545/510 | n/a | n/a | 0/0 | 0.921 | 3 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.839 | 7 | 1200/783 | 0.800 | 6 | 300/145 | 0.833 | 4 | 400/106 | n/a | n/a |
| Qwen 32B | 0.997 | 3 | 1500/436 | 0.992 | 4 | 375/13 | 0.948 | 1 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.996 | 5 | 1500/306 | 1.000 | 1 | 375/1 | 0.935 | 2 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.795 | 9 | 1500/78 | 0.584 | 7 | 375/0 | 0.652 | 5 | 400/8 | 27.0 | 3 |

**baseline_pass_rate**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.895 | 2 | 294/263 | 0.957 | 1 | 70/67 | n/a | n/a | 0/0 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.836 | 3 | 299/250 | 0.838 | 2 | 74/62 | n/a | n/a | 0/0 | n/a | n/a |
| claude-sonnet-4-6 | 0.709 | 4 | 1335/946 | 0.323 | 4 | 300/97 | 0.195 | 3 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.494 | 6 | 1343/663 | 0.257 | 5 | 300/77 | 0.087 | 4 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.936 | 1 | 545/510 | n/a | n/a | 0/0 | 0.733 | 1 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.652 | 5 | 1200/783 | 0.483 | 3 | 300/145 | 0.265 | 2 | 400/106 | n/a | n/a |
| Qwen 32B | 0.291 | 7 | 1500/436 | 0.035 | 6 | 375/13 | 0.077 | 5 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.204 | 8 | 1500/306 | 0.003 | 7 | 375/1 | 0.018 | 7 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.052 | 9 | 1500/78 | 0.000 | 8 | 375/0 | 0.020 | 6 | 400/8 | 27.0 | 3 |

**conditional Mut@K**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.963 | 2 | 294/263 | 0.906 | 1 | 70/67 | n/a | n/a | 0/0 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.957 | 3 | 299/250 | 0.898 | 2 | 74/62 | n/a | n/a | 0/0 | n/a | n/a |
| claude-sonnet-4-6 | 0.955 | 5 | 1335/946 | 0.828 | 5 | 300/97 | 0.756 | 6 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.955 | 4 | 1343/663 | 0.871 | 4 | 300/77 | 0.801 | 5 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.974 | 1 | 545/510 | n/a | n/a | 0/0 | 0.888 | 3 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.953 | 7 | 1200/783 | 0.881 | 3 | 300/145 | 0.821 | 4 | 400/106 | n/a | n/a |
| Qwen 32B | 0.955 | 6 | 1500/436 | 0.547 | 6 | 375/13 | 0.901 | 1 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.925 | 8 | 1500/306 | 0.541 | 7 | 375/1 | 0.894 | 2 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.813 | 9 | 1500/78 | n/a | n/a | 375/0 | 0.407 | 7 | 400/8 | 27.0 | 3 |

**coverage-adjusted Mut@K**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.861 | 2 | 294/263 | 0.868 | 1 | 70/67 | n/a | n/a | 0/0 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.800 | 3 | 299/250 | 0.752 | 2 | 74/62 | n/a | n/a | 0/0 | n/a | n/a |
| claude-sonnet-4-6 | 0.677 | 4 | 1335/946 | 0.268 | 4 | 300/97 | 0.147 | 3 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.472 | 6 | 1343/663 | 0.223 | 5 | 300/77 | 0.070 | 4 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.911 | 1 | 545/510 | n/a | n/a | 0/0 | 0.651 | 1 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.622 | 5 | 1200/783 | 0.426 | 3 | 300/145 | 0.218 | 2 | 400/106 | n/a | n/a |
| Qwen 32B | 0.278 | 7 | 1500/436 | 0.019 | 6 | 375/13 | 0.070 | 5 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.189 | 8 | 1500/306 | 0.001 | 7 | 375/1 | 0.016 | 6 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.042 | 9 | 1500/78 | n/a | n/a | 375/0 | 0.008 | 7 | 400/8 | 27.0 | 3 |

### Scope: canonical_plus_cross_family (13 models)

**exec_rate**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 1.000 | 1 | 294/263 | 1.000 | 1 | 70/67 | n/a | n/a | 0/0 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.997 | 4 | 299/250 | 1.000 | 1 | 74/62 | n/a | n/a | 0/0 | n/a | n/a |
| claude-sonnet-4-6 | 0.814 | 12 | 1335/946 | 0.377 | 12 | 300/97 | 0.453 | 10 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.946 | 8 | 1343/663 | 0.807 | 8 | 300/77 | 0.393 | 11 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 1.000 | 1 | 545/510 | n/a | n/a | 0/0 | 0.921 | 4 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.839 | 11 | 1200/783 | 0.800 | 9 | 300/145 | 0.833 | 7 | 400/106 | n/a | n/a |
| Qwen 32B | 0.997 | 3 | 1500/436 | 0.992 | 4 | 375/13 | 0.948 | 2 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.996 | 5 | 1500/306 | 1.000 | 1 | 375/1 | 0.935 | 3 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.795 | 13 | 1500/78 | 0.584 | 11 | 375/0 | 0.652 | 9 | 400/8 | 27.0 | 6 |
| DeepSeek-6.7B | 0.983 | 6 | 300/46 | 0.973 | 5 | 75/0 | 0.963 | 1 | 400/25 | 35.5 | 4 |
| CodeLlama-13B | 0.860 | 10 | 300/44 | 0.907 | 7 | 75/1 | 0.873 | 6 | 400/8 | 28.5 | 5 |
| StarCoder2-15B | 0.923 | 9 | 300/75 | 0.800 | 9 | 75/0 | 0.887 | 5 | 400/56 | 37.6 | 3 |
| Mistral-7B | 0.967 | 7 | 300/5 | 0.947 | 6 | 75/0 | 0.823 | 8 | 400/1 | 19.5 | 7 |

**baseline_pass_rate**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.895 | 2 | 294/263 | 0.957 | 1 | 70/67 | n/a | n/a | 0/0 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.836 | 3 | 299/250 | 0.838 | 2 | 74/62 | n/a | n/a | 0/0 | n/a | n/a |
| claude-sonnet-4-6 | 0.709 | 4 | 1335/946 | 0.323 | 4 | 300/97 | 0.195 | 3 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.494 | 6 | 1343/663 | 0.257 | 5 | 300/77 | 0.087 | 5 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.936 | 1 | 545/510 | n/a | n/a | 0/0 | 0.733 | 1 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.652 | 5 | 1200/783 | 0.483 | 3 | 300/145 | 0.265 | 2 | 400/106 | n/a | n/a |
| Qwen 32B | 0.291 | 7 | 1500/436 | 0.035 | 6 | 375/13 | 0.077 | 6 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.204 | 9 | 1500/306 | 0.003 | 8 | 375/1 | 0.018 | 10 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.052 | 12 | 1500/78 | 0.000 | 9 | 375/0 | 0.020 | 8 | 400/8 | 27.0 | 6 |
| DeepSeek-6.7B | 0.153 | 10 | 300/46 | 0.000 | 9 | 75/0 | 0.062 | 7 | 400/25 | 35.5 | 4 |
| CodeLlama-13B | 0.147 | 11 | 300/44 | 0.013 | 7 | 75/1 | 0.020 | 8 | 400/8 | 28.5 | 5 |
| StarCoder2-15B | 0.250 | 8 | 300/75 | 0.000 | 9 | 75/0 | 0.140 | 4 | 400/56 | 37.6 | 3 |
| Mistral-7B | 0.017 | 13 | 300/5 | 0.000 | 9 | 75/0 | 0.003 | 11 | 400/1 | 19.5 | 7 |

**conditional Mut@K**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.963 | 2 | 294/263 | 0.906 | 1 | 70/67 | n/a | n/a | 0/0 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.957 | 3 | 299/250 | 0.898 | 2 | 74/62 | n/a | n/a | 0/0 | n/a | n/a |
| claude-sonnet-4-6 | 0.955 | 5 | 1335/946 | 0.828 | 5 | 300/97 | 0.756 | 7 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.955 | 4 | 1343/663 | 0.871 | 4 | 300/77 | 0.801 | 6 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.974 | 1 | 545/510 | n/a | n/a | 0/0 | 0.888 | 4 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.953 | 8 | 1200/783 | 0.881 | 3 | 300/145 | 0.821 | 5 | 400/106 | n/a | n/a |
| Qwen 32B | 0.955 | 6 | 1500/436 | 0.547 | 7 | 375/13 | 0.901 | 2 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.925 | 10 | 1500/306 | 0.541 | 8 | 375/1 | 0.894 | 3 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.813 | 13 | 1500/78 | n/a | n/a | 375/0 | 0.407 | 11 | 400/8 | 27.0 | 6 |
| DeepSeek-6.7B | 0.955 | 7 | 300/46 | n/a | n/a | 75/0 | 0.657 | 8 | 400/25 | 35.5 | 4 |
| CodeLlama-13B | 0.876 | 12 | 300/44 | 0.750 | 6 | 75/1 | 0.605 | 9 | 400/8 | 28.5 | 5 |
| StarCoder2-15B | 0.919 | 11 | 300/75 | n/a | n/a | 75/0 | 0.554 | 10 | 400/56 | 37.6 | 3 |
| Mistral-7B | 0.935 | 9 | 300/5 | n/a | n/a | 75/0 | 0.931 | 1 | 400/1 | 19.5 | 7 |

**coverage-adjusted Mut@K**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.861 | 2 | 294/263 | 0.868 | 1 | 70/67 | n/a | n/a | 0/0 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.800 | 3 | 299/250 | 0.752 | 2 | 74/62 | n/a | n/a | 0/0 | n/a | n/a |
| claude-sonnet-4-6 | 0.677 | 4 | 1335/946 | 0.268 | 4 | 300/97 | 0.147 | 3 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.472 | 6 | 1343/663 | 0.223 | 5 | 300/77 | 0.070 | 5 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.911 | 1 | 545/510 | n/a | n/a | 0/0 | 0.651 | 1 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.622 | 5 | 1200/783 | 0.426 | 3 | 300/145 | 0.218 | 2 | 400/106 | n/a | n/a |
| Qwen 32B | 0.278 | 7 | 1500/436 | 0.019 | 6 | 375/13 | 0.070 | 6 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.189 | 9 | 1500/306 | 0.001 | 8 | 375/1 | 0.016 | 8 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.042 | 12 | 1500/78 | n/a | n/a | 375/0 | 0.008 | 10 | 400/8 | 27.0 | 6 |
| DeepSeek-6.7B | 0.146 | 10 | 300/46 | n/a | n/a | 75/0 | 0.041 | 7 | 400/25 | 35.5 | 4 |
| CodeLlama-13B | 0.129 | 11 | 300/44 | 0.010 | 7 | 75/1 | 0.012 | 9 | 400/8 | 28.5 | 5 |
| StarCoder2-15B | 0.230 | 8 | 300/75 | n/a | n/a | 75/0 | 0.077 | 4 | 400/56 | 37.6 | 3 |
| Mistral-7B | 0.016 | 13 | 300/5 | n/a | n/a | 75/0 | 0.002 | 11 | 400/1 | 19.5 | 7 |

## Table 2: cross-benchmark rank agreement (ONE table, canonical scope, Holm-corrected within this 12-test family)

Kendall tau primary (permutation p, Holm-adjusted p); Spearman rho shown alongside. Dynamic side uses pooled (matching this project's established RQ5 primary convention).

| Metric | Dynamic<->ULT | Dynamic<->BigCodeBench | ULT<->BigCodeBench |
|---|---|---|---|
| exec_rate | τ=0.429 ρ=0.643 n=7 p=0.2430 (Holm p=1.0000) | τ=1.000 ρ=1.000 n=3 p=0.3312 (Holm p=1.0000) | τ=1.000 ρ=1.000 n=3 p=0.3312 (Holm p=1.0000) |
| baseline_pass_rate | τ=0.810 ρ=0.929 n=7 p=0.0115 (Holm p=0.1265) | τ=1.000 ρ=1.000 n=3 p=0.3312 (Holm p=1.0000) | τ=0.333 ρ=0.500 n=3 p=1.0000 (Holm p=1.0000) |
| conditional Mut@K | τ=0.143 ρ=0.143 n=7 p=0.7689 (Holm p=1.0000) | τ=1.000 ρ=1.000 n=3 p=0.3312 (Holm p=1.0000) | τ=1.000 ρ=1.000 n=3 p=0.3312 (Holm p=1.0000) |
| coverage-adjusted Mut@K | τ=0.905 ρ=0.964 n=7 p=0.0034 (Holm p=0.0408) | τ=1.000 ρ=1.000 n=3 p=0.3312 (Holm p=1.0000) | τ=1.000 ρ=1.000 n=3 p=0.3312 (Holm p=1.0000) |

Significant at raw p<0.05: 2/12. Significant at Holm-adjusted p<0.05: **1/12**.

## Table 3: noise floor (canonical scope, Dynamic pooled) — can this metric resolve model differences?

Between-model spread (max-min across 9 canonical models) vs the mean
within-model between-instantiation SD (from stability data). A metric
whose spread is smaller than or comparable to its own noise floor cannot
reliably rank closely-scored models, independent of cross-benchmark
agreement.

| Metric | Between-model spread | Mean within-model SD | Spread/SD ratio |
|---|---|---|---|
| exec_rate | 0.205 | 0.020 | 10.4 |
| baseline_pass_rate | 0.884 | 0.021 | 41.2 |
| conditional Mut@K | 0.161 | 0.009 | 17.3 |
| coverage-adjusted Mut@K | 0.869 | 0.020 | 42.6 |

## Table 4: reliability — mean pairwise Kendall tau across instantiations (canonical scope, Dynamic)

| Metric | N=4 mean pairwise tau | All-pairs mean pairwise tau |
|---|---|---|
| exec_rate | 0.854 | 0.842 |
| baseline_pass_rate | 1.000 | 1.000 |
| conditional Mut@K | 0.635 | 0.661 |
| coverage-adjusted Mut@K | 1.000 | 1.000 |
