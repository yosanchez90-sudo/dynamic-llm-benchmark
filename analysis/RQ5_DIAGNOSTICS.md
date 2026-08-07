# RQ5 diagnostics (post-hoc, zero-compute)

Generated: 2026-08-07T16:04:45.379766+00:00
Git commit: 28dd3c5
Script: scripts/analyze_rq5_diagnostics.py

Pooled Dynamic Mut@K vs ULT remains the pre-registered PRIMARY result
(analysis/RQ5_ANALYSIS_PLAN.md, analysis/RQ5_PROVENANCE.md) -- everything
below is post-hoc diagnostic of that result's low rank agreement (Kendall
tau=0.333, n=9), not a replacement for it.

## 1. Tier-matched (L4-only) vs pooled vs per-tier

Dynamic-L4 is the CC>=8 band, matching ULT exactly (Comparison A's own
convention, src/Analysis/comparison.py). Pooling L1-L4 compares a
mixed-difficulty benchmark (L1/L2 near-ceiling for most models) against a
hard-only one -- this is the first candidate explanation for low pooled
rank agreement.

| Dynamic side | n | Pearson r | CI | Spearman ρ | CI | Kendall τ | CI | perm p (τ) |
|---|---|---|---|---|---|---|---|---|
| pooled | 9 | 0.912 | [-0.48, 0.99] | 0.350 | [-0.45, 1.00] | 0.333 | [-0.25, 1.00] | 0.2540 |
| L1 | 9 | -0.383 | [-0.96, 0.78] | 0.126 | [-0.68, 0.83] | 0.085 | [-0.59, 0.66] | 0.8433 |
| L2 | 9 | 0.886 | [-0.56, 0.99] | 0.017 | [-0.75, 0.81] | 0.056 | [-0.56, 0.74] | 0.9201 |
| L3 | 9 | 0.814 | [-0.58, 0.99] | 0.100 | [-0.65, 0.85] | 0.111 | [-0.48, 0.75] | 0.7576 |
| L4 | 8 | -0.476 | [-0.89, 0.97] | -0.214 | [-0.74, 0.97] | 0.000 | [-0.57, 0.91] | 1.0000 |

**Same table, thin cells excluded** (n_defined<20 on either side for that tier -- a model whose own mean is a shaky point estimate shouldn't drive a cross-model correlation any more than it should drive a paired comparison, same threshold as Comparison A's thin-cell audit,
`analysis/COMPARISON_PROVENANCE.md`):

| Dynamic side | n | Kendall τ | CI | perm p (τ) | thin model(s) excluded |
|---|---|---|---|---|---|
| pooled | 7 | 0.429 | [-0.25, 1.00] | 0.2412 | ['Qwen 1.5B', 'Qwen 7B'] |
| L1 | 7 | 0.238 | [-0.56, 1.00] | 0.5644 | ['Qwen 1.5B', 'Qwen 7B'] |
| L2 | 7 | -0.048 | [-0.87, 0.88] | 1.0000 | ['Qwen 1.5B', 'Qwen 7B'] |
| L3 | 7 | 0.048 | [-0.73, 0.88] | 1.0000 | ['Qwen 1.5B', 'Qwen 7B'] |
| L4 | 6 | 0.733 | [-0.09, 1.00] | 0.0547 | ['Qwen 32B', 'Qwen 7B'] |

## 2. Discrimination audit: score spread per tier / pooled

| Dynamic side | n models | min | max | range | SD | mean adjacent-rank gap |
|---|---|---|---|---|---|---|
| pooled | 9 | 0.813 | 0.969 | 0.156 | 0.048 | 0.0194 |
| L1 | 9 | 0.983 | 1.000 | 0.017 | 0.007 | 0.0021 |
| L2 | 9 | 0.781 | 0.991 | 0.210 | 0.067 | 0.0263 |
| L3 | 9 | 0.722 | 0.961 | 0.239 | 0.078 | 0.0298 |
| L4 | 8 | 0.541 | 0.911 | 0.371 | 0.158 | 0.0529 |
| ULT | 9 | 0.407 | 0.901 | 0.494 | 0.155 | 0.0618 |

Pooled: 8/9 models within 0.05 of the max; 3 adjacent pair(s) within 0.001 of each other.
Highest-SD (best-discriminating) tier among the top models: **L4**.

## 2b. Noise-floor / resolving-power audit

The discrimination audit above (sec 2) shows the between-model SPREAD; on
its own that doesn't say whether pooled Mut@K can actually RESOLVE which
model ranks above which -- for that, the spread has to be compared against
each model's own between-instantiation noise (RQ4.1, `analysis/STABILITY.md`).
If two adjacent models' score gap is smaller than either model's own SD
across repeat instantiations, their relative rank is not distinguishable from
noise -- re-running the same model would plausibly reorder them on its own.
ULT has no repeat-instantiation concept (K=1, static benchmark), so this audit
is Dynamic-only.

| Dynamic side | between-model SD | mean within-model SD (n models w/ 2+ inst) | ratio (between/within) |
|---|---|---|---|
| pooled | 0.0484 | 0.0076 | 6.40 |
| L1 | 0.0071 | 0.0026 | 2.74 |
| L2 | 0.0672 | 0.0094 | 7.17 |
| L3 | 0.0779 | 0.0519 | 1.50 |
| L4 | 0.1581 | 0.0130 | 12.19 |

**Pooled ratio = 6.40** (above 1).

**Largest run of adjacent models whose pooled Mut@K gap is smaller than either model's own between-instantiation SD (i.e. not reliably orderable against each other from this data alone)**: gpt-5-2025-08-07 > gpt-5-mini-2025-08-07 > claude-haiku-4-5-20251001 > Qwen 32B > claude-sonnet-4-6 > gemini-3.1-flash-lite -- 6 models.
Their pooled spread is 0.007; their own individual SDs are 0.002, 0.001, 0.004, 0.003, 0.003, 0.004 -- the spread is smaller than every one of these models' own measurement noise. **Rewriting the tau=0.333 interpretation accordingly: at least part of the low rank agreement is not that Dynamic and ULT disagree about these models' quality, it's that pooled Mut@K lacks the resolving power to rank them AT ALL, on this data alone -- "the benchmarks disagree" and "this benchmark can't resolve close scores" are different claims, and the tau=0.333 headline conflates them.**

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
| gpt-5-2025-08-07 | dyn_pooled | 1500 | 1331 | 0.887 | 0.960 | 0.8519 |
| gpt-5-2025-08-07 | dyn_L4 | 375 | 361 | 0.963 | 0.911 | 0.8771 |
| gpt-5-2025-08-07 | ult | 400 | 279 | 0.698 | 0.869 | 0.6060 |
| gpt-5-mini-2025-08-07 | dyn_pooled | 1500 | 1257 | 0.838 | 0.958 | 0.8030 |
| gpt-5-mini-2025-08-07 | dyn_L4 | 375 | 306 | 0.816 | 0.896 | 0.7315 |
| gpt-5-mini-2025-08-07 | ult | 400 | 219 | 0.547 | 0.851 | 0.4660 |
| claude-sonnet-4-6 | dyn_pooled | 1500 | 1055 | 0.703 | 0.954 | 0.6711 |
| claude-sonnet-4-6 | dyn_L4 | 375 | 123 | 0.328 | 0.827 | 0.2714 |
| claude-sonnet-4-6 | ult | 400 | 78 | 0.195 | 0.756 | 0.1474 |
| claude-haiku-4-5-20251001 | dyn_pooled | 1500 | 753 | 0.502 | 0.955 | 0.4796 |
| claude-haiku-4-5-20251001 | dyn_L4 | 375 | 98 | 0.261 | 0.875 | 0.2285 |
| claude-haiku-4-5-20251001 | ult | 400 | 35 | 0.087 | 0.801 | 0.0701 |
| gemini-3.1-pro-preview | dyn_pooled | 583 | 548 | 0.940 | 0.969 | 0.9104 |
| gemini-3.1-pro-preview | dyn_L4 | 38 | 38 | 1.000 | 0.895 | 0.8953 |
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

**Flagged explicitly (3 of 9 canonical models have a compromised L4 contribution to their pooled score, not just one)**:
- Qwen 32B: THIN (n_defined=13 < 20)
- Qwen 7B: THIN (n_defined=1 < 20)
- Qwen 1.5B: FLOOR (attempted, 0 passed baseline -- a genuine capability finding)
"Pooled" therefore silently means a different tier composition per model for 3/9 models -- not an apples-to-apples average, a real methodological gap in the pre-registered primary metric as computed.

**Top-ranked model check**: by pooled Mut@K, **gemini-3.1-pro-preview** ranks highest (0.969) -- its L4 status is OK. By coverage-adjusted score, the SAME model (gemini-3.1-pro-preview) also ranks highest (0.9104). Neither top-ranked model has a MISSING L4 status, so this specific confound does not apply to the top rank, though thin coverage elsewhere in the table still affects the tier composition comparability noted above.

**Rank correlation on coverage-adjusted score (n_models=9)**: Pearson r=0.883, Spearman ρ=0.983, Kendall τ=0.944 (perm p=0.0002).

## 3b. Decomposing the coverage-adjusted agreement

coverage_adjusted = Mut@K x baseline_pass_rate is a PRODUCT of two signals --
how much of its tau=0.944 agreement is just baseline pass rate (can the
model produce a suite that PASSES against the original function, a stricter and
later gate than mere exec/collection -- src/eval/test_gen_scorer.py's
exec_ok and baseline_passed are distinct checks, not the same thing) vs
actual mutation-killing quality? Same n, same models (dropna on the
coverage-adjusted columns) for all three rows, so they're directly comparable.

| Component | n | Pearson r | Spearman ρ | Kendall τ | perm p (τ) |
|---|---|---|---|---|---|
| (a) baseline_pass_rate alone | 9 | 0.891 | 0.967 | 0.889 | 0.0004 |
| (b) conditioned Mut@K alone (= the pre-registered PRIMARY result) | 9 | 0.912 | 0.350 | 0.333 | 0.2540 |
| (c) coverage-adjusted product (Mut@K x baseline_pass_rate) | 9 | 0.883 | 0.983 | 0.944 | 0.0002 |

**How much of τ=0.944 is baseline pass rate vs mutation quality:** baseline_pass_rate ALONE already gives τ=0.889 -- nearly all of the coverage-adjusted agreement is explained by which models can produce a baseline-passing suite at all (a suite that PASSES against the real function -- not merely one that executes/collects, a weaker, earlier gate this project's scorer calls exec_ok), not by mutation-killing quality once that's controlled for -- conditioned Mut@K alone (row b, the actual pre-registered primary result) is τ=0.333, i.e. models that clear the baseline-pass bar do NOT then agree on which suites are the BETTER mutation killers. Read literally: the coverage-adjusted score's apparent validity is substantially a baseline-pass-rate-agreement result, not evidence that Mut@K itself (conditional on passing) is cross-benchmark valid.

## 3c. Reliability of the coverage-adjusted score

If the coverage-adjusted score is not just more cross-benchmark-valid but
also more RELIABLE (stabler across Dynamic instantiations) than raw Mut@K,
that's a stronger case for using it going forward, not just a post-hoc
rescue of one result. Recomputed on CANONICAL_MODELS-filtered Dynamic data,
N=4 scope (instantiations 1-4), same as sec 4's raw-Mut@K reliability.

| Score | N=4 mean pairwise Kendall tau |
|---|---|
| raw Mut@K | 0.667 |
| coverage-adjusted (Mut@K x baseline_pass_rate) | 1.000 |

**The coverage-adjusted score IS more reliable** across Dynamic instantiations (1.000 vs 0.667 raw) -- this makes it both more valid (sec 3b) and more reliable, a real argument for reporting it as a companion metric, not just a post-hoc robustness check. A perfect or near-perfect adjusted figure is worth a sanity check before taking as an unqualified win, though: verified this is not a degenerate small-n artifact (n_models=9 per pair, every pair individually significant at p=5.51e-06 (largest/least-significant p across pairs), not just the mean) -- it is the SAME mechanism as sec 3b, not a separate finding. **Qualification: "n=9" is models, not a uniform amount of repeat measurement per model** -- instantiation counts vary: Qwen 1.5B=5, Qwen 32B=5, Qwen 7B=5, claude-haiku-4-5-20251001=5, claude-sonnet-4-6=5, gemini-3.1-flash-lite=4, gemini-3.1-pro-preview=4, gpt-5-2025-08-07=5, gpt-5-mini-2025-08-07=5. A model with only 4 scorable instantiations (or with some instantiations partially landed, see analysis/STABILITY.md) contributes a noisier per-model SD to this figure than one with a full 5, so treat the exact tau value as somewhat more uncertain than a clean n=9 label implies. baseline_pass_rate apparently varies enormously and consistently BETWEEN models (a 45x spread, sec 3 above) while staying comparatively stable WITHIN a model across instantiations, so a score dominated by that spread ranks models the same way every time almost by construction -- the same reason it's more cross-benchmark-valid (baseline pass rate dominates the signal) is why it's more reliable (baseline pass rate is itself the stable quantity). Neither result is suspect; both are the same underlying fact read two ways.

## 4. Attenuation correction

rho_disattenuated = rho_observed / sqrt(reliability_x * reliability_y) -- the
classical correction for attenuation due to unreliable measurement (Spearman,
1904), derived for Pearson r under classical test theory. Applying the same form
to Kendall tau here is an APPROXIMATION carried over by analogy, not a rigorously
derived rank-statistic correction -- treat the disattenuated tau as illustrative.

- Dynamic's own reliability (RQ4.1, N=4 mean pairwise Kendall tau across instantiations, computed live from CANONICAL_MODELS-filtered data on disk as of this run -- see the Generated/Git commit stamp above; this is NOT a frozen constant and will move as more instantiation data lands, same as `analysis/STABILITY.md` itself): **0.667**.
- ULT has **no repeat-measure reliability estimate in this project** -- it is evaluated once per model (K=1; the K=5 sensitivity sweep was the first item cut per PROJECT_BRIEF.md's gate cut-priority, and a static benchmark has no "instantiation" concept to repeat across the way Dynamic does). Stated plainly rather than assumed: the correction below uses Dynamic's reliability only (equivalent to assuming ULT's reliability=1, which UNDERESTIMATES the true disattenuated correlation if ULT is not, in fact, perfectly reliable).
- Observed pooled Kendall τ = 0.333 (n_models=9).
- Partial disattenuation (ULT reliability assumed = 1): τ_disattenuated = 0.333 / sqrt(0.667) = **0.408**.
- Even with this correction, the disattenuated tau stays far from the pre-registered validity-supporting zone -- the low observed correlation is NOT primarily an artifact of Dynamic's own (already-high, 0.667) reliability.

**Matched disattenuation on the coverage-adjusted score** (sec 3b/3c) -- the pairing above uses the RAW Mut@K correlation with the RAW Mut@K reliability; this is the same correction applied to the ADJUSTED correlation with the ADJUSTED score's OWN reliability, since mixing a raw correlation with an adjusted reliability (or vice versa) would not be a matched pair:
- Coverage-adjusted reliability (N=4, sec 3c): **1.000**.
- Observed coverage-adjusted Kendall τ = 0.944 (n_models=9).
- Matched disattenuation: τ_disattenuated = 0.944 / sqrt(1.000) = **0.944**.
- Compare to the raw-matched 0.408 above -- the coverage-adjusted score's disattenuated agreement is still much higher, consistent with sec 3b's finding that most of its apparent validity is a baseline-pass-rate-agreement effect rather than a reliability artifact of either metric.

**Thin-cell-filtered primary correlation** (n_defined<20 on either side -- same threshold as secs 1/3b and Comparison A's audit):
- Unfiltered: τ=0.333 (n_models=9). Thin-cell-excluded: τ=0.429 (n_models=7, excluded: ['Qwen 1.5B', 'Qwen 7B']).
- **Mistral is unquotable on this pair once cross-family models are in scope** (ULT n_defined=1, analysis/RQ5_CROSS_FAMILY_PROVENANCE.md) -- not applicable to this canonical-only n=9 table (Mistral isn't one of the 9 canonical models), flagged here so the rule is visible in one place; see the cross-family provenance doc for its own thin-cell flags.
