# ULT/PLT data-quality audit

**Purpose and framing.** This document consolidates three independent
findings about the published ULT/PLT dataset (Huang & Du et al.,
arXiv:2508.00408, the static benchmark this project uses as its main
comparator), discovered separately across this project's work and
brought together here for one reason: read together, they are a
consistent, multi-angle picture of an artifact whose self-reported data
quality is measurably lower than a user of the published paper alone
would assume. **This is written as an audit of a published research
artifact, not as an attack on it or its authors.** Mutation testing,
CC computation, and mutation-score definitions are all genuinely
ambiguous/hard problems, ULT is a real and useful contribution, and every
finding below is stated with its evidence and method so it can be
checked or disputed on its own terms. **Flagged for supervisor review
before any of this is cited externally** (e.g. in a related-work
discussion, an email to the ULT authors, or a public write-up). These are
this project's own measurements against a third party's published
artifact, and deserve a second pair of eyes before that step.

## Finding 1 — ULT's shipped ground-truth tests mostly do not pass against ULT's shipped code

**Evidence**: `data/raw/ult_plt/PROVENANCE.md`, `scripts/
check_ult_ground_truth_baseline.py` (SLURM job 9488064) and
`scripts/repair_ult_ground_truth.py` (SLURM job 9488141). Of 2,986 CC≥8
ULT records with parseable `code` and `tests` fields, only **251 (8.4%)**
passed cleanly with no modification, checked via this project's own
real scoring harness (`test_gen_scorer.py`'s `_write_case`/`_collect_ok`/
`_run_pytest`, a genuine subprocess+pytest run, not an ad hoc in-process
check). An earlier, independent check
(`check_ult_ground_truth_baseline.py`) found a near-identical **253/2,986
(8.5%)** using the same method. The 2-record difference between the two
counts is not reconciled in this project's records and should be read as
noise at this sample size, not as evidence either figure is wrong.

Full breakdown of the remaining 91.6%:

| Category | Count | % | Meaning |
|---|---|---|---|
| CLEAN (no repair needed) | 251 | 8.4% | Passes as shipped. |
| ASSERTION_MISMATCH_REPAIRED_VERIFIED | 602 | 20.2% | Code runs; the shipped expected value was wrong; repaired and re-verified through the real harness. |
| ASSERTION_MISMATCH_REPAIRED_DEGENERATE | 164 | 5.5% | Repaired and verified, but all 5 of the record's tests ended up asserting the *same* repaired value, a weaker test than the un-degenerate repairs. |
| ASSERTION_MISMATCH_VERIFY_FAILED | 9 | 0.3% | Repair attempted, did not verify. |
| SHAPE_NOT_REPAIRABLE | 927 | 31.0% | Runs, but the shipped test isn't a single `assert x == y` statement this project's repair pipeline can safely rewrite. |
| STRUCTURAL | 1,031 | 34.5% | The shipped `code` cannot run (e.g. a missing import). |
| FLAKY | 2 | 0.1% | Non-deterministic outcome across two runs. |

**Method note**: the repair pipeline only ever rewrites the *expected
value* in a matched `assert <call-expr> == <literal>` shape, and only for
`ASSERTION_MISMATCH` records (code runs cleanly). `code`
is never touched, and no record outside the `assert x == y` shape is
guessed at. "Repaired" therefore means "the ground truth's stated
expected value was wrong, not that the function was suspect."

**Why this matters beyond ULT's quality**: it explains this
project's Comparison C finding that even 100%-verbatim reproduction of
ULT's ground-truth tests only reaches Mut@K≈0.438
(`analysis/COMPARISON_C_INTERPRETATION.md`). Perfect memorisation of a
mediocre test suite is still a mediocre test suite, a ceiling inherited
from ULT's data, not a fine-tuning artifact.

## Finding 2 — ULT's self-reported cyclomatic complexity is unreliable at its stated filter boundary

**Evidence**: `data/raw/ult_plt/PROVENANCE.md` ("Tier / CC scoping"
section), `tests/test_ult_plt_loader.py`, `logs/verify-ult-plt-counts-
9372877.out`. ULT's authors state their benchmark is CC-filtered to
**CC≥10 exclusively** (their own claimed field: min 10, max 82, mean
14.87). This project's own AST-based `compute_cc()`
(scoped to the target function only, via `cc_lookup()`) recomputes CC for
every ULT record independently and finds a materially different
distribution: **min 1** (not 10), mean 13.93 (vendor claims 14.87). **233
of 3,909 ULT records (~6%) fall below this project's own CC≥8 threshold**
despite the vendor's own claimed field asserting every record is CC≥10.
The vendor's self-reported CC field disagrees with an independent
recomputation for about 1 in 17 records, at exactly the boundary that
determines whether a record is usable for this project's CC-matched
comparison.

**This did not silently corrupt any of this project's own results**: this
project's own `load()` filters on its *own* recomputed CC, never on the
vendor's claimed field (`tests/test_ult_plt_loader.py`'s explicit note on
why the vendored `cyclomatic_complexity` field is never trusted). So
every ULT/PLT record that reaches a model in this project is genuinely
CC≥8 by independent, first-party measurement, regardless of what ULT's
own metadata claims. The 233/3,909 records are dropped, not scored
incorrectly. Post-filter, this project's own recomputed CC quartiles for
ULT are `[8, 10, 12, 16, 82]`, broadly consistent with the vendor's
claimed range at the middle of the distribution, diverging at
the low tail the vendor's filter was supposed to exclude entirely.

**Why this matters**: it's independent, converging evidence (alongside
Finding 1) that ULT's own published metadata should not be taken at face
value without a first-party recomputation. This project does
that recomputation for both CC and ground-truth pass/fail, but a reader of
the ULT paper alone, relying on its self-reported filter, would not know
~6% of records at the CC≥10 boundary don't actually meet that bar under an
independent AST-based measurement.

## Finding 3 — the paper's stated mutation-score formula contradicts its own published implementation

**Evidence**: `analysis/RQ5_CROSS_DEFINITION_AUDIT.md` (full verbatim
quotes and code excerpts, summarised here). The paper's Section 3.4.3
prose states `Mut@k = Σ Mi / N` with **N explicitly defined as "the total
number of functions in the benchmark"**. Read literally, this describes
an INCLUDE-AS-ZERO (unconditional) mean: every function counts in the
denominator, including ones whose test suite never passed. The
paper's own published code
(`github.com/huangd1999/UnLeakedTestBench`,
`Ray/main.py::mutation_statistic()`, the function actually invoked from
that repository's CLI) instead computes
`surviving_mutants_rate = sum(per-task rate) / len(correct_tasks)`, where
`correct_tasks` is the set of tasks whose *baseline* (unmutated) run
passed, an EXCLUDE (conditional) mean, with no zero-filling anywhere,
the same estimand as this project's own pre-registered primary Mut@K
definition.

**This is reported as a genuine, unresolved contradiction, not resolved by
picking a side**: the paper's prose and its own code describe two
different statistics, and this project's reading of "which one is
authoritative" is necessarily a judgement call (code is arguably stronger
evidence of what was actually measured; prose is what a reader
replicating from the paper's text alone, without consulting the code,
would implement). Full reasoning is in `RQ5_CROSS_DEFINITION_AUDIT.md`
§2. Separately, the paper's stated "percentage of non-equivalent mutants"
is not implemented anywhere in the published code (no equivalent-mutant
detection or filtering was found in any of `Ray/main.py`,
`Ray/generate_mutation_details.py`, or `Ray/result_exporter.py`). "Surviving"
mutants are whatever Cosmic Ray reports as not-killed, undifferentiated
by equivalence, despite the prose's "non-equivalent" qualifier.

**Why this matters**: any published Mut@k figure from this paper (e.g.
its own reported ~40.21% average) cannot be assumed to mean the same
thing as a reader's own re-implementation from the paper's stated
formula. The two estimands, applied to identical data, produce
materially different numbers (this project's own `coverage_adjusted` vs
conditional Mut@K, `RQ5_CROSS_DEFINITION_AUDIT.md` §3, diverge by up to an
order of magnitude for models with low baseline-pass rates).

## Reading the three findings together

Each finding was discovered independently, through unrelated work (a
fine-tuning training-data preparation step; a loader/tier-scoping
sanity check; a metric-definition reconciliation prompted by external
review). They were not gathered as part of a deliberate search for
problems with ULT. That they converge on the same picture (the
published artifact's metadata and stated methodology are less reliable
than the paper alone would suggest, in three unrelated dimensions: test
correctness, complexity measurement, and metric definition) is worth
stating plainly, without overstating it into a broader claim this
project has not verified (e.g. this audit says nothing about ULT's
actual usefulness as a decontamination protocol, its complexity-filtering
methodology's soundness, or any of its other reported results).

## Recommendation

**Do not cite any of the three findings externally (e.g. to the ULT
authors, in a public write-up, in related-work framing) before supervisor
review.** All three are checkable independently from this project's
scripts and raw data (cited above per finding). The recommendation is
about review before external use, not about confidence in the findings
themselves, which are reproducible from files in this repository.
