# H3 (RQ2) — tier gradient: pre-registered analysis plan

**Written and committed before any H3 correlation is computed** (matching
the discipline already used for RQ5's `RQ5_ANALYSIS_PLAN.md`).
`analysis/HYPOTHESIS_COVERAGE_AUDIT.md` found H3 had never been
implemented. This plan fixes every design choice in advance so the
eventual result can't be read as tuned after seeing it.

## Research question and hypothesis

**RQ2**: How does generated-test effectiveness (mutation score) vary
across the four CC tiers (L1-L4)?

**H3**: Spearman ρ between tier index and mutation score, per model and
pooled.

## Estimands — decided in advance

**Per-model estimand (primary)**: for each of the 9 canonical models,
Spearman ρ between tier index (ordinal 1-4) and `mutation_score`, computed
**across every individual problem row with `baseline_passed=True`** for
that model (not across the 4 per-tier means). This is a deliberate choice
over the alternative (correlating 4 tier-means against tier index, n≤4
per model): a 4-point correlation has almost no statistical power and no
CI worth reporting, while the problem-level version gives each model
hundreds of data points and a correlation whose bootstrap CI and
permutation p-value (`src/Analysis/correlation.py::compute_correlations`,
already built and used throughout RQ5) mean something. The 4-tier-mean
version is still reported, but as a **low-power supplementary row**, not
the primary per-model result, labelled as such, n≤4 stated explicitly,
never described as "significant" or "not significant" on its own.

**Pooled estimand**: Spearman ρ between tier index and `mutation_score`
across every canonical model's defined rows pooled together. **Caveat
decided in advance, not discovered after computing it**: this pools a
between-model confound with the tier effect. If some models are
better across the board, pooling could show a tier effect that's partly
"which models happen to have more rows at which tier," not a pure
within-model tier effect. The per-model estimand above is the one that
isolates the tier effect cleanly. The pooled estimand is reported as a
secondary, coarser summary with this confound stated alongside it, not
as a stronger or more authoritative number than the per-model results.

## Ceiling-effect handling — decided in advance

The tier-discrimination gradient is already established
(`analysis/RQ5_DIAGNOSTICS.md`, `analysis/METRICS_AND_FINDINGS_EXPLAINED.md`
finding #3): L1's score range across all 9 canonical models is 0.017
(everyone at or near ceiling, 0.98-1.00), while L4's is 0.366. Including
L1 in a tier-gradient correlation risks the correlation being dominated by
tie-heavy, near-zero-variance rows at the easy end. **Decision: report
both an all-tier (L1-L4) and an L2-L4 reading, side by side, for every
model and pooled**, not picking one, since the all-tier reading is the
literal, full-scope answer to "across the four CC tiers" (RQ2's
wording) while L2-L4 is the sensitivity check that isolates whether the
near-ceiling tier is doing the work. This mirrors how Comparison A already
handles the analogous tier-composition question (reporting Dynamic-L4-only
alongside pooled, `analysis/RQ5_DIAGNOSTICS.md` sec 1), applying a
known, already-disclosed lesson proactively, not discovering the
same distortion again after the fact.

## Conditioning convention

**`mutation_score` rows only where `baseline_passed=True`**, the same
exclude/conditional convention used as this project's pre-registered
primary everywhere else (`analysis/METRICS_AND_FINDINGS_EXPLAINED.md` §2).
A row that never reached the mutation-scoring stage contributes nothing to
either estimand. It is not zero-filled. This means each model's H3
correlation is computed over a self-selected, baseline-passing subset.
The same conditioning/survivorship caveat already extensively documented
for Mut@K generally applies here too and will be stated in the write-up,
not treated as a new discovery specific to H3.

## Coverage-adjusted companion — decided in advance

`coverage_adjusted` (Mut@K × baseline_pass_rate) is an aggregate quantity
(a product of two per-model-per-scope means), not a per-row value. It
cannot be attached to an individual problem row the way raw
`mutation_score` can, so the **primary problem-level correlation uses raw
conditional Mut@K only**. The tier-MEAN supplementary row (see estimands
above) DOES get a coverage-adjusted companion, since it's
computed at the per-tier-aggregate level where `coverage_adjusted` is
well-defined (mean Mut@K for that model×tier × that model×tier's
baseline_pass_rate). Both the raw and coverage-adjusted tier-mean rows are
reported side by side, same discipline as everywhere else, never one
without the other, and both explicitly labelled low-power (n≤4).

## Incomplete tier coverage — how it's handled, decided in advance

Checked directly against real data before writing this plan (not assumed):
**7 of 9 canonical models have baseline-passing rows at all 4 tiers**
(gpt-5, gpt-5-mini, claude-sonnet, claude-haiku, gemini-flash-lite, Qwen
32B, Qwen 7B, though Qwen 32B's L4 n_defined=13 and Qwen 7B's L4 n_defined=1 are
individually thin by this project's `n_defined<20` convention).
**2 of 9 have zero baseline-passing L4 rows**: Gemini 3.1 Pro Preview
(L1 n_defined=249, L2 n_defined=102, L3 n_defined=159, L4 n_defined=0, the already-documented Dynamic-L4
quota gap, `analysis/METRICS_AND_FINDINGS_EXPLAINED.md`'s "Gemini-Pro-has-
no-L4" section) and Qwen 2.5-Coder-1.5B-Instruct (L1 n_defined=12, L2 n_defined=64, L3
n_defined=2, L4 n_defined=0, a genuine floor effect, this model cannot clear the CC≥8
baseline gate).

**Decision**: compute each model's per-model correlation over whatever
tiers it has defined rows for. **Never drop these two models
entirely, never impute a value for the missing tier**. For the "all-tier"
reading, their correlation is reported as computed over L1-L3 only, with
an explicit flag (`tiers_available` column), not a silent 4-tier
claim. For the "L2-L4" reading, these two models reduce further to L2-L3
only (2 tiers), flagged as **too low-resolution to report a meaningful
rank correlation** (Spearman across 2 different tier values is barely
defined), not computed and quoted anyway. Their row in that table
reports "insufficient tier range," not a number. Qwen 1.5B's L3
row (n_defined=2) is separately thin at the row-count level regardless of tier
range, flagged in the per-model output, not silently included as an
equally reliable data point.

## Multiple-comparisons correction — decided in advance

Two separate Holm-Bonferroni families, mirroring the N=4-vs-all-pairs
split already applied to RQ4/H5 (`analysis/STABILITY.md`): **(1)** the 9
models' all-tier p-values, corrected as one family of ≤9 (fewer if a
model's correlation can't be computed); **(2)** the 9 models' L2-L4
p-values, corrected as a separate family of ≤9. The pooled estimand's
p-value (one number per tier-scope) is not part of either per-model
family. A family of one is a documented no-op, same treatment as RQ1's
H2 (`analysis/COMPARISON_A_INTERPRETATION.md`'s Holm section). The
low-power tier-mean supplementary rows are not included in either
corrected family (already labelled as not to be read via a significance
threshold, per the ceiling-effect section above).

## What gets built next

Once this plan is committed: a new script (working name
`scripts/analyze_h3_tier_gradient.py`) computing exactly the estimands
above from `data/results/dynamic/*.jsonl` (already on disk, no new
generation), writing `analysis/rq5_h3_tier_gradient.csv` and
`analysis/H3_TIER_GRADIENT_PROVENANCE.md` (raw tables, auto-generated,
same split as every other RQ in this project), with a hand-written
`analysis/H3_INTERPRETATION.md` once results exist.
