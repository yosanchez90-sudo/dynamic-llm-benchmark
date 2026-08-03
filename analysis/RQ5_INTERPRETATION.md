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

**(b) Conditioning/survivorship — the largest single factor found, but now
decomposed further (2026-07-28).** Mut@K is only defined where
`baseline_passed=True`, so each model's mean is taken over a
different-sized, self-selected subset (pooled baseline_pass_rate ranges
from 0.02 for Qwen 1.5B to 0.90 for GPT-5 — a 45x spread in how much of the
benchmark even contributes to the average). Re-scoring with a
coverage-adjusted metric (Mut@K × baseline_pass_rate, which folds the
selection back in rather than conditioning it away) **recovers Kendall
τ=0.905, Spearman ρ=0.964 (permutation p=0.0034)** — a near-total reversal
from the raw pooled result. This is the strongest single piece of evidence
in this diagnosis, but decomposing the product (`analysis/RQ5_DIAGNOSTICS.md`
sec 3b) sharpens what it actually shows: **baseline_pass_rate ALONE already
gives τ=0.810** — nearly all of the recovered agreement is models agreeing
on who can produce a baseline-passing suite at all (PASSES against the real
function — a stricter, later gate than mere exec/collection, which this
project's scorer tracks separately as `exec_ok`), not on mutation-killing
quality. Conditioned Mut@K alone (the pre-registered primary metric,
restricted to the same n=7/same models for a fair comparison) is τ=0.143 —
identical to the full-pool result, meaning models that clear the
baseline-pass bar do **not** then agree on which suites are the *better*
mutation killers. So: most of the apparent Dynamic/ULT disagreement is not
that the two benchmarks disagree about model *capability* broadly — it's
specifically that they disagree about *baseline pass rate* very little and
about *mutation-quality-conditional-on-passing* almost completely. Mut@K
and coverage-adjusted-Mut@K are different
estimands measuring different things (respectively: "how good are the
tests that already passed" vs "how good is the model overall, including
whether it clears the gate"); this result says the cross-benchmark
agreement lives almost entirely in the "clears the gate" component, not the
"how good once it does" component — a more precise and less flattering
statement than "most of the disagreement is conditioning" on its own. The
coverage-adjusted score is also markedly MORE reliable across Dynamic
instantiations than raw Mut@K (N=4 mean pairwise Kendall τ=1.000 vs 0.635,
`analysis/RQ5_DIAGNOSTICS.md` sec 3c) — verified not a small-n artifact, and
the same underlying fact as the validity finding: baseline_pass_rate is
apparently both the thing that varies enormously and consistently BETWEEN
models and the thing that stays comparatively stable WITHIN a model across
instantiations.

**(c) Reliability ceiling — a minor factor.** Disattenuating the observed
τ=0.143 by Dynamic's own RQ4.1 self-consistency (mean pairwise Kendall tau,
computed live rather than a frozen constant — see
`analysis/RQ5_DIAGNOSTICS.md` sec 4 for the current figure and why it's
computed live, not hard-coded) gives a disattenuated τ barely moved from
the raw observed value. Dynamic's own noisiness is not why the
cross-benchmark number is low.

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
however, complicates a simple "distinct capabilities" reading — with a
sharper edge than it first appeared: most of the gap is attributable to how
Mut@K conditions on baseline-pass rather than to Dynamic and ULT
disagreeing about model capability outright, and a coverage-adjusted
re-scoring that folds the baseline-pass rate back in recovers τ=0.905. But
decomposing that recovered agreement shows it is almost entirely a
*baseline-pass-rate* story, not a mutation-quality one: baseline_pass_rate
alone already correlates at τ=0.810 across benchmarks, while Mut@K
conditional on passing (the actual pre-registered metric) stays at τ=0.143
even within that same matched comparison. Disattenuating for Dynamic's own
measurement reliability moves the raw number only slightly (see
`analysis/RQ5_DIAGNOSTICS.md` sec 4 for the current, live-computed figure),
while the coverage-adjusted score's own (much higher, and independently
verified) reliability leaves ITS disattenuated figure essentially
unchanged — reliability is not the limiting factor for either reading. **A
further check against the pre-registered interpretation frame itself
(`analysis/RQ5_ANALYSIS_PLAN.md`, Spearman ρ 0.4–0.8 = validity-supporting,
near-perfect = redundant) sharpens this further: τ=0.905 sits at or above
the "redundant" line, not inside the validity-supporting zone.** So the
honest statement is two-sided, more specific, and less comfortable than a
first pass suggests: the metric as pre-registered and specified does rank
models inconsistently across benchmarks on mutation-quality-conditional-
on-passing (the validity-undermining zone), while the coverage-adjusted
score's cross-benchmark agreement is strong enough to raise a redundancy
concern rather than resolve a validity one. Neither candidate reading of
this benchmark's primary metric lands in the zone the plan predicted in
advance. The one
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

## Cross-family extension — final results (2026-07-29)

All 4 candidates landed complete (300/300 Dynamic, 400/400 ULT each):
DeepSeek-Coder-6.7B-Instruct, CodeLlama-13B-Instruct,
StarCoder2-15B-Instruct-v0.1, Mistral-7B-Instruct-v0.3. Full script:
`scripts/analyze_rq5_cross_family.py`; raw tables:
`analysis/RQ5_CROSS_FAMILY_PROVENANCE.md`.

**Dynamic↔ULT** (breaks nothing new about the family confound — both sides
are our own benchmarks — but adds statistical power, n=7→n=11):

| | n | Kendall τ |
|---|---|---|
| raw Mut@K, canonical-only | 7 | 0.143 |
| raw Mut@K, +cross-family | 11 | 0.345 (CI [-0.18, 0.76], p=0.16 — still not significant) |
| coverage-adjusted, canonical-only | 7 | 0.905 |
| coverage-adjusted, +cross-family | 11 | **0.855** (CI [0.61, 1.00], p=0.0001) |

The coverage-adjusted finding **holds up well** with genuine family
diversity added — a small, expected drop (0.905→0.855), still strongly
significant. The raw metric's rank agreement actually improves somewhat
(0.143→0.345) but stays statistically indistinguishable from no
relationship.

**Dynamic/ULT↔BigCodeBench — this is the result that actually breaks the
size-sweep confound**, n=3 (all-Qwen)→n=7 (4 families):

| Pair | Metric | n | Kendall τ |
|---|---|---|---|
| Dynamic↔public | raw Mut@K | 3→7 | 1.000 → **0.429** (CI [-0.34, 1.00], p=0.24 — collapses) |
| ULT↔public | raw Mut@K | 3→7 | 1.000 → **0.238** (p=0.57 — collapses) |
| Dynamic↔public | coverage-adjusted | 3→7 | 1.000 → **0.905** (CI [0.56, 1.00], p=0.0034 — holds) |
| ULT↔public | coverage-adjusted | 3→7 | 1.000 → **0.714** (CI [0.06, 1.00], p=0.032 — holds, weaker) |

**This is exactly the confirmation the "read this as size-scaling, not
cross-benchmark validity" caution above was waiting on.** The raw
pre-registered metric's perfect n=3 correlation was indeed a within-family
size-scaling artifact — it falls apart the moment real architectural
diversity enters the comparison (τ 1.000→0.429/0.238, both statistically
indistinguishable from chance). The coverage-adjusted score's correlation
survives this test essentially intact (τ 1.000→0.905 for Dynamic, a real,
significant, n=7, 4-family result) — independent, external evidence for
the same "baseline-pass-rate agreement is real and robust" finding as the
Dynamic↔ULT internal comparison above, now validated against a public
benchmark this project had no hand in constructing.

**Bottom-line construct-validity statement, checked directly against the
pre-registered frame (`analysis/RQ5_ANALYSIS_PLAN.md`), not smoothed over.**
That frame set three zones in advance: near-zero = undermines validity,
Spearman ρ roughly 0.4–0.8 = validity-supporting, near-perfect = makes the
benchmark **redundant** ("if Dynamic's ranking were fully predictable from a
generic code-gen leaderboard, there would be no reason to run a separate
test-generation benchmark at all"). Neither of this analysis's two headline
numbers lands in the validity-supporting zone:

- The pre-registered primary (conditional Mut@K, τ=0.143, and its
  cross-family echo τ=0.345) sits in the near-zero, validity-undermining
  zone — reported as-is throughout this document, not re-litigated here.
- The coverage-adjusted score (τ=0.905 canonical, 0.855 cross-family
  internal, 0.905/0.714 cross-family external) sits at or above the
  near-perfect end — by the pre-registered frame's own logic, **this is
  the "redundant" zone, not the "validity-supporting" one.** Presenting
  0.905 as an unqualified win misreads the frame that was written down
  specifically to prevent exactly that reading. Taken at face value, a
  benchmark whose coverage-adjusted score predicts a generic code-gen
  leaderboard this well is not adding much test-generation-specific
  signal beyond "can this model produce working code at all" — which is
  close to what BigCodeBench's own Pass@1 already measures.

**So the honest two-sided statement is not "the benchmark validates via the
coverage-adjusted score" — it is that NEITHER of this project's two
candidate primary-metric readings lands where the pre-registered frame
called validity-supporting.** The conditional metric is too disconnected
from external benchmarks; the coverage-adjusted metric is disconnected in
the other direction, tracking external benchmarks closely enough to raise
a redundancy concern rather than resolve it. What's left, and what actually
IS informative, is the diagnosis itself (secs above, `RQ5_DIAGNOSTICS.md`):
this benchmark's headline metric decomposes cleanly into a baseline-pass-
rate component that is highly redundant with generic coding ability
(consistent with "redundant") and a mutation-quality-conditional-on-passing
component that shows no measurable cross-benchmark signal at all
(consistent with "undermines validity", though sec 2b's noise-floor audit
shows part of that near-zero reading is a resolving-power artifact among
closely-scored models, not necessarily genuine disagreement for every
pair). Neither component, nor their product, is the "related but distinct,
ρ 0.4–0.8" result the plan predicted in advance. This should be written up
as a genuine, unresolved tension for the construct-validity argument, not
narrated past.

## Cross-family extension (approved 2026-07-28) — limitations

Full-scale Dynamic (L1-L4, inst1) + ULT core_400 runs for 4 non-Qwen
candidates (DeepSeek-Coder-6.7B-Instruct, CodeLlama-13B-Instruct,
StarCoder2-15B-Instruct-v0.1, Mistral-7B-Instruct-v0.3) are the mechanism
for breaking the Parts 2-3 all-Qwen size-sweep confound above. Two
limitations to disclose alongside whatever correlation these runs produce,
not discovered after the fact:

**Chat-template drift relative to each model's published BigCodeBench
number.** Snapshot verification (`analysis/RQ5_CROSS_FAMILY_PROPOSAL.md`)
confirmed no weight-file-changing commit since each model's eval date for
all 4 candidates — but weights are not the whole story for a chat model;
the *template* that turns messages into a prompt string matters too, and
two of the four postdate their own eval:
- **CodeLlama-13B-Instruct**: `tokenizer_config.json`'s `chat_template` was
  added 2024-03-04 — its BigCodeBench eval date is 2023-08-25. At eval
  time this model most likely had NO chat template at all; BigCodeBench's
  own harness would have applied its own Llama-style formatting. This
  project's harness applies the template that exists TODAY.
- **Mistral-7B-Instruct-v0.3**: tokenizer/chat-template adjustments landed
  Aug 2024 — its eval date is 2024-05-22.
- DeepSeek-Coder-6.7B-Instruct and StarCoder2-15B-Instruct-v0.1's templates
  predate or coincide with their eval dates — no equivalent concern.

Practically: our own Dynamic/ULT numbers for these two models are internally
valid (every model in this project is prompted via the same
`apply_chat_template()` call, consistently) but are **not guaranteed to
reproduce the exact prompt formatting that produced their published
BigCodeBench Pass@1** — a cross-family correlation against those published
numbers should note this rather than treat all 4 candidates' published
figures as equally trustworthy anchors. This is a prompt-FORMATTING
provenance gap, not a weight-snapshot one; the two are logged and verified
independently (`chat_template_hash`/`chat_template_source` in
`src/models/local.py` output vs. the HF commit-history check).

**StarCoder2-15B-Instruct-v0.1's prompt delivery differs from the other
three.** Its `chat_template` unconditionally rejects a `role="system"`
message (verified by reading the template source directly, not inferred).
Accommodated via `supports_system_role: false`
(`configs/dry_run_ult_starcoder2_15b.yaml` and its full-scale configs): the
system instruction is folded into the first user turn instead of sent
separately (`src/data/test_gen.py::_build_messages`), logged per-row as
`prompt_delivery_mode` (`"system_role"` for the other 3 candidates and every
canonical model, `"system_folded_into_user"` for StarCoder2). The
instruction TEXT is identical either way — only its delivery differs — but
this means StarCoder2's results are not from a byte-identical prompt
structure to the other candidates, a genuine (small, disclosed) methodological
asymmetry within the cross-family cohort itself, separate from the
published-benchmark comparison above.

**Mistral-7B-Instruct-v0.3 floor verification (2026-07-28).** Its full-scale
Dynamic run landed a baseline_pass_rate of just 1.7% (5/300) — by far the
lowest of the four cross-family candidates and comparable to Qwen 1.5B's
established floor behavior. Before treating this as a real capability
finding rather than a harness artifact (chat-template drift was already
flagged as a live concern for this model), inspected 5 raw completions
end-to-end, one per tier plus a duplicate at L4, all with `exec_rate=1.0`
(collectible) and `baseline_passed=False`, plus 2 of the 10 `exec_rate=0.0`
rows:
- **`extracted_test_file` matches the raw `response` verbatim in all 7
  cases** (modulo the markdown code-fence stripping) — extraction did its
  job; nothing here is a parsing artifact.
- **L1-coerce-002, L2-validator-001, L3-search-001, L4-aggregate-001,
  L4-pipeline-001** (all `exec=1.0`, `baseline_passed=False`): syntactically
  clean, well-formed test files that assert **specific, concrete, wrong**
  numeric values for what the function actually returns (e.g.
  `test_encode_input_normal_case` asserts `encode_input(5, 2) == [5, 15]`
  against the real implementation's actual output) — the model can write a
  valid, importable test but reasons incorrectly about the function's real
  behavior. Notably this shows up even at **L1**, this project's easiest
  tier, where every other model tested so far (canonical and cross-family)
  sits at or near ceiling — this is a genuine, tier-independent capability
  gap for this model, not a hard-tier-only effect.
- **L1-format-001** (`exec=0.0`, "collection error"): the model's own
  generation degenerates into an endless repeated-digit string
  (`...9999999999...`, response length 2265 chars, cut off mid-digit-string
  by `max_new_tokens`) — the same repetition-collapse failure mode already
  documented for Qwen 1.5B's L4 seeds 1101/1102
  (`analysis/STABILITY_INTERPRETATION.md`), just triggered here at L1 rather
  than only at the hardest tier.
- **L1-arithmetic-001** (`exec=0.0`, "collection error"): a complete,
  ordinary-looking test file with no chat-template pollution or stray
  tokens — the collection failure itself traces to the model's own
  content (mismatched function signature/name assumption for this
  instance), not to prompt construction.

None of the 7 inspected rows show any sign of the chat-template-drift caveat
above actually corrupting output (no stray special tokens, no malformed
structure, no truncated/duplicated framing) — the low pass rate is a
genuine capability-limitation finding for this model on this benchmark, by
the same evidence standard already applied to Qwen 1.5B, not a
template-drift or extraction artifact.

## What this means going forward

Superseded by the cross-family extension above (completed 2026-07-29,
n=11 Dynamic↔ULT / n=7 Dynamic-ULT↔BigCodeBench) — the "genuinely larger N"
this section originally called for has now landed, and it changed the
read: the raw pre-registered metric's apparent cross-benchmark agreement
(both internal and external) does not survive it, while the coverage-
adjusted score's does. One caution carried over unchanged: with n=7-11,
individual points still matter — a future 5th or 6th cross-family model
landing differently could move these numbers meaningfully, so treat this
as strong current evidence, not a permanently closed question. The same
bootstrap/permutation reporting standard applies to any future extension.
