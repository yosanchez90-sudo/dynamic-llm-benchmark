# RQ5 / H6 — interpretation

Hand-written, not auto-generated. `analysis/RQ5_PROVENANCE.md` (regenerated
by `scripts/analyze_rq5.py`) holds the raw tables this refers to.

## Part 1 (zero-compute): Dynamic(pooled) vs ULT — a genuine surprise, reported as found

**The primary (Spearman/Kendall, per the pre-registered plan) result is much
weaker than the score-level (Pearson) result suggests, and does not land in
the pre-registered validity-supporting zone.** n=7 (all models with both
Dynamic and ULT core_400 data; GPT-5/GPT-5-mini have no ULT data yet):

| Statistic | Value | 95% bootstrap CI | Permutation p |
|---|---|---|---|
| Pearson r | 0.904 | [-0.681, 0.993] | 0.082 |
| Spearman ρ | **0.143** | [-0.750, 1.000] | 0.779 |
| Kendall τ | **0.143** | [-0.600, 1.000] | 0.769 |

The Pearson number alone would read as a strong, encouraging correlation.
It isn't one — the CI includes strongly negative values, and the rank-based
statistics (which the analysis plan named primary precisely because a
linear read can be misleading with a skewed score distribution) are close
to zero. **Why the two disagree**: `analysis/figures/rq5_correlation.png`
shows the reason directly. Qwen 1.5B is a clear outlier on both axes (0.81
Dynamic-pooled, 0.41 ULT) — its distance from the other six models drives
the Pearson coefficient almost by itself. The other six models are bunched
tightly on Dynamic-pooled (0.925-0.974, a 5pp band) while spread widely on
ULT (0.756-0.901, a 15pp band), and **their rank order barely agrees between
benchmarks at all**: ULT ranks them Qwen32B > Qwen7B > Gemini-Pro-Preview >
Gemini-Flash-Lite > Haiku > Sonnet, while Dynamic-pooled ranks the same six
Gemini-Pro-Preview > Haiku > Sonnet > Qwen32B > Flash-Lite > Qwen7B — almost
the reverse for the two Qwen sizes.

**Reading this against the pre-registered frame**: the interpretation frame
recorded moderate-to-strong Spearman ρ as validity-supporting and near-zero
as validity-undermining. 0.143 sits in the latter zone, not the former —
but at n=7, this genuinely **cannot distinguish "no relationship" from
"not enough power to detect one"** (CI spans nearly the entire [-1, 1]
range). This is exactly the power limitation the plan pre-registered, not a
post-hoc excuse: report the number honestly, do not claim validity is
established, and do not claim it is refuted either.

## Diagnosis (post-hoc, `analysis/RQ5_DIAGNOSTICS.md` has the full tables)

Four candidate explanations for τ=0.143, checked in turn. **The pooled
result above remains the pre-registered primary and is not superseded by
anything below** — this is a diagnosis of why it came out low, not a
higher, more flattering number to report instead.

**(a) Difficulty composition.** Pooling L1-L4 compares a mixed-difficulty
benchmark against ULT's CC>=8-only band. Tier-matching (Dynamic-L4 only,
Comparison A's own convention) does not simply weaken the correlation — it
**flips its sign** (Pearson r=-0.873, Kendall τ=-0.200, n=5). At n=5 with a
CI spanning almost the full [-1,1] range this is not a confident finding on
its own, but it rules out the easy story ("pooling just adds noise that
tier-matching would fix") — the CC-matched comparison looks, if anything,
slightly worse than the pooled one, not better. The discrimination audit
explains part of why pooling is misleading regardless of sign: L1 has a
0.017 range across all 9 models (everyone at ceiling) while L4 has a 0.366
range and ULT a 0.494 range — pooling a near-zero-variance tier in with the
genuinely discriminating ones dilutes whatever signal the hard tiers carry,
in either direction.

**(b) Conditioning/survivorship — the largest single factor found.** Mut@K
is only defined where `baseline_passed=True`, so each model's mean is taken
over a different-sized, self-selected subset (pooled baseline_pass_rate
ranges from 0.02 for Qwen 1.5B to 0.90 for GPT-5 — a 45x spread in how much
of the benchmark even contributes to the average). Re-scoring with a
coverage-adjusted metric (Mut@K × baseline_pass_rate, which folds the
selection back in rather than conditioning it away) **recovers Kendall
τ=0.905, Spearman ρ=0.964 (permutation p=0.0034)** — a near-total reversal
from the raw pooled result. This is the strongest single piece of evidence
in this diagnosis: most of the apparent Dynamic/ULT disagreement is not
that the two benchmarks disagree about model *capability*, it's that Mut@K
as conventionally computed (conditional on baseline-pass) throws away the
part of the signal — how *often* a model clears the baseline gate at all —
that carries most of the cross-benchmark agreement. Mut@K and
coverage-adjusted-Mut@K are different estimands measuring different
things (respectively: "how good are the tests that already passed" vs "how
good is the model overall, including whether it clears the gate"); this
result says the latter is where the cross-benchmark agreement lives, not
that the former was computed wrong.

**(c) Reliability ceiling — a minor factor.** Disattenuating the observed
τ=0.143 by Dynamic's own RQ4.1 self-consistency (mean pairwise Kendall tau
0.675 across instantiations) gives τ_disattenuated≈0.174 — barely moved.
Dynamic's own noisiness is not why the cross-benchmark number is low.

**(d) Genuine construct difference — what's left over.** After (a) and (c)
are largely ruled out as the main drivers and (b) is shown to recover most
of the missing agreement, the residual "genuine distinct-capability" story
is smaller than the raw pooled result on its own would suggest. This
reframes the headline: **the pre-registered primary metric (pooled Mut@K)
genuinely does show weak rank agreement with ULT, and that finding stands,
unflattered** — but the diagnosis indicates this is substantially a property
of *how Mut@K conditions on baseline-pass*, not strong evidence that
Dynamic and ULT are measuring unrelated things. Both statements are true at
once and both belong in the write-up: the metric-as-specified underperforms
at cross-benchmark ranking, and the underlying capabilities it's built from
are not as disconnected as that number alone implies.

Also carried over from the per-tier check: Qwen 32B/7B score much higher on
ULT (0.90/0.89) than their Dynamic-L4 performance predicts (0.55/0.54,
already a documented stability outlier), while the API models show the
opposite asymmetry. n=5 is too small to treat this as confirmed, but it's
the kind of pattern a contamination story would produce (open-weight models
plausibly saw ULT-adjacent web content a leakage-free Dynamic instantiation
can't replicate) — recorded as a lead for RQ1 cross-referencing, not a
finding established here.

## Write-up stub — Discussion chapter (expand from here, not a final draft)

This project's construct validity for the Dynamic benchmark rests on two
complementary arguments. The **top-down** argument (§2 corpus design, §5
tier/mutation-operator specification) is definitional: the benchmark is
built directly from an explicit, pre-specified model of what test-generation
capability consists of (complexity-tiered problem structure, a fixed
mutation-operator catalogue, docstring-synonym variation) — validity is
designed in, not discovered after the fact. The **bottom-up** argument (this
RQ5/H6 analysis) is empirical: does the benchmark's ranking of models agree
with independent measures of related capability? The answer here is mixed
and instructive rather than simply confirmatory. Cross-provider rank
agreement with ULT (n=7, spanning distinct architectures and providers) is
close to zero on the pre-registered primary metric (Kendall τ=0.143), and
that finding is reported as-is, not smoothed over. A post-hoc diagnosis,
however, complicates a simple "distinct capabilities" reading: most of the
gap is attributable to how Mut@K conditions on baseline-pass rather than to
Dynamic and ULT disagreeing about model capability outright — a
coverage-adjusted re-scoring that folds the baseline-pass rate back in
recovers τ=0.905, and disattenuating for Dynamic's own measurement
reliability moves the observed number by only 0.03. So the honest
statement is two-sided: the metric as pre-registered and specified does
rank models inconsistently across benchmarks, which is a real limitation to
disclose, but the underlying capabilities are less disconnected than that
number alone implies. The one
clean, strong correlation available (Dynamic/ULT vs BigCodeBench, n=3) is
confined to a single model family's size sweep and is better read as
evidence that scale predicts everything within a family than as independent
proxy validation across the field. Taken together, the two halves of
construct validity point in a genuinely open direction rather than a
foregone conclusion: the top-down design is principled, and the bottom-up
diagnosis suggests the underlying capabilities are more related than the
headline cross-provider number implies once measurement conditioning is
accounted for — but that accounting is itself a post-hoc correction, not a
pre-registered result, and a genuinely cross-provider public-benchmark
comparison (contingent on models this recent — GPT-5, Claude Sonnet
4.6/Haiku 4.5, Gemini 3.1 — ever appearing on a BigCodeBench-style
leaderboard, which may simply never happen for snapshots this new) remains
the evidence that would actually settle which reading is closer to correct.

## Parts 2-3 result: Dynamic/ULT vs BigCodeBench, N=3, all-Qwen

The leaderboard harvest (`analysis/RQ5_LEADERBOARD_HARVEST.md`) found
published, snapshot-matched BigCodeBench numbers for all 3 Qwen sizes and
none of the six API models — so no self-run was needed, but the
public-benchmark correlation is **N=3, and all three points are the same
model family at three sizes** (Qwen 1.5B/7B/32B):

| Pair | n | Pearson r | Spearman ρ | Kendall τ | permutation p (τ) |
|---|---|---|---|---|---|
| Dynamic(pooled) ↔ BigCodeBench (Complete) | 3 | 0.981 | 1.000 | 1.000 | 0.331 |
| ULT ↔ BigCodeBench (Complete) | 3 | 0.927 | 1.000 | 1.000 | 0.331 |
| Dynamic(pooled) ↔ BigCodeBench (Hard) | 3 | 0.992 | 1.000 | 1.000 | 0.331 |
| ULT ↔ BigCodeBench (Hard) | 3 | 0.949 | 1.000 | 1.000 | 0.331 |

**Read this as size-scaling, not cross-benchmark validity, and say so
explicitly.** A perfect rank match across a 1.5B→7B→32B sweep within one
model family is close to the least surprising result available: bigger
Qwen-Coder checkpoints are better at essentially everything, so of course
they rank the same way on Dynamic, ULT, and BigCodeBench. This is NOT the
same kind of evidence as the n=7 Dynamic↔ULT result above, which spans
multiple providers/architectures and is the test that can actually fail
(and did show near-zero rank agreement). The permutation p-value confirms
this isn't statistically distinguishable from chance either (p=0.331 even
at "perfect" τ=1.0 — n=3 has only 6 possible orderings, so a perfect match
isn't rare enough to be significant). **Do not report the n=3 numbers as
"BigCodeBench validates this benchmark"** — report them as "consistent
with, but not independent evidence for, cross-benchmark validity," and
lead with the cross-provider n=7 Dynamic↔ULT result as the analysis that
actually stress-tests the claim.

## What this means going forward

The public-benchmark harvest/self-run (Parts 2-3) is not gated on this
result, but it does raise the stakes for getting a genuinely larger N: with
only 7 points, one outlier model can flip the whole read of "does this
benchmark validate against X" depending on which correlation statistic is
quoted. The same bootstrap/permutation reporting standard applies there.
