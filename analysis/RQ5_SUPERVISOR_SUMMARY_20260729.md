# RQ5 bottom-up validity — summary for supervisor meeting (2026-07-29)

## The question

*"Correlation (in model ranking) with existing coding benchmarks? Run a
few open-source models on both our benchmark and public benchmarks, and
see if these benchmarks can (1) rank models consistently, (2) produce
accuracies/scores that correlate."*

This is exactly what the last two weeks of RQ5/H6 work has been doing.
Below is the honest answer, in three parts: the headline result, why it
came out that way, and whether it holds up once the model set is widened
beyond a single family.

## 1. Headline result: rank agreement is weak, as specified

We compared our Dynamic benchmark against ULT (a static benchmark) across
**7 models spanning 5 providers** (Claude, Gemini, GPT-5/GPT-5-mini once
that data lands, and 3 Qwen sizes) using the pre-registered primary metric
(Mut@K, mutation-kill rate) and the pre-registered primary statistic
(Kendall's tau, a rank-agreement measure — chosen over Pearson correlation
specifically because a linear correlation coefficient can look strong even
when models don't actually rank consistently, which turned out to be
exactly the risk here).

**Kendall τ = 0.143 (n=7).** Near zero. The two benchmarks do **not** rank
models consistently on the metric as pre-registered. This is reported
as-is — it is not the flattering answer, and we are not softening it.

(For context: the same comparison using Pearson r looks much better — 0.904
— which is precisely why the rank statistic was pre-registered as primary.
Pearson is misleading here because one model, Qwen-1.5B, is a clear outlier
that drags the linear correlation up almost by itself; the other six models
are bunched tightly on our benchmark but spread widely on ULT, and among
those six the rank order is close to reversed between the two benchmarks.)

## 2. Why: the disagreement is mostly about *executability*, not test quality

We didn't stop at the negative result — we decomposed it, because a null
result with no diagnosis isn't useful to report. Mut@K is only defined for
problems where the model's test suite actually runs and passes against the
original function (`baseline_passed=True`). That means each model's score
is averaged over a different, self-selected subset of problems — a model
that rarely produces a passing suite gets averaged only over the easy
subset it did clear, not penalized for how rarely it clears the bar at all.

Re-scoring with baseline pass rate folded back in (Mut@K × pass rate)
**recovers τ = 0.905** — a near-complete reversal. But we went one step
further and decomposed *why*:

| Signal | τ (n=7) |
|---|---|
| Pass rate alone (can the model produce a passing suite at all?) | **0.810** |
| Mut@K alone, conditional on passing (is the passing suite a *good* one?) | **0.143** |
| The combined, coverage-adjusted score | 0.905 |

**The two benchmarks agree strongly on which models can produce working
test suites. They do not agree at all on which of the working suites are
better mutation-killers.** That's the honest, precise version of the
finding — not "the benchmarks disagree," and not "conditioning fixes it,"
but "the agreement that exists is about executability, and the part of the
metric that's supposed to measure test *quality* shows no cross-benchmark
signal once you control for that."

We also checked this isn't a measurement-noise artifact: the coverage-
adjusted score is independently *more* stable across our benchmark's five
repeat instantiations (τ=1.000 vs 0.635 for raw Mut@K) — same underlying
reason (pass rate is a big, stable difference between models; fine-grained
mutation-quality differences are noisier), not a separate finding.

**Side finding, same audit**: our own internal Comparison A (Dynamic vs
ULT, the more basic "do the two benchmarks even point the same direction"
check) has its effect *direction* flip depending on whether you apply this
same conditioning — raw says ULT scores slightly higher, adjusted says our
benchmark scores higher (n=5 either way, neither statistically
significant, but the sign isn't robust). Flagged, not hidden.

## 3. Is this a Qwen-family artifact? Cross-family extension — DONE, and it's the cleanest result of the whole analysis

The one place we did see a strong, clean correlation was against
BigCodeBench (a public leaderboard) — but that comparison was **n=3, all
three points the same model family (Qwen) at three sizes.** A perfect
rank match across a 1.5B→7B→32B sweep within one family is close to the
least surprising result available (bigger checkpoints are better at
everything), so it's not independent evidence of validity.

To break that confound, we ran **4 additional open-source models from 4
different families** (DeepSeek-Coder-6.7B, CodeLlama-13B, StarCoder2-15B,
Mistral-7B-v0.3) on both benchmarks. **All 4 now complete** (300/300 Dynamic
+ 400/400 ULT each), expanding Dynamic↔ULT from n=7→n=11 and
Dynamic/ULT↔BigCodeBench from n=3 (all-Qwen)→n=7 (4 families).

**This is the result that actually answers the question**, and it's a
clean story:

| Comparison | Metric | n: 3-Qwen → 4-family | Kendall τ |
|---|---|---|---|
| Dynamic↔ULT | raw Mut@K | 7 → 11 | 0.143 → 0.345 (still not significant, p=0.16) |
| Dynamic↔ULT | coverage-adjusted | 7 → 11 | 0.905 → **0.855** (p=0.0001 — holds) |
| Dynamic↔BigCodeBench | raw Mut@K | 3 → 7 | 1.000 → **0.429** (p=0.24 — collapses) |
| Dynamic↔BigCodeBench | coverage-adjusted | 3 → 7 | 1.000 → **0.905** (p=0.0034 — holds) |
| ULT↔BigCodeBench | coverage-adjusted | 3 → 7 | 1.000 → **0.714** (p=0.032 — holds, weaker) |

**The "perfect" n=3 BigCodeBench correlation was exactly the within-family
size-scaling artifact we suspected** — the raw metric's correlation with an
external public benchmark falls apart the moment genuine architectural
diversity is added (1.000→0.429, no longer distinguishable from chance).
The coverage-adjusted score's correlation with that same external
benchmark **survives essentially intact** (1.000→0.905) — and this is now
independent, external, cross-family evidence for the executability-
agreement finding in §2, not just an internal comparison between our own
two benchmarks.

We also independently verified (2026-07-28) that Mistral's very low pass
rate on our benchmark (1.7%) is a genuine capability finding, not an
artifact of running an unfamiliar model family through our harness — traced
5+ raw completions end to end and confirmed the test extraction is faithful
and the failures are real reasoning/generation errors, including at our
easiest difficulty tier (where every other model we've tested sits near
ceiling).

## Bottom line to say out loud

1. **As pre-registered, our benchmark's mutation-quality ranking does not
   agree with a static benchmark's, or with a public leaderboard.** Real,
   disclosed, not explained away.
2. **The reason is specific, not vague**: all three benchmarks agree well
   on which models can produce a working test suite at all; none of their
   fine-grained "how good is the test once it works" signals transfer to
   each other. A scoping finding about Mut@K's conditioning, not a verdict
   on the benchmark's overall design.
3. **This is not a Qwen-family artifact — confirmed, not just suspected.**
   The n=3 "perfect" public-benchmark correlation collapses once 4 real
   families are added (exactly as predicted); the coverage-adjusted score's
   correlation survives the same test, both internally (our two benchmarks)
   and externally (against BigCodeBench). That's the strongest, most
   defensible piece of evidence in this whole analysis, and it's now final,
   not preliminary.

## Appendix: where the detail lives

- Pre-registered primary result + full diagnosis:
  `analysis/RQ5_INTERPRETATION.md`, `analysis/RQ5_DIAGNOSTICS.md`
- Cross-family extension proposal + status:
  `analysis/RQ5_CROSS_FAMILY_PROPOSAL.md`,
  `analysis/RQ5_CROSS_FAMILY_PROVENANCE.md`
- Comparison A conditioning finding: `analysis/COMPARISON_PROVENANCE.md`
