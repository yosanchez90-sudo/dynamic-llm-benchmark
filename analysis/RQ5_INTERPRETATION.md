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

## Exploratory: per-tier breakdown (not primary, small n, flagged for cross-reference)

Pooling across all four Dynamic tiers likely dilutes the signal: L1/L2 are
near-ceiling for every model (little room to rank models against each
other), while L3/L4 spread models out much more. Per-tier Pearson r against
ULT: L1 = -0.331, L2 = 0.885, L3 = 0.810, **L4 = -0.873 (n=5 only — Qwen
1.5B and gemini-3.1-pro-preview have no defined L4 Mut@K)**.

The L4 result is worth a specific flag even though n=5 is too small to
trust as a standalone finding: Qwen 32B/7B score *much higher* on ULT
(0.90/0.89) than their own Dynamic-L4 performance would predict (0.55/0.54,
already documented as a stability outlier in `analysis/STABILITY.md`),
while the API models (Gemini Flash-Lite, Claude Haiku, Claude Sonnet) show
the opposite pattern — higher Dynamic-L4 than ULT. This is the kind of
asymmetry a contamination story would produce (open-weight Qwen models
plausibly saw ULT-adjacent web content during pretraining that a
leakage-free Dynamic instantiation can't replicate) but n=5 is far too
small to treat this as confirmed here — recorded as a lead for RQ1
cross-referencing and for interpretation once more models land, not as a
finding this analysis establishes on its own.

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
close to zero (Kendall τ=0.143), driven by a single outlier model rather
than a shared ordering among the rest — a result that, read against the
interpretation frame pre-registered before it was computed, sits closer to
"distinct capabilities" than "redundant with ULT," and raises a real
question about what pooled Dynamic Mut@K is measuring once tier-level
ceiling effects are accounted for (§ the per-tier breakdown above). The one
clean, strong correlation available (Dynamic/ULT vs BigCodeBench, n=3) is
confined to a single model family's size sweep and is better read as
evidence that scale predicts everything within a family than as independent
proxy validation across the field. Taken together, the two halves of
construct validity point in a genuinely open direction rather than a
foregone conclusion: the top-down design is principled, but the bottom-up
evidence available so far does not strongly corroborate it across providers,
and a larger, cross-provider public-benchmark comparison — contingent on
models this recent (GPT-5, Claude Sonnet 4.6/Haiku 4.5, Gemini 3.1) ever
appearing on a BigCodeBench-style leaderboard, which may simply never happen
for snapshots this new — would be needed to resolve which reading is
closer to correct.

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
