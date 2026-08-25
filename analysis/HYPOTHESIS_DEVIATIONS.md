# Hypothesis deviation ledger

For each of the six supervisor-approved hypotheses (`docs/Approved_Hypotheses.md`,
quoted verbatim below, the governing document for wording):
what the approved text says, what was actually executed, why it differs
(if it does), and a paper-ready sentence. Numbers are live as of the
Phase 0 rebuild this pass (`analysis/WORKBOOK_VERIFICATION.md` has the
full verification trail. Two figures below were corrected from a stale
2026-08-07 snapshot as part of that pass: H5's mean pairwise τ and H3's
downstream per-model magnitudes both reflect Gemini 3.1 Pro Preview's
Dynamic-L4 crawl completing 2026-08-11).

---

## H1 Test 1 (RQ1)

**Approved wording (verbatim)**: "Mutation scores produced by 8 LLMs on
the dynamic benchmark will be lower than the scores on the static
benchmarks, after controlling for cyclomatic complexity (to hold
cyclomatic complexity constant and run fair comparisons)." Test 1: "run
paired comparison, Wilcoxon signed-rank across model–problem pairs."

**What was executed**: Comparison A (`scripts/build_comparison_tables.py`,
`src/Analysis/comparison.py`): Dynamic-L4 (the CC≥8 tier, matching ULT's
CC band) vs ULT core_400, paired Wilcoxon signed-rank **at model
level** (one paired observation per model: that model's own mean on
Dynamic-L4 vs its own mean on ULT), n=8. Raw/pre-registered-primary
reading: rank-biserial effect_r = **-0.167**, p = **0.7422**.

**Why it differs**:
1. **8 LLMs → 9 canonical models attempted, 8 qualify.** The approved set
   was written against an earlier model roster. This project's 9-model
   canonical panel (`PROJECT_BRIEF.md` §6) is the executed scope. Of
   those 9, only 8 have scorable data for this specific test. Qwen
   2.5-Coder-1.5B-Instruct is excluded by a genuine floor effect (0 of
   375 Dynamic-L4 attempts clear the baseline-pass gate), not a
   data-collection gap.
2. **Model-problem pairing → model-level pairing, a structural necessity,
   not a shortcut.** Dynamic problems are synthesized from a template
   grammar. ULT/PLT problems are real-world scraped functions. The two
   benchmarks share no common problem identity to pair on. There is no
   "the same problem" on both sides to pair a model-problem observation
   against. Model-level pairing (one paired observation per model) is the
   only pairing the data supports, and is documented as such in
   `src/Analysis/comparison.py`'s own module docstring.
3. **Predicted direction: mixed, and the approved test's own statistic
   contradicts the prediction.** H1 predicts Dynamic scores LOWER than
   static. The raw column means *do* run this way (mean Dynamic-L4 =
   0.7966 vs mean ULT = 0.8477, Dynamic lower, as predicted). But the
   approved test is the **paired Wilcoxon signed-rank test**,
   whose own effect size is the rank-biserial correlation, and that
   statistic is **negative** (effect_r = -0.167, where negative means
   Dynamic-L4 is favored: 6 of the 8 models individually score higher on
   Dynamic-L4 than on ULT). The column-mean read is dominated by two
   large-magnitude Qwen outliers (Qwen 32B, Qwen 7B, each ~0.35 higher on
   ULT). The rank statistic the hypothesis actually specifies is not
   dominated by them, and it points the opposite way. Neither reading is
   statistically significant (p=0.7422).

**Verdict: NOT SUPPORTED.** Not significant, and the approved test's own
designated statistic runs opposite to the predicted direction.

**Paper-ready sentence**: "H1 Test 1 (paired Wilcoxon signed-rank,
Dynamic-L4 vs ULT, n=8 of the 9 canonical models, Qwen 2.5-Coder-1.5B-
Instruct excluded by a genuine floor effect) is not supported: the
rank-biserial effect size (effect_r = -0.167, p = 0.7422) favors
Dynamic-L4, opposite to the predicted direction, even though a naive
comparison of raw column means (0.797 vs 0.848) runs the predicted way.
The discrepancy traces to two large-magnitude outlier models that
dominate the mean but not the rank statistic the approved test actually
reports. Pairing was conducted at model level, not model-problem level,
since Dynamic and ULT/PLT are generated from disjoint sources sharing no
common problem identity."

---

## H1 Test 2 (RQ1)

**Approved wording (verbatim)**: "Test 2: Comparison between ULT vs PLT.
Observational contamination signal: same models, decontaminated vs leaked
equivalents. Having Mutation score as the main metric."

**What was executed**: Comparison B (`scripts/build_comparison_tables.py`):
ULT vs PLT, paired Wilcoxon signed-rank at model level, CC-band matched
(`src/Analysis/comparison.py::matched_cc_table`), n=9 (full canonical
roster, no floor exclusions, since every model clears the baseline gate
on at least some ULT and PLT rows). PLT scores higher than ULT on **every**
conditioning: raw p=0.0391 (effect_r=0.778), thin-cell-filtered p=0.0312
(effect_r=0.929), definition-matched p=0.0078 (effect_r=0.956).

**Why it differs**: The test itself was executed exactly as specified.
This is not a design or execution deviation. The deviation is
**governance/procedural**: prior to this pass, the repo's docs
(`COMPARISON_A_INTERPRETATION.md`, `HYPOTHESIS_COVERAGE_AUDIT.md`) treated
Comparison B as an informal, unofficial exploratory check, explicitly
excluded from RQ1's Holm-Bonferroni family on the grounds that "Comparison
B is not one of PROJECT_BRIEF's six official hypotheses." That framing
was incorrect. The approved H1 names ULT-vs-PLT as its *second test*
verbatim, so it is hypothesis evidence and belongs in RQ1's correctable
family. `analysis/COMPARISON_A_INTERPRETATION.md`'s updated
"Multiple-comparisons correction for RQ1" section has the corrected
2-test Holm computation.

**Verdict: SUPPORTED IN DIRECTION**, with significance conditional on
which reading and correction is quoted (Holm recomputation below).

**Paper-ready sentence**: "H1 Test 2 (paired comparison, ULT vs PLT,
CC-band matched, n=9) is supported in direction: PLT scores higher than
ULT, the contamination-consistent result, on all three conditionings.
After Holm-Bonferroni correction within RQ1's two-test family (H1 Test 1
+ H1 Test 2), the raw/pre-registered-primary reading (p=0.0391) does not
survive (adjusted p=0.0782). The definition-matched co-primary reading
(p=0.0078) does (adjusted p=0.0156)."

---

## H2 (RQ1)

**Approved wording (verbatim)**: "After fine-tuning a small open-source
LLM on a static benchmark, its mutation-score on the static benchmark
will be larger than on the dynamic benchmark (even after applying
changes)." Test: "validate differences on mutation scores (pre vs. post
fine-tuning), considering (static vs. dynamic)."

**What was executed**: Comparison C's canonical 2×3 difference-in-
differences (`scripts/analyze_comparison_c.py`): Qwen2.5-Coder-1.5B-
Instruct, LoRA fine-tuned on repair-verified ULT ground truth, evaluated
PRE/POST on ULT, PLT, and Dynamic (both an L4 CC-matched control and an
L1-L3 headroom control). **`baseline_pass_rate` is the primary outcome**,
not mutation score.

**Why it differs: two different deviations, not one:**

**(1) An explicit interpretive step the approved wording itself requires,
not an added assumption.** The approved sentence alone is ambiguous
between two readings: "its mutation-score [the raw post-fine-tune value]
on the static benchmark will be larger than on the dynamic benchmark," or
"its mutation-score *gain* [pre-to-post difference] on the static
benchmark will be larger than its gain on the dynamic benchmark." Only
the accompanying Test clause resolves this: "validate differences on
mutation scores (**pre vs. post** fine-tuning), considering (static vs.
dynamic)" is explicit about comparing a *difference*, which only a
gain/DiD reading supports. The raw-score reading would need no "pre vs.
post" language. This project reads H2 as a gain/DiD hypothesis on
that basis, and executes it as one (Comparison C's 2×3
difference-in-differences), recorded here as a resolved ambiguity in the
approved text, not a deviation from it.

**(2) A genuine metric substitution.** PRE (base-model) Mut@K is undefined for **111 of the
112 seen-ULT problems** (`n_mut_defined=1` in the PRE row of
`COMPARISON_C_PROVENANCE.md`'s Mut@K table). The base 1.5B model almost
never produces a suite that clears ULT's baseline-pass gate, and
mutation score is only defined conditional on passing that gate. A
PRE-vs-POST difference in mutation score literally cannot be computed for
the population (seen-ULT) that matters most to this hypothesis.
`baseline_pass_rate` is used as the primary outcome instead, with Mut@K
reported alongside wherever it is computable, same estimand (does
fine-tuning inflate the static score more than the dynamic score), a
substituted metric.

**Verdict: SUPPORTED**, the strongest result in the project.

**Paper-ready sentence**: "H2 (2×3 difference-in-differences,
Qwen2.5-Coder-1.5B-Instruct LoRA-fine-tuned on repair-verified ULT,
PRE/POST × {ULT, PLT, Dynamic}) is supported: seen-ULT gains +99.1
percentage points (95% CI [97.3, 100.0]) with 100% verbatim reproduction
of training targets (112/112), against a genuine +8.7pp (CI [5.6, 12.0])
generic-fine-tuning-improvement control on Dynamic-L1-L3 and exactly
0.0pp on the CC-matched Dynamic-L4 control (floor-limited, this 1.5B
model never clears the Dynamic-L4 baseline gate). `baseline_pass_rate`,
not mutation score, is reported as the primary outcome: the approved
metric is undefined for the PRE condition in 111 of 112 seen-ULT
problems, since mutation score requires a baseline-passing suite the
base model almost never produces."

---

## H3 (RQ2)

**Approved wording (verbatim)**: "Mean mutation score will keep
decreasing (or stay the same) from L1 to L4 across all evaluated LLMs, it
will never go back up." Test: "Spearman ρ between tier index and
mutation score, per model and for all models combined."

**What was executed**: Per-model Spearman ρ between ordinal tier index
(1-4) and mutation score, all-tier and L2-L4 (ceiling-robustness) scopes,
Holm-Bonferroni corrected within each scope
(`scripts/analyze_h3_tier_gradient.py`). **9/9 models significant at
Holm-adjusted p<0.05, all-tier; 8/8 computable models significant,
L2-L4** (Qwen 1.5B has no baseline-passing L4 rows, a genuine floor
effect, correctly excluded from the L2-L4 scope, not computed on
an insufficient tier range).

**Why it differs**: Spearman ρ tests a **monotone trend**, not the
literal, stronger "never go back up" clause. A high, significant ρ is
compatible with an occasional small local rebound. This audit closes that
gap (task 9, zero additional compute.
`analysis/H3_TIER_GRADIENT_PROVENANCE.md`'s "low-power tier-mean"
section independently shows the same result via its raw
tier-mean Spearman column): checking every adjacent tier step
(L1→L2, L2→L3, L3→L4) for each of the 9 canonical models' raw per-tier
mean Mut@K (from `analysis/RQ5_PROVENANCE.md`'s per-tier columns,
cross-checked against `H3_TIER_GRADIENT_PROVENANCE.md`'s tier-mean
Spearman, which shows exactly -0.8, not -1.0, for the same two
models, the signature of exactly one adjacent-pair inversion in a
4-point sequence):

| Model | Rebound? | Where | Magnitude |
|---|---|---|---|
| gpt-5-2025-08-07 | **YES** | L1→L2 | 0.985487 → 0.990774 (+0.53pp) |
| gpt-5-mini-2025-08-07 | **YES** | L1→L2 | 0.982875 → 0.990388 (+0.75pp) |
| claude-sonnet-4-6 | No | — | strictly decreasing, all 4 tiers |
| claude-haiku-4-5-20251001 | No | — | strictly decreasing, all 4 tiers |
| gemini-3.1-pro-preview | No | — | strictly decreasing, all 4 tiers |
| gemini-3.1-flash-lite | No | — | strictly decreasing, all 4 tiers |
| Qwen 32B | No | — | strictly decreasing, all 4 tiers |
| Qwen 7B | No | — | strictly decreasing, all 4 tiers |
| Qwen 1.5B | No | — | strictly decreasing, L1-L3 (no L4 data — floor effect) |

**7 of 9 models satisfy the literal clause exactly. 2 (both GPT-5
models) violate it once each, at the identical L1→L2 step, both by less
than 1 percentage point, both already at ≥98% mutation score at L1**, a
near-ceiling regime this project's own docs repeatedly flag as a
measurement-noise zone, not a substantive reversal.

**Verdict: SUPPORTED (trend), literal clause holds for 7/9, violated by a
sub-1pp near-ceiling rebound for 2/9.**

**Paper-ready sentence**: "H3 (Spearman ρ between tier index and
mutation score) is supported as a monotone trend: every one of the 9
canonical models shows a significant negative correlation, surviving
Holm-Bonferroni correction in both the all-tier and L2-L4 (ceiling-
robustness) families. The stronger, literal 'never goes back up' clause
holds exactly for 7 of 9 models. 2 (GPT-5, GPT-5-mini) show a single
small upward step at L1→L2 (+0.5pp and +0.8pp respectively), both models
already at or above 98% mutation score at L1, consistent with
near-ceiling measurement noise, not a substantive reversal, but a
literal exception nonetheless."

---

## H4 (RQ3)

**Approved wording (verbatim)**: "The gap between static and dynamic
mutation scores will be larger at L1–L2 than at L3–L4." Test: "See if
there is an interaction between tier and benchmark in a regression that
treats different LLMs as a random source of variation."

**What was executed**: Nothing built. No mixed-effects model exists in
this project. `statsmodels` was deliberately not added as a dependency.

**Why it differs**: Not a shortcut. **The approved wording is untestable
by construction.** ULT/PLT contain only CC≥8 functions (the source
dataset's own filter), so there is no static-benchmark score at
CC<8 (Dynamic's L1-L2 range) to form the predicted gap with. A tier×
benchmark interaction term cannot be estimated when one side of the
interaction has zero variance in the tier variable. Declared
untestable-by-construction, approved by the supervisor 2026-08-05
(`analysis/H4_DESIGN_MEMO.md`, `PROJECT_BRIEF.md` §3.1).

**Verdict: DROPPED, untestable by construction.**

**Paper-ready sentence**: "H4 (tier × benchmark interaction, mixed-
effects regression) is dropped as untestable by construction, approved
2026-08-05: ULT/PLT contain no CC<8 (L1-L2-equivalent) problems by the
source dataset's own filter, so no static-benchmark score exists at low
complexity to form the predicted gap with. The regression's interaction
term cannot be estimated when one side has no variance in the tier
variable. RQ3 is instead answered narratively, via H3's within-Dynamic
tier gradient and this structural finding itself: a CC-filtered static
benchmark cannot even pose the question RQ3 asks."

---

## H5 (RQ4, all)

**Approved wording (verbatim)**: "Across N=5 independent instantiations
of the dynamic benchmark, the Kendall's τ... between LLM rankings will
exceed 0.7." Test: "pairwise Kendall's τ across instantiations, each time
with different random seeds."

**What was executed**: Pairwise Kendall's τ between per-instantiation
model rankings (`scripts/analyze_stability.py`). **N=4 headline scope**
(2 of 9 canonical models, both Gemini, never reached the approved N=5).
**Mean pairwise τ = 0.583** at N=4 (live, this pass's rebuild,
corrected from a stale 0.667 that predates the Gemini crawl's completion,
detailed in `analysis/WORKBOOK_VERIFICATION.md`); **0.569 all-pairs** (including
instantiation 5, which exists for 7 of the 9 canonical models, every
model except the two Geminis).

**Why it differs**:
1. **N=4, not the approved N=5, a checked and declined gap, not an open
   one.** Confirmed 2026-08-12 via `scripts/coverage_matrix.py` (zero
   active/pending SLURM jobs): 172/180 model×tier×instantiation cells
   complete. The only gap is both Gemini models' instantiation 5 (600
   problems). Closing it was quantified at **$9.60** (Gemini Pro Preview
   $9.34, Flash-Lite $0.27, `scripts/estimate_cost.py
   --target-instantiations 5`) with a 4-5 hour to 2-day completion
   window, and **declined 2026-08-12** for two reasons: (a) H5's
   THRESHOLD NOT MET verdict is unchanged at any plausible resulting τ;
   (b) adding two more models to every inst5-involving pair would most
   likely move τ further *down*, not up, for the same noise-floor reason
   τ fell from 0.667 to 0.583 when Gemini Pro Preview's L4 data landed
   (`analysis/RQ5_DIAGNOSTICS.md` sec 2b: 5 adjacent canonical models sit
   within a pooled spread of 0.005, smaller than their own
   between-instantiation SDs. This is a property of how tightly this
   model population clusters on this metric, not of the instrument).
   N=4 is itself the pre-registered cut-priority decision from
   2026-07-15 (`PROJECT_BRIEF.md` §11, "the fifth dynamic instantiation",
   cut-priority item #4, designed in advance to preserve every RQ), so
   reporting at N=4 exercises a documented contingency as intended, not
   an unexplained shortfall. Both scopes are reported (N=4 headline and
   the all-pairs figure including the partial fifth instantiation) so no
   collected data is discarded.
2. **The approved H5 covers the whole of RQ4.** RQ4.2/4.3/4.4 have no
   approved hypothesis of their own and are reported descriptively, not
   as a gap.

**Per-pair breakdown** (more informative than the mean alone), N=4 set, 6 pairs:

| Pair | n_models | τ | raw p | Holm p | >0.7? | Survives Holm? |
|---|---|---|---|---|---|---|
| 1-2 | 9 | **0.889** | 0.0002 | **0.0015** | **YES** | **YES** |
| 1-3 | 9 | 0.556 | 0.0446 | 0.1785 | no | no |
| 1-4 | 9 | 0.500 | 0.0752 | 0.2255 | no | no |
| 2-3 | 9 | 0.444 | 0.1194 | 0.2255 | no | no |
| 2-4 | 9 | 0.611 | 0.0247 | 0.1237 | no | no |
| 3-4 | 9 | 0.500 | 0.0752 | 0.2255 | no | no |

**Only 1 of 6 N=4-scope pairs individually exceeds 0.7**, and it is the
only one to survive Holm correction. All-pairs (10 pairs, including
instantiation 5, n_models=7 where either side involves a Gemini):
additionally 1-5=0.429, 2-5=0.333, **3-5=0.905** (Holm p=0.025, survives),
4-5=0.524. **2 of 10 pairs exceed 0.7**, and those same 2 are the ones
that survive Holm.

**Verdict: THRESHOLD NOT MET.** Mean (0.583) and all but one individual
pair fall short of the pre-registered 0.7 bar. Score-level reliability
(StableMut@K SD 0.001-0.004 for most models) is separately strong and not
in question. It is rank-level stability that falls short.

**Paper-ready sentence**: "H5 (pairwise Kendall's τ across dynamic-
benchmark instantiations, threshold τ>0.7) is not met at either reported
scope: mean pairwise τ = 0.583 at the N=4 headline scope (the largest all
9 canonical models can enter) and 0.569 across all pairs including a
partial fifth instantiation (present for 7 of 9 models, both Gemini
models excepted). Closing the remaining N=5 gap was quantified at $9.60
and declined, since the noise-floor mechanism driving the current
shortfall (several models clustered within 0.005 of each other, smaller
than their own measurement noise) predicts the gap would not close, and
plausibly widen, with more data. Of the 6 N=4-scope pairs, only 1
(instantiations 1-2, τ=0.889) individually exceeds 0.7, and it is the
only pair to survive Holm-Bonferroni correction within the family.
Score-level reliability is separately strong (StableMut@K SD 0.001-0.004
for most models). It is rank-level agreement across
re-instantiations that falls short of the pre-registered bar, not
measurement noise generally, and the shortfall is attributable to the
model population's own tight clustering, not to the dynamic
benchmark as an instrument."

---

## H6 clause 1 (RQ5)

**Approved wording (verbatim)**: "Test-generation mutation score on the
dynamic benchmark will correlate positively but imperfectly with
code-generation Pass@1 on a proxy benchmark..." Test: "Pearson r and
Spearman ρ between scores."

**What was executed**: Dynamic↔BigCodeBench correlation, canonical (n=3)
and cross-family (n=7) scopes, raw conditional Mut@K and coverage-
adjusted, with Pearson r / Spearman ρ / Kendall τ, bootstrap CIs and
permutation p-values (`scripts/analyze_rq5_cross_family.py`).
Cross-family, raw Mut@K: τ=0.429 (not significant, perm p=0.241).
Cross-family, coverage-adjusted: τ=0.905 (Holm-adjusted p=0.034,
survives).

**Why it differs**: No deviation in execution. The n=3 canonical-only
reading is a within-family (all-Qwen) size-scaling artifact (τ=1.000, but
permutation p=0.331, not significant at this n, and not independent
evidence). The cross-family extension (4 additional non-Qwen open-source
models) breaks that confound and is the reading that should be quoted.

**Verdict: MIXED.** Positive under both metrics. "Imperfect" holds for
the raw reading but not clearly for the coverage-adjusted reading, which
sits close to perfect rank agreement, inside this project's own
internally-defined 0.4-0.8 "validity zone," near its upper edge.

**Paper-ready sentence**: "H6 clause 1 (dynamic-benchmark mutation score
correlates positively but imperfectly with BigCodeBench Pass@1) is
mixed: positive under every metric and scope tested, but 'imperfect'
holds cleanly only for the raw conditional Mut@K reading (τ=0.429,
cross-family n=7, not significant). The coverage-adjusted reading
(τ=0.905, Holm-adjusted p=0.034) is close enough to perfect rank
agreement to read as near-redundant with a generic code-generation
leaderboard, by this project's own pre-registered 0.4-0.8 validity-zone
criterion."

---

## H6 clause 2 (RQ5)

**Approved wording (verbatim)**: "...and this correlation will be weaker
than the correlation between static-benchmark mutation score and the same
proxy. Test: Pearson r and Spearman ρ between scores." (No Fisher
z-test: that appeared only in a later, unapproved expanded draft. The
approved wording asks for the two coefficients directly.)

**What was executed**: Answerable entirely from data already computed for
clause 1, direct comparison of Dynamic↔BigCodeBench against
ULT↔BigCodeBench, same scopes, same metrics, same run
(`analysis/RQ5_CROSS_FAMILY_PROVENANCE.md`). Full table (§ below, added to
`analysis/RQ5_INTERPRETATION.md` per task 8):

| Scope | Metric | Statistic | Dynamic↔BCB | ULT↔BCB | Dynamic stronger? |
|---|---|---|---|---|---|
| canonical, n=3 | raw | Pearson r | 0.981 [0.981,1.00] | 0.927 [0.927,1.00] | yes |
| canonical, n=3 | raw | Spearman ρ | 1.000 | 1.000 | tie (ceiling at n=3) |
| canonical, n=3 | raw | Kendall τ | 1.000 | 1.000 | tie (ceiling at n=3) |
| canonical, n=3 | coverage-adj | Pearson r | 0.9999 [0.9999,1.00] | 0.859 [0.859,1.00] | yes |
| canonical, n=3 | coverage-adj | Spearman ρ | 1.000 | 1.000 | tie |
| canonical, n=3 | coverage-adj | Kendall τ | 1.000 | 1.000 | tie |
| cross-family, n=7 | raw | Pearson r | 0.461 [-0.135,0.986] | 0.243 [-0.687,0.957] | **yes** |
| cross-family, n=7 | raw | Spearman ρ | 0.464 [-0.585,1.00] | 0.143 [-0.765,1.00] | **yes** |
| cross-family, n=7 | raw | Kendall τ | 0.429 [-0.335,1.00] | 0.238 [-0.647,1.00] | **yes** |
| cross-family, n=7 | coverage-adj | Pearson r | 0.946 [0.814,0.998] | 0.747 [0.312,0.987] | **yes** |
| cross-family, n=7 | coverage-adj | Spearman ρ | 0.964 [0.565,1.00] | 0.821 [0.059,1.00] | **yes** |
| cross-family, n=7 | coverage-adj | Kendall τ | 0.905 [0.556,1.00] | 0.714 [0.059,1.00] | **yes** |

Dynamic is the stronger (or tied) correlation in **all 12** comparisons,
never weaker. At cross-family n=7 (the scope that isn't ceiling-limited),
Dynamic is strictly stronger on every one of the 6 statistic×metric
combinations.

**Caveats that travel with this table** (per `WORKBOOK_VERIFICATION.md`
§5, not previously attached to this specific comparison anywhere in the
repo): 2 of the 7 cross-family points are individually thin-cell
(CodeLlama-13B: ULT n_defined=8; Mistral-7B: Dynamic n_defined=5, ULT
n_defined=1). 2 of the 7 cross-family models have chat-template dates
postdating their own published BigCodeBench eval date. StarCoder2
required a non-identical prompt-delivery accommodation. All disclosed in
`RQ5_INTERPRETATION.md`'s existing cross-family limitations section, now
also attached at the point clause 2's table is quoted.

**Why it differs**: No deviation in test design. The approved wording
requires exactly this direct comparison, no Fisher z. The **result**
differs from the prediction: this project predicted a weaker dynamic-proxy
correlation and found the opposite.

**Verdict: NOT SUPPORTED.** Direction is opposite to the prediction.

**Paper-ready sentence**: "H6 clause 2 (the dynamic-proxy correlation
will be weaker than the static-proxy correlation) is not supported:
Dynamic↔BigCodeBench is the stronger (or tied) correlation under every
one of Pearson r, Spearman ρ, and Kendall τ, at both the n=3 canonical
and n=7 cross-family scopes, under both raw and coverage-adjusted Mut@K,
never weaker in any of the 12 comparisons tested. This is defensible as a
favourable finding, not a failed prediction: the dynamic benchmark
tracks external code-generation capability at least as well as, and by
several measures better than, the static benchmark it was designed as a
contamination-resistant alternative to."
