# Ranking matrix — every metric, every benchmark, side by side

Generated: 2026-08-29T23:44:05.890587+00:00
Git commit: 9cdef55
Script: scripts/build_ranking_matrix.py

Supervisor reframe (2026-08-04): the ranking exercise is metric-agnostic.
This file reports model rankings under exec_rate, baseline_pass_rate,
conditional Mut@K, and coverage-adjusted Mut@K side by side, instead of
arguing which Mut@K definition is canonical. Full per-cell data:
`analysis/ranking_matrix_scores.csv`. Hand-written interpretation, if any,
belongs in a separate file. This one is auto-generated raw tables only.

## Table 1: per-metric scores and ranks

(a) Dynamic pooled, (b) Dynamic L4, (c) ULT core_400, (d) BigCodeBench
(published Complete-split Pass@1, not a per-row metric, so the SAME
BigCodeBench number/rank is shown under every metric block below. This is
noted, not an oversight). Canonical (9) and canonical+cross-family (13)
scopes shown separately.

### Scope: canonical (9 models)

**exec_rate**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.997 | 3 | 1500/1331 | 1.000 | 1 | 375/361 | 0.993 | 1 | 400/279 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.996 | 4 | 1500/1257 | 0.995 | 4 | 375/306 | 0.983 | 2 | 400/219 | n/a | n/a |
| claude-sonnet-4-6 | 0.805 | 8 | 1500/1055 | 0.381 | 9 | 375/123 | 0.453 | 8 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.942 | 6 | 1500/753 | 0.808 | 6 | 375/98 | 0.393 | 9 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.998 | 1 | 1200/1147 | 0.997 | 3 | 300/292 | 0.921 | 5 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.839 | 7 | 1200/783 | 0.800 | 7 | 300/145 | 0.833 | 6 | 400/106 | n/a | n/a |
| Qwen 32B | 0.997 | 2 | 1500/436 | 0.992 | 5 | 375/13 | 0.948 | 3 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.996 | 4 | 1500/306 | 1.000 | 1 | 375/1 | 0.935 | 4 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.795 | 9 | 1500/78 | 0.584 | 8 | 375/0 | 0.652 | 7 | 400/8 | 27.0 | 3 |

**baseline_pass_rate**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.887 | 2 | 1500/1331 | 0.963 | 2 | 375/361 | 0.698 | 2 | 400/279 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.838 | 3 | 1500/1257 | 0.816 | 3 | 375/306 | 0.547 | 3 | 400/219 | n/a | n/a |
| claude-sonnet-4-6 | 0.703 | 4 | 1500/1055 | 0.328 | 5 | 375/123 | 0.195 | 5 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.502 | 6 | 1500/753 | 0.261 | 6 | 375/98 | 0.087 | 6 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.956 | 1 | 1200/1147 | 0.973 | 1 | 300/292 | 0.733 | 1 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.652 | 5 | 1200/783 | 0.483 | 4 | 300/145 | 0.265 | 4 | 400/106 | n/a | n/a |
| Qwen 32B | 0.291 | 7 | 1500/436 | 0.035 | 7 | 375/13 | 0.077 | 7 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.204 | 8 | 1500/306 | 0.003 | 8 | 375/1 | 0.018 | 9 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.052 | 9 | 1500/78 | 0.000 | 9 | 375/0 | 0.020 | 8 | 400/8 | 27.0 | 3 |

**conditional Mut@K**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.960 | 1 | 1500/1331 | 0.911 | 2 | 375/361 | 0.869 | 4 | 400/279 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.958 | 3 | 1500/1257 | 0.896 | 3 | 375/306 | 0.851 | 5 | 400/219 | n/a | n/a |
| claude-sonnet-4-6 | 0.954 | 6 | 1500/1055 | 0.827 | 6 | 375/123 | 0.756 | 8 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.955 | 4 | 1500/753 | 0.875 | 5 | 375/98 | 0.801 | 7 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.960 | 2 | 1200/1147 | 0.919 | 1 | 300/292 | 0.888 | 3 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.953 | 7 | 1200/783 | 0.881 | 4 | 300/145 | 0.821 | 6 | 400/106 | n/a | n/a |
| Qwen 32B | 0.955 | 5 | 1500/436 | 0.547 | 7 | 375/13 | 0.901 | 1 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.925 | 8 | 1500/306 | 0.541 | 8 | 375/1 | 0.894 | 2 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.813 | 9 | 1500/78 | n/a | n/a | 375/0 | 0.407 | 9 | 400/8 | 27.0 | 3 |

**coverage-adjusted Mut@K**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.852 | 2 | 1500/1331 | 0.877 | 2 | 375/361 | 0.606 | 2 | 400/279 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.803 | 3 | 1500/1257 | 0.732 | 3 | 375/306 | 0.466 | 3 | 400/219 | n/a | n/a |
| claude-sonnet-4-6 | 0.671 | 4 | 1500/1055 | 0.271 | 5 | 375/123 | 0.147 | 5 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.480 | 6 | 1500/753 | 0.229 | 6 | 375/98 | 0.070 | 6 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.917 | 1 | 1200/1147 | 0.894 | 1 | 300/292 | 0.651 | 1 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.622 | 5 | 1200/783 | 0.426 | 4 | 300/145 | 0.218 | 4 | 400/106 | n/a | n/a |
| Qwen 32B | 0.278 | 7 | 1500/436 | 0.019 | 7 | 375/13 | 0.070 | 7 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.189 | 8 | 1500/306 | 0.001 | 8 | 375/1 | 0.016 | 8 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.042 | 9 | 1500/78 | n/a | n/a | 375/0 | 0.008 | 9 | 400/8 | 27.0 | 3 |

### Scope: canonical_plus_cross_family (13 models)

**exec_rate**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.997 | 3 | 1500/1331 | 1.000 | 1 | 375/361 | 0.993 | 1 | 400/279 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.996 | 4 | 1500/1257 | 0.995 | 4 | 375/306 | 0.983 | 2 | 400/219 | n/a | n/a |
| claude-sonnet-4-6 | 0.805 | 12 | 1500/1055 | 0.381 | 13 | 375/123 | 0.453 | 12 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.942 | 8 | 1500/753 | 0.808 | 9 | 375/98 | 0.393 | 13 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.998 | 1 | 1200/1147 | 0.997 | 3 | 300/292 | 0.921 | 6 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.839 | 11 | 1200/783 | 0.800 | 10 | 300/145 | 0.833 | 9 | 400/106 | n/a | n/a |
| Qwen 32B | 0.997 | 2 | 1500/436 | 0.992 | 5 | 375/13 | 0.948 | 4 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.996 | 4 | 1500/306 | 1.000 | 1 | 375/1 | 0.935 | 5 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.795 | 13 | 1500/78 | 0.584 | 12 | 375/0 | 0.652 | 11 | 400/8 | 27.0 | 6 |
| DeepSeek-6.7B | 0.983 | 6 | 300/46 | 0.973 | 6 | 75/0 | 0.963 | 3 | 400/25 | 35.5 | 4 |
| CodeLlama-13B | 0.860 | 10 | 300/44 | 0.907 | 8 | 75/1 | 0.873 | 8 | 400/8 | 28.5 | 5 |
| StarCoder2-15B | 0.923 | 9 | 300/75 | 0.800 | 10 | 75/0 | 0.887 | 7 | 400/56 | 37.6 | 3 |
| Mistral-7B | 0.967 | 7 | 300/5 | 0.947 | 7 | 75/0 | 0.823 | 10 | 400/1 | 19.5 | 7 |

**baseline_pass_rate**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.887 | 2 | 1500/1331 | 0.963 | 2 | 375/361 | 0.698 | 2 | 400/279 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.838 | 3 | 1500/1257 | 0.816 | 3 | 375/306 | 0.547 | 3 | 400/219 | n/a | n/a |
| claude-sonnet-4-6 | 0.703 | 4 | 1500/1055 | 0.328 | 5 | 375/123 | 0.195 | 5 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.502 | 6 | 1500/753 | 0.261 | 6 | 375/98 | 0.087 | 7 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.956 | 1 | 1200/1147 | 0.973 | 1 | 300/292 | 0.733 | 1 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.652 | 5 | 1200/783 | 0.483 | 4 | 300/145 | 0.265 | 4 | 400/106 | n/a | n/a |
| Qwen 32B | 0.291 | 7 | 1500/436 | 0.035 | 7 | 375/13 | 0.077 | 8 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.204 | 9 | 1500/306 | 0.003 | 9 | 375/1 | 0.018 | 12 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.052 | 12 | 1500/78 | 0.000 | 10 | 375/0 | 0.020 | 10 | 400/8 | 27.0 | 6 |
| DeepSeek-6.7B | 0.153 | 10 | 300/46 | 0.000 | 10 | 75/0 | 0.062 | 9 | 400/25 | 35.5 | 4 |
| CodeLlama-13B | 0.147 | 11 | 300/44 | 0.013 | 8 | 75/1 | 0.020 | 10 | 400/8 | 28.5 | 5 |
| StarCoder2-15B | 0.250 | 8 | 300/75 | 0.000 | 10 | 75/0 | 0.140 | 6 | 400/56 | 37.6 | 3 |
| Mistral-7B | 0.017 | 13 | 300/5 | 0.000 | 10 | 75/0 | 0.003 | 13 | 400/1 | 19.5 | 7 |

**conditional Mut@K**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.960 | 1 | 1500/1331 | 0.911 | 2 | 375/361 | 0.869 | 5 | 400/279 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.958 | 3 | 1500/1257 | 0.896 | 3 | 375/306 | 0.851 | 6 | 400/219 | n/a | n/a |
| claude-sonnet-4-6 | 0.954 | 7 | 1500/1055 | 0.827 | 6 | 375/123 | 0.756 | 9 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.955 | 4 | 1500/753 | 0.875 | 5 | 375/98 | 0.801 | 8 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.960 | 2 | 1200/1147 | 0.919 | 1 | 300/292 | 0.888 | 4 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.953 | 8 | 1200/783 | 0.881 | 4 | 300/145 | 0.821 | 7 | 400/106 | n/a | n/a |
| Qwen 32B | 0.955 | 5 | 1500/436 | 0.547 | 8 | 375/13 | 0.901 | 2 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.925 | 10 | 1500/306 | 0.541 | 9 | 375/1 | 0.894 | 3 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.813 | 13 | 1500/78 | n/a | n/a | 375/0 | 0.407 | 13 | 400/8 | 27.0 | 6 |
| DeepSeek-6.7B | 0.955 | 6 | 300/46 | n/a | n/a | 75/0 | 0.657 | 10 | 400/25 | 35.5 | 4 |
| CodeLlama-13B | 0.876 | 12 | 300/44 | 0.750 | 7 | 75/1 | 0.605 | 11 | 400/8 | 28.5 | 5 |
| StarCoder2-15B | 0.919 | 11 | 300/75 | n/a | n/a | 75/0 | 0.554 | 12 | 400/56 | 37.6 | 3 |
| Mistral-7B | 0.935 | 9 | 300/5 | n/a | n/a | 75/0 | 0.931 | 1 | 400/1 | 19.5 | 7 |

**coverage-adjusted Mut@K**
| Model | (a) Dyn pooled | rank | n/n_def | (b) Dyn L4 | rank | n/n_def | (c) ULT | rank | n/n_def | (d) BigCodeBench | rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | 0.852 | 2 | 1500/1331 | 0.877 | 2 | 375/361 | 0.606 | 2 | 400/279 | n/a | n/a |
| gpt-5-mini-2025-08-07 | 0.803 | 3 | 1500/1257 | 0.732 | 3 | 375/306 | 0.466 | 3 | 400/219 | n/a | n/a |
| claude-sonnet-4-6 | 0.671 | 4 | 1500/1055 | 0.271 | 5 | 375/123 | 0.147 | 5 | 400/78 | n/a | n/a |
| claude-haiku-4-5-20251001 | 0.480 | 6 | 1500/753 | 0.229 | 6 | 375/98 | 0.070 | 7 | 400/35 | n/a | n/a |
| gemini-3.1-pro-preview | 0.917 | 1 | 1200/1147 | 0.894 | 1 | 300/292 | 0.651 | 1 | 101/74 | n/a | n/a |
| gemini-3.1-flash-lite | 0.622 | 5 | 1200/783 | 0.426 | 4 | 300/145 | 0.218 | 4 | 400/106 | n/a | n/a |
| Qwen 32B | 0.278 | 7 | 1500/436 | 0.019 | 7 | 375/13 | 0.070 | 8 | 400/31 | 49.0 | 1 |
| Qwen 7B | 0.189 | 9 | 1500/306 | 0.001 | 9 | 375/1 | 0.016 | 10 | 400/7 | 40.4 | 2 |
| Qwen 1.5B | 0.042 | 12 | 1500/78 | n/a | n/a | 375/0 | 0.008 | 12 | 400/8 | 27.0 | 6 |
| DeepSeek-6.7B | 0.146 | 10 | 300/46 | n/a | n/a | 75/0 | 0.041 | 9 | 400/25 | 35.5 | 4 |
| CodeLlama-13B | 0.129 | 11 | 300/44 | 0.010 | 8 | 75/1 | 0.012 | 11 | 400/8 | 28.5 | 5 |
| StarCoder2-15B | 0.230 | 8 | 300/75 | n/a | n/a | 75/0 | 0.077 | 6 | 400/56 | 37.6 | 3 |
| Mistral-7B | 0.016 | 13 | 300/5 | n/a | n/a | 75/0 | 0.002 | 13 | 400/1 | 19.5 | 7 |

## Table 2: cross-benchmark rank agreement (ONE table, canonical scope, Holm-corrected within this 12-test family)

Kendall tau primary (permutation p, Holm-adjusted p); Spearman rho shown alongside. Dynamic side uses pooled (matching this project's established RQ5 primary convention).

| Metric | Dynamic<->ULT | Dynamic<->BigCodeBench | ULT<->BigCodeBench |
|---|---|---|---|
| exec_rate | τ=0.423 ρ=0.653 n_models=9 p=0.1441 (Holm p=1.0000) | τ=1.000 ρ=1.000 n_models=3 p=0.3312 (Holm p=1.0000) | τ=1.000 ρ=1.000 n_models=3 p=0.3312 (Holm p=1.0000) |
| baseline_pass_rate | τ=0.889 ρ=0.967 n_models=9 p=0.0004 (Holm p=0.0044) | τ=1.000 ρ=1.000 n_models=3 p=0.3312 (Holm p=1.0000) | τ=0.333 ρ=0.500 n_models=3 p=1.0000 (Holm p=1.0000) |
| conditional Mut@K | τ=0.278 ρ=0.333 n_models=9 p=0.3505 (Holm p=1.0000) | τ=1.000 ρ=1.000 n_models=3 p=0.3312 (Holm p=1.0000) | τ=1.000 ρ=1.000 n_models=3 p=0.3312 (Holm p=1.0000) |
| coverage-adjusted Mut@K | τ=0.944 ρ=0.983 n_models=9 p=0.0002 (Holm p=0.0024) | τ=1.000 ρ=1.000 n_models=3 p=0.3312 (Holm p=1.0000) | τ=1.000 ρ=1.000 n_models=3 p=0.3312 (Holm p=1.0000) |

Significant at raw p<0.05: 2/12. Significant at Holm-adjusted p<0.05: **2/12**.

## Table 3: noise floor (canonical scope, Dynamic pooled) — can this metric resolve model differences?

Between-model spread (max-min across 9 canonical models) vs the mean
within-model between-instantiation SD (from stability data). A metric
whose spread is smaller than or comparable to its own noise floor cannot
reliably rank closely-scored models, independent of cross-benchmark
agreement.

| Metric | Between-model spread | Mean within-model SD | Spread/SD ratio |
|---|---|---|---|
| exec_rate | 0.203 | 0.010 | 21.1 |
| baseline_pass_rate | 0.904 | 0.016 | 56.6 |
| conditional Mut@K | 0.147 | 0.007 | 20.7 |
| coverage-adjusted Mut@K | 0.875 | 0.015 | 59.2 |

## Table 4: reliability — mean pairwise Kendall tau across instantiations (canonical scope, Dynamic)

| Metric | N=4 mean pairwise tau | All-pairs mean pairwise tau |
|---|---|---|
| exec_rate | 0.704 | 0.690 |
| baseline_pass_rate | 1.000 | 1.000 |
| conditional Mut@K | 0.583 | 0.569 |
| coverage-adjusted Mut@K | 1.000 | 1.000 |
