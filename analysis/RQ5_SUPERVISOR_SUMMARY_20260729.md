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

## 3. Is this a Qwen-family artifact? Cross-family extension (in progress)

The one place we did see a strong, clean correlation was against
BigCodeBench (a public leaderboard) — but that comparison was **n=3, all
three points the same model family (Qwen) at three sizes.** A perfect
rank match across a 1.5B→7B→32B sweep within one family is close to the
least surprising result available (bigger checkpoints are better at
everything), so it's not independent evidence of validity.

To break that confound, we're running **4 additional open-source models
from 4 different families** (DeepSeek-Coder-6.7B, CodeLlama-13B,
StarCoder2-15B, Mistral-7B-v0.3) on both benchmarks, expanding:
- Dynamic↔ULT from **n=7 → n=11**
- Dynamic/ULT↔BigCodeBench from **n=3 (all-Qwen) → n=7 (4 families)**

**Status as of this morning, 3 of 4 landed** (StarCoder2 still running —
one config bug and one cluster-queue relocation cost us time, expect it
done today):

| | n | Kendall τ |
|---|---|---|
| Dynamic↔ULT, coverage-adjusted, canonical-only (Qwen+API) | 7 | 0.905 |
| Dynamic↔ULT, coverage-adjusted, +3 of 4 new families | 10 | **0.867** |

**Preliminary answer: the executability-agreement finding survives adding
genuinely different model families** — it drops a little (0.905→0.867) but
does not collapse. This is provisional (StarCoder2 not in yet, so it's
n=10 of the eventual n=11), and I'd treat it as directional until the last
model lands and I re-run the final numbers — which I expect to have later
today.

We also independently verified (2026-07-28) that Mistral's very low pass
rate on our benchmark (1.7%) is a genuine capability finding, not an
artifact of running an unfamiliar model family through our harness — traced
5+ raw completions end to end and confirmed the test extraction is faithful
and the failures are real reasoning/generation errors, including at our
easiest difficulty tier (where every other model we've tested sits near
ceiling).

## Bottom line to say out loud

1. **As pre-registered, our benchmark's mutation-quality ranking does not
   agree with a static benchmark's.** Real, disclosed, not explained away.
2. **The reason is specific, not vague**: both benchmarks agree well on
   which models can produce a working test suite at all; neither one's
   fine-grained "how good is the test once it works" signal transfers to
   the other. That's a scoping finding about Mut@K's conditioning, not a
   verdict on the benchmark's overall design.
3. **This isn't just a Qwen-family artifact** — the 4-family extension so
   far preserves the executability-driven agreement once size-scaling is
   no longer doing all the work. Final, complete number (n=11) expected
   today.

## Appendix: where the detail lives

- Pre-registered primary result + full diagnosis:
  `analysis/RQ5_INTERPRETATION.md`, `analysis/RQ5_DIAGNOSTICS.md`
- Cross-family extension proposal + status:
  `analysis/RQ5_CROSS_FAMILY_PROPOSAL.md`,
  `analysis/RQ5_CROSS_FAMILY_PROVENANCE.md`
- Comparison A conditioning finding: `analysis/COMPARISON_PROVENANCE.md`
