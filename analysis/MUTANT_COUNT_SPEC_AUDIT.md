# Mutant-count spec audit — PROJECT_BRIEF §5.1/§5.3 vs observed data

Prompted by an observation during the metric-definition reconciliation
(`analysis/RQ5_CROSS_DEFINITION_AUDIT.md`) that real mutant counts range
from 4 to 771 (mean 94.4) — apparently far outside PROJECT_BRIEF.md §5.3's
stated "cap 30 mutants/instance, sample if more" and §5.1's per-tier target
bands (5-10/10-15/15-25/25-40 for L1-L4). This audit determines exactly
what's true, for which benchmark, and what (if anything) needs to change.

**Headline finding, stated up front**: the 4-771/mean-94.4 figure is
**ULT-specific, not project-wide**. Dynamic (the project's own template
corpus, which §5.1/§5.3 actually describe) is close to its declared bands.
The real, disclosable gap is narrower than the opening observation
suggested — but it is real, and specifically about Dynamic's L4 tier and
about the brief's own internal inconsistency between §5.1 and §5.3.

## (a) Was the cap/sampler ever implemented?

**No — searched the entire git history of the mutation-generation engine
(`template_corpus/templates/_smoke/mutator.py`) and found no cap or
stratified-sampling logic at any point.** `generate_mutants()`
(`mutator.py`) runs all 7 SAC operators (AOR, ROR, LOR, CR, BM, SDL, RSM)
exhaustively over whatever mutation sites exist in the given source and
returns every one — there is no `if len(mutants) > 30` branch, no random
subsample, in any commit. `src/eval/mutation_adapter.py` (the thin adapter
between the engine and the harness) and `src/eval/test_gen_scorer.py`
(the scorer that consumes the mutant list) likewise contain no capping
logic — `score_problem()` receives `mutants: list[Mutant]` and scores
every one of them (minus any that get `dropped` for failing to import).

**Consequence**: §5.3's cap was a design intention that was never carried
into code, for either Dynamic or ULT/PLT (both use the same
`generate_mutants()` engine — `mutation_adapter.py`'s own docstring notes
`scope_fn_name` exists specifically to support "external sources like
UnLeakedTestBench/PreLeakedTestBench").

## (b) Why did `mutation_sweep.py` report "60/60 in declared mutant-count band" on 2026-07-14?

Because it validates a much narrower population than "every mutant count
in the evaluated benchmark," and it was never claimed to cover more than
that — the gap is in how its result was *described downstream*, not in
its own logic. Precisely:

1. **Dynamic only.** `mutation_sweep.py`'s `sweep()` globs
   `template_corpus/templates/{L1,L2,L3,L4}/*.py` — the 60 hand-authored
   templates. It has no code path touching ULT/PLT at all; those are
   loaded by a completely different module (`src/data/ult_plt.py`) with no
   `Template`/`expected_mutant_count` concept.
2. **One hardcoded seed (42), not the full instantiation distribution.**
   `instantiate(t, 42)` draws exactly one canonical instance per template,
   deterministically. The real evaluated benchmark instantiates each
   template across 5 seeds (101-105, further offset per instantiation ID
   for the stability study) — `mutation_sweep.py` checks none of those,
   only the seed-42 rendering.
3. **The band itself is a single spot-check, not a measured range.**
   `template_corpus/templates/spec/__init__.py`'s docstring for
   `expected_mutant_count` states explicitly: *"This tuple is (measured -
   3, measured + 3) where `measured` is the author's spot-checked count on
   a representative instance."* — e.g. `L3-clamp-seq-001.py`'s
   `expected_mutant_count=(18, 24), # measured 21; band = measured +/- 3`.
   The band is therefore, by construction, centred on the same single
   instance `mutation_sweep.py` re-checks — a self-consistency check, not
   an independent stability measurement across the population actually
   used in evaluation.

**This was found and disclosed as a scope/documentation gap, not a
runtime bug** — `mutation_sweep.py`'s own logic does exactly what it says
it does. The bug is one level up: `scripts/archive_diversity_audit.py`'s
generated `README.md` hardcoded a "60/60 templates land inside their
declared per-template stability band" sentence (see
`analysis/VALIDATOR_SWEEP.md`, error ledger bug #9) that reads, out of
context, as a broader claim than `mutation_sweep.py` can support — fixed
2026-08-03 by making that summary recompute itself from the underlying
data on every run and explicitly stating the scope limitation (single
seed, Dynamic-only) directly in the generated text.

## (c) The actual per-tier mutant-count distribution vs the spec bands

Computed directly from every row with a defined `mutants_total` in
`data/results/{dynamic,ult,plt}/*.jsonl` (all models, all instantiations —
i.e. the full *evaluated* population, not a single spot-check):

### Dynamic (the population §5.1/§5.3 actually describe)

| Tier | n rows | min | max | mean | Spec band | % within band | % exceeding the §5.3 cap of 30 |
|---|---|---|---|---|---|---|---|
| L1 | 3,653 | 5 | 11 | 7.6 | 5-10 | 93.6% | 0.0% |
| L2 | 3,105 | 10 | 15 | 13.3 | 10-15 | 100.0% | 0.0% |
| L3 | 3,173 | 17 | 26 | 21.1 | 15-25 | 92.9% | 0.0% |
| L4 | 2,694 | 30 | 40 | 35.6 | 25-40 | 100.0% | **93.3%** (2,514/2,694) |

L1-L3 are close to their declared bands (92.9-100% within) and never
approach the 30-mutant cap at all — it was never needed for these tiers.
**L4 is where the brief is internally inconsistent**: its own declared
per-tier target band (25-40) already exceeds §5.3's separately-stated
30-mutant cap, and the real data lands squarely inside the *declared band*
(mean 35.6, matching L4's 25-40 range almost exactly) while just as
squarely violating the *cap* (93.3% of L4 rows exceed 30). These are not
independently satisfiable — the brief specifies both, and the corpus was
built to satisfy the per-tier band, not the blanket cap.

### ULT / PLT (real-world scraped functions — not templated, no §5.1/§5.3 band ever applied)

| Benchmark | n rows | min | max | mean | % exceeding 30 |
|---|---|---|---|---|---|
| ULT | 4,501 | 4 | 771 | 94.8 | 81.8% |
| PLT | 2,916 | 4 | 991 | 80.7 | 84.9% |

This is the population the opening "4-771, mean 94.4" observation actually
describes. ULT/PLT functions are real, scraped code with organically
varying AST complexity; Cosmic-Ray-style mutant generation (`generate_mutants()`,
matching the ULT/PLT paper's own "generate all possible mutants" methodology,
`analysis/RQ5_CROSS_DEFINITION_AUDIT.md` §1a) was never intended to be
capped to a Dynamic-style band, since doing so would break comparability
with the source paper's own methodology (see (e) below).

## (d) Consequence: does the macro/micro choice change any conclusion?

**For Dynamic: no, and the effect is negligible.** Per-tier macro (mean of
per-problem ratios, this project's actual metric) vs micro (pooled
kill/scored ratio) computed for every canonical model at every tier:
only 2 of the ~28 model×tier cells checked differ by more than 0.01, and
the largest is 0.040 (Qwen 1.5B, L3, on an n_defined=2 cell that is
already thin/unreliable for other reasons). This is expected given (c):
Dynamic's per-tier mutant-count range is narrow (e.g. L4: 30-40, a
10-mutant spread), so the two aggregation choices barely diverge.

**For ULT/PLT: the absolute numbers shift meaningfully, and the shift can
reorder closely-scored models, but the project's actual reported
conclusions survive it.** On ULT, macro vs micro per canonical model:

| Model | macro | micro | gap |
|---|---|---|---|
| Qwen 32B | 0.901 | 0.839 | +0.062 |
| Qwen 7B | 0.894 | 0.885 | +0.009 |
| Gemini Pro Preview | 0.888 | 0.883 | +0.006 |
| Gemini Flash-Lite | 0.821 | 0.744 | +0.078 |
| Claude Haiku | 0.801 | 0.600 | +0.201 |
| Claude Sonnet | 0.756 | 0.583 | +0.173 |
| Qwen 1.5B | 0.407 | 0.390 | +0.016 |

Kendall τ between the macro-ranked and micro-ranked model orderings:
**0.810** (not 1.0) — Qwen 7B and Gemini Pro Preview swap the #2/#3
position depending on which is used (0.894 vs 0.888 under macro; 0.885 vs
0.883 under micro — a near-tie either way, but the ORDER flips). The two
API models with the largest gaps (Claude Haiku, Claude Sonnet, both
≈+0.17-0.20) are the ones whose ULT problem population presumably skews
toward higher-mutant-count functions relative to their own killed-count
distribution — not independently verified per-model here, flagged as a
direction for follow-up, not asserted as explained.

**Does either project-reported conclusion actually depend on this
choice?** Checked directly, not assumed:
- **Comparison A** (Dynamic-L4 vs ULT, raw/unfiltered): recomputed under
  micro — effect_r=+0.200, p=0.8125, **identical to three decimal places**
  to the macro-based reported figure. No change.
- **Comparison B** (ULT vs PLT): recomputed under micro — PLT scores
  higher for 6 of 7 models (only Qwen 7B reverses, and only slightly:
  0.849 vs 0.885), same qualitative direction as the macro-based reported
  result. No change to the headline finding.

**So: the macro/micro choice does not change any conclusion this project
actually reports** (Comparison A's null, Comparison B's PLT>ULT
direction) — it would only matter for a claim this project does not make,
e.g. "Gemini Pro Preview specifically outranks Qwen 7B on ULT," which is
within noise of a coin flip under either definition.

## (e) Recommendation: amend the brief and disclose, do not retro-cap and rescore

**Recommendation: amend §5.1/§5.3 and disclose this audit; do not
retro-cap.** Reasoning for both halves, not just the conclusion:

**Cost of retro-capping (rejected)**: applying a 30-mutant stratified cap
retroactively would require re-generating a capped mutant subset for every
affected row (93.3% of Dynamic-L4 rows, 82-85% of ULT/PLT rows — i.e. the
large majority of every row this project has ever scored) and then
**re-running the mutation-testing harness against that new subset** — this
is not a re-analysis of existing numbers, it is re-executing test suites
against a different set of mutants, which is compute (SLURM time), not
free. Every downstream number is affected transitively: Comparison A/B's
Mut@K and coverage_adjusted values, all of RQ5's correlations, Comparison
C's Mut@K figures (already reported as final, PROJECT_BRIEF.md §11),
StableMut@K. This late in the project, re-running the full pipeline over
a corrected mutant population carries real timeline risk for a change (d)
already shows produces, at most, a reordering among closely-scored models
on ULT/PLT — not a reversal of any reported qualitative conclusion.

**Cost of amend + disclose (recommended)**: zero re-computation risk,
immediate, and consistent with how this project already handled the
metric-definition mismatch (`RQ5_CROSS_DEFINITION_AUDIT.md`) — disclose
the gap, explain why the as-run methodology is still defensible, do not
retroactively rewrite results to match a brief that was itself not fully
self-consistent (§5.1 vs §5.3, see (c)).

**What "amend" should say, concretely** (applied in
`PROJECT_BRIEF.md` directly, see the brief-reconciliation pass): the
30-mutant cap was never implemented; Dynamic's L1-L3 tiers never needed
it (they land inside the declared bands without any capping); L4's
declared band (25-40) supersedes the cap in practice and was what the
corpus was actually built to satisfy; ULT/PLT mutants are intentionally
uncapped, generated the same way as the source paper's own methodology
(Cosmic-Ray-style "all possible mutants"), which is required for
Comparison A/B to be comparing against ULT/PLT on like terms rather than
an artificially thinned mutant set unique to this project. The 4-771/
mean-94.4 figure describes ULT specifically, not the project as a whole.
