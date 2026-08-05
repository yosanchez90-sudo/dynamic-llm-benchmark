# RQ5 diagnostics (post-hoc, zero-compute)

Generated: 2026-08-05T20:28:16.879914+00:00
Git commit: d07d7c8
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

**Same table, thin cells excluded** (n_defined<20 on either side for that tier -- a model whose own mean is a shaky point estimate shouldn't drive a cross-model correlation any more than it should drive a paired comparison, same threshold as Comparison A's thin-cell audit,
`analysis/COMPARISON_PROVENANCE.md`):

| Dynamic side | n | Kendall τ | CI | perm p (τ) | thin model(s) excluded |
|---|---|---|---|---|---|
| pooled | 5 | 0.000 | [-1.00, 1.00] | 1.0000 | ['Qwen 1.5B', 'Qwen 7B'] |
| L1 | 5 | 0.600 | [-0.50, 1.00] | 0.2377 | ['Qwen 1.5B', 'Qwen 7B'] |
| L2 | 5 | 0.200 | [-1.00, 1.00] | 0.8166 | ['Qwen 1.5B', 'Qwen 7B'] |
| L3 | 5 | -0.200 | [-1.00, 1.00] | 0.8199 | ['Qwen 1.5B', 'Qwen 7B'] |
| L4 | 3 | 1.000 | [1.00, 1.00] | 0.3312 | ['Qwen 32B', 'Qwen 7B'] |

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
| pooled | 0.0490 | 0.0093 | 5.26 |
| L1 | 0.0070 | 0.0026 | 2.73 |
| L2 | 0.0674 | 0.0145 | 4.64 |
| L3 | 0.0777 | 0.0665 | 1.17 |
| L4 | 0.1645 | 0.0183 | 8.97 |

**Pooled ratio = 5.26** (above 1).

**Largest run of adjacent models whose pooled Mut@K gap is smaller than either model's own between-instantiation SD (i.e. not reliably orderable against each other from this data alone)**: claude-haiku-4-5-20251001 > claude-sonnet-4-6 > Qwen 32B > gemini-3.1-flash-lite -- 4 models.
Their pooled spread is 0.002; their own individual SDs are 0.005, 0.004, 0.003, 0.004 -- the spread is smaller than every one of these models' own measurement noise. **Rewriting the tau=0.143 interpretation accordingly: at least part of the low rank agreement is not that Dynamic and ULT disagree about these models' quality, it's that pooled Mut@K lacks the resolving power to rank them AT ALL, on this data alone -- "the benchmarks disagree" and "this benchmark can't resolve close scores" are different claims, and the tau=0.143 headline conflates them.**

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

**Flagged explicitly (4 of 9 canonical models have a compromised L4 contribution to their pooled score, not just one)**:
- gemini-3.1-pro-preview: MISSING (never attempted -- data-collection gap, not a capability result)
- Qwen 32B: THIN (n_defined=13 < 20)
- Qwen 7B: THIN (n_defined=1 < 20)
- Qwen 1.5B: FLOOR (attempted, 0 passed baseline -- a genuine capability finding)
"Pooled" therefore silently means a different tier composition per model for 4/9 models -- not an apples-to-apples average, a real methodological gap in the pre-registered primary metric as computed.

**Top-ranked model check**: by pooled Mut@K, **gemini-3.1-pro-preview** ranks highest (0.974) -- its L4 status is MISSING (never attempted -- data-collection gap, not a capability result). By coverage-adjusted score, the SAME model (gemini-3.1-pro-preview) also ranks highest (0.9115). **The top-ranked model on both metrics never faced the hardest tier at all** -- its apparent lead may reflect having only been scored on easier problems, not genuine superiority over models that were tested on L4 and paid a real cost for it.

**Rank correlation on coverage-adjusted score (n=7)**: Pearson r=0.841, Spearman ρ=0.964, Kendall τ=0.905 (perm p=0.0034).

## 3b. Decomposing the coverage-adjusted agreement

coverage_adjusted = Mut@K x baseline_pass_rate is a PRODUCT of two signals --
how much of its tau=0.905 agreement is just baseline pass rate (can the model
produce a suite that PASSES against the original function, a stricter and
later gate than mere exec/collection -- src/eval/test_gen_scorer.py's
exec_ok and baseline_passed are distinct checks, not the same thing) vs
actual mutation-killing quality? Same n, same models (dropna on the
coverage-adjusted columns) for all three rows, so they're directly comparable.

| Component | n | Pearson r | Spearman ρ | Kendall τ | perm p (τ) |
|---|---|---|---|---|---|
| (a) baseline_pass_rate alone | 7 | 0.851 | 0.929 | 0.810 | 0.0115 |
| (b) conditioned Mut@K alone (= the pre-registered PRIMARY result) | 7 | 0.904 | 0.143 | 0.143 | 0.7689 |
| (c) coverage-adjusted product (Mut@K x baseline_pass_rate) | 7 | 0.841 | 0.964 | 0.905 | 0.0034 |

**How much of τ=0.905 is baseline pass rate vs mutation quality:** baseline_pass_rate ALONE already gives τ=0.810 -- nearly all of the coverage-adjusted agreement is explained by which models can produce a baseline-passing suite at all (a suite that PASSES against the real function -- not merely one that executes/collects, a weaker, earlier gate this project's scorer calls exec_ok), not by mutation-killing quality once that's controlled for -- conditioned Mut@K alone (row b, the actual pre-registered primary result) is τ=0.143, i.e. models that clear the baseline-pass bar do NOT then agree on which suites are the BETTER mutation killers. Read literally: the coverage-adjusted score's apparent validity is substantially a baseline-pass-rate-agreement result, not evidence that Mut@K itself (conditional on passing) is cross-benchmark valid.

## 3c. Reliability of the coverage-adjusted score

If the coverage-adjusted score is not just more cross-benchmark-valid but
also more RELIABLE (stabler across Dynamic instantiations) than raw Mut@K,
that's a stronger case for using it going forward, not just a post-hoc
rescue of one result. Recomputed on CANONICAL_MODELS-filtered Dynamic data,
N=4 scope (instantiations 1-4), same as sec 4's raw-Mut@K reliability.

| Score | N=4 mean pairwise Kendall tau |
|---|---|
| raw Mut@K | 0.635 |
| coverage-adjusted (Mut@K x baseline_pass_rate) | 1.000 |

**The coverage-adjusted score IS more reliable** across Dynamic instantiations (1.000 vs 0.635 raw) -- this makes it both more valid (sec 3b) and more reliable, a real argument for reporting it as a companion metric, not just a post-hoc robustness check. A perfect or near-perfect adjusted figure is worth a sanity check before taking as an unqualified win, though: verified this is not a degenerate small-n artifact (n_models=7 per pair, every pair individually significant at p<0.02, not just the mean) -- it is the SAME mechanism as sec 3b, not a separate finding. **Qualification: "n=7" is models, not a uniform amount of repeat measurement per model** -- instantiation counts vary: Qwen 1.5B=5, Qwen 32B=5, Qwen 7B=5, claude-haiku-4-5-20251001=5, claude-sonnet-4-6=5, gemini-3.1-flash-lite=4, gemini-3.1-pro-preview=4, gpt-5-2025-08-07=1, gpt-5-mini-2025-08-07=1. A model with only 4 scorable instantiations (or with some instantiations partially landed, see analysis/STABILITY.md) contributes a noisier per-model SD to this figure than one with a full 5, so treat the exact tau value as somewhat more uncertain than a clean n=7 label implies. baseline_pass_rate apparently varies enormously and consistently BETWEEN models (a 45x spread, sec 3 above) while staying comparatively stable WITHIN a model across instantiations, so a score dominated by that spread ranks models the same way every time almost by construction -- the same reason it's more cross-benchmark-valid (baseline pass rate dominates the signal) is why it's more reliable (baseline pass rate is itself the stable quantity). Neither result is suspect; both are the same underlying fact read two ways.

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
- Even with this correction, the disattenuated tau stays far from the pre-registered validity-supporting zone -- the low observed correlation is NOT primarily an artifact of Dynamic's own (already-high, 0.635) reliability.

**Matched disattenuation on the coverage-adjusted score** (sec 3b/3c) -- the pairing above uses the RAW Mut@K correlation with the RAW Mut@K reliability; this is the same correction applied to the ADJUSTED correlation with the ADJUSTED score's OWN reliability, since mixing a raw correlation with an adjusted reliability (or vice versa) would not be a matched pair:
- Coverage-adjusted reliability (N=4, sec 3c): **1.000**.
- Observed coverage-adjusted Kendall τ = 0.905 (n=7).
- Matched disattenuation: τ_disattenuated = 0.905 / sqrt(1.000) = **0.905**.
- Compare to the raw-matched 0.179 above -- the coverage-adjusted score's disattenuated agreement is still much higher, consistent with sec 3b's finding that most of its apparent validity is a baseline-pass-rate-agreement effect rather than a reliability artifact of either metric.

**Thin-cell-filtered primary correlation** (n_defined<20 on either side -- same threshold as secs 1/3b and Comparison A's audit):
- Unfiltered: τ=0.143 (n=7). Thin-cell-excluded: τ=0.000 (n=5, excluded: ['Qwen 1.5B', 'Qwen 7B']).
- **Mistral is unquotable on this pair once cross-family models are in scope** (ULT n_defined=1, analysis/RQ5_CROSS_FAMILY_PROVENANCE.md) -- not applicable to this canonical-only n=7 table (Mistral isn't one of the 9 canonical models), flagged here so the rule is visible in one place; see the cross-family provenance doc for its own thin-cell flags.
