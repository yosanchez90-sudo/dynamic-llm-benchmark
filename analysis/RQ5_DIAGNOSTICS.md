# RQ5 diagnostics (post-hoc, zero-compute)

Generated: 2026-07-27T23:47:52.158430+00:00
Git commit: e6f7413
Script: scripts/analyze_rq5_diagnostics.py

Pooled Dynamic Mut@K vs ULT remains the pre-registered PRIMARY result
(analysis/RQ5_ANALYSIS_PLAN.md, analysis/RQ5_PROVENANCE.md) -- everything
below is post-hoc diagnostic of that result's low rank agreement (Kendall
tau=0.143, n=7), not a replacement for it.

## 1. Tier-matched (L4-only) vs pooled vs per-tier

Dynamic-L4 is the CC>=8 band, matching ULT exactly (Comparison A's own
convention, src/Analysis/comparison.py). Pooling L1-L4 compares a
mixed-difficulty benchmark (L1/L2 near-ceiling for most models) against a
hard-only one -- this is the first candidate explanation for low pooled
rank agreement.

| Dynamic side | n | Pearson r | CI | Spearman ρ | CI | Kendall τ | CI | perm p (τ) |
|---|---|---|---|---|---|---|---|---|
| pooled | 7 | 0.904 | [-0.68, 0.99] | 0.143 | [-0.75, 1.00] | 0.143 | [-0.60, 1.00] | 0.7689 |
| L1 | 7 | -0.331 | [-0.96, 0.99] | 0.198 | [-0.75, 1.00] | 0.195 | [-0.65, 1.00] | 0.6571 |
| L2 | 7 | 0.885 | [-0.72, 0.99] | 0.250 | [-0.68, 1.00] | 0.238 | [-0.41, 1.00] | 0.5662 |
| L3 | 7 | 0.810 | [-0.84, 0.99] | 0.036 | [-0.88, 1.00] | 0.048 | [-0.76, 0.88] | 1.0000 |
| L4 | 5 | -0.873 | [-1.00, 1.00] | -0.500 | [-1.00, 1.00] | -0.200 | [-1.00, 1.00] | 0.8196 |

## 2. Discrimination audit: score spread per tier / pooled

| Dynamic side | n models | min | max | range | SD | mean adjacent-rank gap |
|---|---|---|---|---|---|---|
| pooled | 9 | 0.813 | 0.974 | 0.161 | 0.049 | 0.0201 |
| L1 | 9 | 0.983 | 1.000 | 0.017 | 0.007 | 0.0021 |
| L2 | 9 | 0.781 | 0.993 | 0.212 | 0.067 | 0.0266 |
| L3 | 9 | 0.722 | 0.967 | 0.244 | 0.078 | 0.0305 |
| L4 | 7 | 0.541 | 0.906 | 0.366 | 0.164 | 0.0610 |
| ULT | 7 | 0.407 | 0.901 | 0.494 | 0.174 | 0.0824 |

Pooled: 8/9 models within 0.05 of the max; 2 adjacent pair(s) within 0.001 of each other.
Highest-SD (best-discriminating) tier among the top models: **L4**.

## 3. Conditioning / survivorship audit

Mut@K is defined only where baseline_passed=True -- each model's pooled/per-tier
mean is therefore computed over a DIFFERENT subset of problems, not a shared
denominator. coverage_adjusted = Mut@K x baseline_pass_rate folds the
conditioning back in (a model that rarely produces a baseline-passing suite
gets penalised, not just averaged over the suites that happened to pass) --
this is NOT the same estimand as Mut@K itself, reported as a robustness check,
not a replacement metric.

| Model | tier | n_total | n_defined | baseline_pass_rate | Mut@K | coverage_adjusted |
|---|---|---|---|---|---|---|
| gpt-5-2025-08-07 | dyn_pooled | 294 | 263 | 0.895 | 0.963 | 0.8612 |
| gpt-5-2025-08-07 | dyn_L4 | 70 | 67 | 0.957 | 0.906 | 0.8676 |
| gpt-5-2025-08-07 | ult | 0 | 0 | nan | nan | nan |
| gpt-5-mini-2025-08-07 | dyn_pooled | 299 | 250 | 0.836 | 0.957 | 0.8003 |
| gpt-5-mini-2025-08-07 | dyn_L4 | 74 | 62 | 0.838 | 0.898 | 0.7521 |
| gpt-5-mini-2025-08-07 | ult | 0 | 0 | nan | nan | nan |
| claude-sonnet-4-6 | dyn_pooled | 1335 | 946 | 0.709 | 0.955 | 0.6770 |
| claude-sonnet-4-6 | dyn_L4 | 300 | 97 | 0.323 | 0.828 | 0.2677 |
| claude-sonnet-4-6 | ult | 400 | 78 | 0.195 | 0.756 | 0.1474 |
| claude-haiku-4-5-20251001 | dyn_pooled | 1343 | 663 | 0.494 | 0.955 | 0.4717 |
| claude-haiku-4-5-20251001 | dyn_L4 | 300 | 77 | 0.257 | 0.871 | 0.2235 |
| claude-haiku-4-5-20251001 | ult | 400 | 35 | 0.087 | 0.801 | 0.0701 |
| gemini-3.1-pro-preview | dyn_pooled | 545 | 510 | 0.936 | 0.974 | 0.9115 |
| gemini-3.1-pro-preview | dyn_L4 | 0 | 0 | nan | nan | nan |
| gemini-3.1-pro-preview | ult | 101 | 74 | 0.733 | 0.888 | 0.6509 |
| gemini-3.1-flash-lite | dyn_pooled | 1200 | 783 | 0.652 | 0.953 | 0.6221 |
| gemini-3.1-flash-lite | dyn_L4 | 300 | 145 | 0.483 | 0.881 | 0.4258 |
| gemini-3.1-flash-lite | ult | 400 | 106 | 0.265 | 0.821 | 0.2176 |
| Qwen 32B | dyn_pooled | 1500 | 436 | 0.291 | 0.955 | 0.2776 |
| Qwen 32B | dyn_L4 | 375 | 13 | 0.035 | 0.547 | 0.0189 |
| Qwen 32B | ult | 400 | 31 | 0.077 | 0.901 | 0.0698 |
| Qwen 7B | dyn_pooled | 1500 | 306 | 0.204 | 0.925 | 0.1887 |
| Qwen 7B | dyn_L4 | 375 | 1 | 0.003 | 0.541 | 0.0014 |
| Qwen 7B | ult | 400 | 7 | 0.018 | 0.894 | 0.0156 |
| Qwen 1.5B | dyn_pooled | 1500 | 78 | 0.052 | 0.813 | 0.0423 |
| Qwen 1.5B | dyn_L4 | 375 | 0 | 0.000 | nan | nan |
| Qwen 1.5B | ult | 400 | 8 | 0.020 | 0.407 | 0.0081 |

**Flagged explicitly**: Qwen-1.5B's pooled Dynamic Mut@K is computed over L1-L3 only (dyn_L4_n_defined=0 -- null throughout, see analysis/STABILITY.md), while every OTHER model's pooled score includes L4 rows. "Pooled" therefore silently means a different tier composition per model -- not an apples-to-apples average, a real methodological gap in the pre-registered primary metric as computed.

**Rank correlation on coverage-adjusted score (n=7)**: Pearson r=0.841, Spearman ρ=0.964, Kendall τ=0.905 (perm p=0.0034).

## 4. Attenuation correction

rho_disattenuated = rho_observed / sqrt(reliability_x * reliability_y) -- the
classical correction for attenuation due to unreliable measurement (Spearman,
1904), derived for Pearson r under classical test theory. Applying the same form
to Kendall tau here is an APPROXIMATION carried over by analogy, not a rigorously
derived rank-statistic correction -- treat the disattenuated tau as illustrative.

- Dynamic's own reliability (RQ4.1, N=4 mean pairwise Kendall tau across instantiations, computed live from CANONICAL_MODELS-filtered data on disk as of this run -- see the Generated/Git commit stamp above; this is NOT a frozen constant and will move as more instantiation data lands, same as `analysis/STABILITY.md` itself): **0.635**.
- ULT has **no repeat-measure reliability estimate in this project** -- it is evaluated once per model (K=1; the K=5 sensitivity sweep was the first item cut per PROJECT_BRIEF.md's gate cut-priority, and a static benchmark has no "instantiation" concept to repeat across the way Dynamic does). Stated plainly rather than assumed: the correction below uses Dynamic's reliability only (equivalent to assuming ULT's reliability=1, which UNDERESTIMATES the true disattenuated correlation if ULT is not, in fact, perfectly reliable).
- Observed pooled Kendall τ = 0.143 (n=7).
- Partial disattenuation (ULT reliability assumed = 1): τ_disattenuated = 0.143 / sqrt(0.635) = **0.179**.
- Even with this correction, the disattenuated tau stays far from the pre-registered validity-supporting zone -- the low observed correlation is NOT primarily an artifact of Dynamic's own (already-high, 0.675) reliability.
