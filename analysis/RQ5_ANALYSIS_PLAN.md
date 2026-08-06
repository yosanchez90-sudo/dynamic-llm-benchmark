# RQ5 / H6 — cross-benchmark validity: pre-registered analysis plan

**Pre-registered 2026-07-27, before any correlation in this document is
computed** (Prompt C', supervisor's "bottom-up" construct-validity ask,
2026-07-27 meeting). Companion to PROJECT_BRIEF.md's top-down framing
(capability-defined corpus, §2/§5) — see the write-up stub at the end of
this file for how the two halves fit together.

## Research question and hypothesis

**RQ5**: How well does dynamic-benchmark test-generation performance
correlate with code-generation performance on a proxy benchmark
(BigCodeBench), and does the correlation differ dynamic vs static (ULT)?

**H6**: Pearson r + Spearman ρ between mutation score and proxy Pass@1,
positive and significant.

## Metrics

- **Score correlation**: Pearson r (linear) + Spearman ρ (monotonic;
  primary, since there's no reason to expect a linear relationship between
  a mutation-kill rate and a Pass@1 rate) between each pair of benchmark
  scores, one point per model.
- **Rank consistency**: Kendall τ between model rankings on each pair of
  benchmarks — the question "do the two benchmarks agree on WHICH models
  are better," distinct from "are the scores linearly/monotonically
  related."

## Comparisons

Three benchmark pairs, each analysed identically:
1. **Dynamic ↔ public** (primary; BigCodeBench, see harvest below)
2. **ULT ↔ public**
3. **Dynamic ↔ ULT** (this project's own two benchmarks — a same-day,
   zero-compute result, see Part 1 below; not gated on the public harvest)

## Primary score definition

- **Dynamic**: pooled Mut@K — mean mutation score across all four tiers
  (L1-L4) and all available instantiations for a model, i.e. the single
  number PROJECT_BRIEF.md's headline metric produces per model when not
  stratified by tier. **baseline_pass_rate (pooled) is secondary** —
  reported alongside for the same reason it's secondary throughout this
  project (a looser, always-defined metric that Mut@K sits on top of).
- **ULT**: mean Mut@K over core_400 (already computed for Comparison
  A/B — `src/Analysis/comparison.py`), matching how Comparison A treats it.
- **Public proxy**: Pass@1 (or the benchmark's own headline pass metric) on
  BigCodeBench, from either a published leaderboard entry that matches this
  project's EXACT pinned snapshot (see harvest, Part 2) or a self-run
  (Part 3, STOP-gated).

## Power and reporting

N is small — 7-9 models depending on data-landing status at analysis time
(this project evaluates 9 models total; GPT-5/GPT-5-mini and, on Dynamic,
Gemini 3.1 Pro Preview are partially or not yet landed as of 2026-07-27, see
`data/results/`). This is **not enough for a well-powered correlation test**
and the write-up must say so explicitly, not just report a p-value and move
on. Reporting standard, throughout:
- **Bootstrap CI** (n_boot=2000, resampling model-pairs with replacement,
  matching this project's existing convention in `src/Analysis/comparison.py`
  and `src/Contamination/did.py`) for every r/ρ/τ point estimate.
- **Permutation p-value** (shuffle one side's model labels, n_perm=10000)
  rather than a parametric p-value, given N is too small for the normal
  approximation to be trustworthy.
- Effect size (the correlation coefficient itself) is primary; the p-value
  is supporting context, consistent with PROJECT_BRIEF.md §3.1's general
  rule for this project ("effect sizes with CIs are primary; p-values
  support").
- State the power limitation plainly: with N=7-9, only a very strong
  correlation would reach conventional significance at all; a
  non-significant result at this N is not evidence of "no relationship,"
  and a significant one should be read as a lower bound on how strong the
  true relationship needs to be to have been detectable.

## Interpretation frame — recorded in advance, before seeing the correlation

Test-generation and code-generation are **related but distinct**
capabilities. The prediction, stated before any number is computed:

- **Near-zero correlation would undermine this benchmark's construct
  validity** — if test-writing ability on this project's Dynamic benchmark
  had nothing to do with general coding capability, that would suggest the
  benchmark is measuring something idiosyncratic rather than a genuine
  facet of model capability.
- **Near-perfect correlation would make the benchmark redundant** — if
  Dynamic's ranking were fully predictable from a generic code-gen
  leaderboard, there would be no reason to run a separate test-generation
  benchmark at all; part of this project's motivation is that test
  generation is its own skill, not a free corollary of code generation.
- **Moderate-to-strong (roughly Spearman ρ in the 0.4-0.8 range, informally
  — not a hard cutoff, a qualitative zone) is the validity-supporting
  result**: positive and clearly non-trivial, but with real unexplained
  variance, consistent with "related but distinct."

This frame is written down now so the actual result (Part 4) is read
against a prediction made in advance, not fit to whatever number comes out.

## Plan of work (parts, not phases — Part 1 does not wait on Parts 2-3)

1. **Zero-compute**: Dynamic (pooled + per-tier) vs ULT core_400 model
   ranking + score correlation, from data already on disk. No gate, no
   wait — same-day deliverable regardless of the public-benchmark harvest.
2. **Leaderboard harvest**: which of this project's exact pinned model
   snapshots have published BigCodeBench (primary)/EvalPlus/HumanEval+/
   LiveCodeBench (secondary, only if snapshot-matched) numbers. A model
   substituted mid-project for availability reasons (Gemini 3.1 Pro
   Preview/Flash-Lite replacing the retired 2.5 Pro/Flash, PROJECT_BRIEF.md
   §11) is **dropped from public-benchmark pairs if its exact snapshot
   has no published number** — never proxied by a different Gemini
   version's number. Snapshot mismatch is not an acceptable substitute for
   missing data anywhere in this analysis.
3. **Self-run plan** for local models lacking a published number (expected:
   the 3 Qwen sizes) — a STOP gate, proposal only, not executed without
   explicit approval.
4. **Full analysis**: all three benchmark pairs, tables + a labelled
   correlation scatter figure, archived with provenance.
5. **Write-up stub** for the Discussion chapter, connecting this
   (bottom-up, empirical) analysis to PROJECT_BRIEF's top-down
   (capability-defined corpus) framing as the two halves of construct
   validity.

## Deferred / explicitly out of scope for this plan

Per session rules: no GPU submission proposed here is executed without a
separate approval step (Part 3), and no correlation number in this document
existed before this plan was committed.

## Addendum (2026-07-28/29) — cross-family extension, NOT part of the original pre-registration

Flagged explicitly for audit-trail honesty: this plan's Part 3 ("Self-run
plan for local models lacking a published number") anticipated re-running
the project's *own* 3 Qwen sizes, which turned out to be unnecessary once
the leaderboard harvest found published numbers for all three. It did
**not** anticipate running additional, non-Qwen model families — that
extension was proposed and approved separately (`analysis/
RQ5_CROSS_FAMILY_PROPOSAL.md`, approved 2026-07-28) in direct response to
the supervisor's own "bottom-up" follow-up ask, specifically to break the
all-Qwen size-sweep confound the harvest's n_models=3 result left unresolved. It
is a genuine post-hoc addition to this research program, not something
pre-registered here in advance, even though it answers the same research
question. Executed and reported in full in `analysis/RQ5_INTERPRETATION.md`
("Cross-family extension — final results") and condensed in
`analysis/RQ5_SUPERVISOR_SUMMARY_20260729.md`.
