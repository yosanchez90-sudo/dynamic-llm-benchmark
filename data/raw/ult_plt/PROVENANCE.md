# ULT / PLT provenance

- **Source:** https://github.com/huangd1999/UnLeakedTestBench (MIT licensed)
- **Paper:** "Benchmarking LLMs for Unit Test Generation from Real-World Functions",
  Huang & Du et al., ACM TOSEM / arXiv:2508.00408.
- **Fetched:** 2026-07-08, from commit `d992b2d95ff0bececa90bfccd1ea683a3a2bea18`
  (2026-02-04) via `git clone --depth 1`.
- **Files:** `ULT.jsonl` (3,909 records — matches the paper exactly), `PLT.jsonl`
  (18,310 records; paper text says "18,169" — the live repo doesn't match the
  paper's own count exactly, treat 18,310 as ground truth since it's what's
  actually here). `ULT_Lite.jsonl` (200-record sample) was NOT vendored — not
  needed since the full files are cheap to store (`data/` is gitignored).

## Known discrepancy — flagged, not resolved here

The repo's README states (Data Preservation Notice): *"we do not release the
ground-truth tests[...] to prevent test case leakage into future LLM training
sets."* This is **not actually true of the files as committed** — `ULT.jsonl`
contains a `tests` field (5 pytest-style assertions per function) and
`ULT_Lite.jsonl` contains `test_list`. Only `PLT.jsonl`'s `test_input` field
lacks real assertions (bare call expressions only).

**Decision (2026-07-08, confirmed with the user):** this project's loader
(`src/data/ult_plt.py`) does not read or use `tests`/`test_input`/`test_list`
at all — Exec@K/Cov/Mut@K only need `code` (the reference implementation) plus
this project's own mutation engine, exactly as for the Dynamic benchmark. The
ground-truth-tests-present-despite-notice discrepancy is worth a line to the
supervisor before citing ULT/PLT results, but doesn't block the pipeline.

## Ground-truth `tests` quality — found 2026-07-25, building Comparison C training data

The above discrepancy became directly load-bearing once the 2026-07-25 supervisor
meeting approved the canonical Comparison C design (fine-tune Qwen-1.5B on ULT,
PROJECT_BRIEF.md Sec 11): that design uses ULT's shipped `tests` field as the
fine-tune's training TARGET, so its internal correctness now matters, not just its
presence.

**Checked empirically (`scripts/check_ult_ground_truth_baseline.py`, SLURM job
9488064, k2-medpri, 2026-07-25): only 253/2,986 (8.5%) of CC>=8-filtered ULT
records have ALL 5 shipped `tests` pass when run directly against the record's own
`code` field.** 91.5% fail at least one assertion, raise, or (rarely) time out.
Breakdown of the 2,733 failing records' first error (`analysis/ult_ground_truth_baseline.csv`
has the per-record detail):

| Cause | Count | % of failures |
|---|---|---|
| AssertionError (code runs, shipped expected value is wrong) | 1,807 | 66.6% |
| NameError (usually a top-level import the original source file had, dropped when ULT extracted just the target function/helpers) | 615 | 22.7% |
| TypeError / AttributeError / IndexError / KeyError / ValueError / StopIteration / other runtime error | 273 | 10.1% |
| Timeout (3s cap) / code itself doesn't exec / other | 18 | 0.7% |

This is **not** an artifact of this project's loader or of
`scripts/build_ult_training_pairs.py`'s test-file construction (verified: the
`from under_test import ...` header correctly includes every helper name a test
body references — the NameErrors are for names `code` never defines at all, e.g.
a bare `random.shuffle(...)` call with no `import random` anywhere in the vendored
snippet). It is a property of the vendored ULT.jsonl data itself: `code` is an
isolated function (+ occasionally its helper classes) lifted out of a real source
file, without that file's own top-level imports, and a nontrivial fraction of the
shipped `tests` were seemingly written against a different version of the function
than the one shipped in `code`, or exercise inputs the shipped implementation
doesn't handle as the test expects.

**Consequence for Comparison C's causal design, flagged not resolved here:** this
project's own `baseline_passed` gate (a suite must pass on the original code before
Mut@K is scored — src/eval/test_gen_scorer.py) would already exclude these same
2,733 records if a MODEL produced this exact test file at eval time. If the
canonical fine-tune trains on the raw, unfiltered `tests` field for all ~3,676
records, the 91.5% majority of memorized targets would still fail `baseline_passed`
post-fine-tune even under perfect memorization — capping, not just denting, the
expected "large ULT gain" (PROJECT_BRIEF.md Sec 7). Filtering training data down to
only the 253 internally-consistent records instead preserves per-example validity
but only contains 26/400 (6.5%) of the core_400 ULT evaluation problems — breaking
the "core_400 guaranteed seen-in-training" property the full-effective-ULT scope
was chosen for.

## Repair pipeline — decided 2026-07-25, still short of the 90% core_400 target

User's decision on the finding above: repair `tests` to be self-consistent rather
than use as-shipped or filter-to-clean-only (see options weighed at the time in
session record; not reproduced here). Constraint set alongside that decision: never
touch `code` itself, because PRE-fine-tune baselines already landed against the
unrepaired `code` (Part 1 item 3, "PRE baselines — reuse, don't re-run... same eval
config as post, or the DiD is invalid") — repairing a record whose *code* needs a
missing import to run at all would silently diverge POST's eval config from PRE's
for that record, regardless of what the model learns. Only the assertion's
recorded expected VALUE may be corrected; `code` stays byte-identical to what PRE
already measured.

**Pipeline** (`scripts/repair_ult_ground_truth.py`, SLURM jobs 9488135 [crashed,
see below] / 9488141 [completed], k2-medpri, 16 workers): every harness call goes
through the real scoring primitives (`src/eval/test_gen_scorer.py`'s
`_write_case`/`_collect_ok`/`_run_pytest` — real subprocess + pytest +
`--import-mode=importlib`, not an ad hoc in-process check), so a "pass" here means
the same thing a "pass" means at actual eval time.

1. **Taxonomy** — run each record's (code, shipped-tests) pair once; failing
   records re-run once more to catch flakiness (unseeded randomness/wall-clock
   dependence); the rest classified by exception type.
2. **Repair** (ASSERTION_MISMATCH only, i.e. code runs cleanly, an expected value
   is wrong) — for the common ULT shape `def test_x(): assert <call-expr> ==
   <literal>` (single statement), re-evaluate `<call-expr>` against the
   *unmodified* code and rewrite the literal to match. Any test whose shape isn't
   exactly one such statement is left alone, not guessed at.
3. **Verify** — every repaired test file is re-scored through the same real
   harness; only `baseline_passed=True` outcomes enter the training set. This
   caught a real bug in step 2 (below) rather than silently shipping it.

**Final taxonomy, n=2,986 CC>=8 records with parseable code+tests** (690 further
CC>=8 records were dropped before this stage — `code` or one of the 5 shipped
tests itself doesn't parse as Python; not attempted here):

| Category | Count | % |
|---|---|---|
| CLEAN (already passed, no repair needed) | 251 | 8.4% |
| ASSERTION_MISMATCH_REPAIRED_VERIFIED | 602 | 20.2% |
| ASSERTION_MISMATCH_REPAIRED_DEGENERATE (repaired, verified, but the 5 repaired expected-values are all identical — see caveat below) | 164 | 5.5% |
| ASSERTION_MISMATCH_VERIFY_FAILED (repair attempted, didn't verify) | 9 | 0.3% |
| SHAPE_NOT_REPAIRABLE (not a single `assert x == y` statement) | 927 | 31.0% |
| STRUCTURAL (code itself can't run cleanly — missing import, etc.) | 1,031 | 34.5% |
| FLAKY | 2 | 0.1% |

**Final verified training set: 1,017 records** (CLEAN + REPAIRED_VERIFIED +
REPAIRED_DEGENERATE) → `data/finetune/train_ult_repaired.jsonl`. Full per-record
detail: `analysis/ult_ground_truth_taxonomy.csv`.

**Fine-tune-readiness filter (2026-07-26, preparing STOP GATE B):**
`scripts/finalize_ult_training_set.py` tokenizes all 1,017 pairs with the actual
target-model tokenizer — 3 ULT `code` blobs are enormous outliers (max ~116k
tokens; one, ULT-11221 at 66,627 tokens, exceeds even Qwen2.5-Coder-1.5B's own
32,768-token position-embedding limit). `max_length=3072` would silently truncate
these mid-`code`, before the sequence ever reaches the assistant's test-file
target — a wasted training step with zero actual learning signal, not a harmless
truncation. Dropped (ULT-10024, ULT-11221, ULT-14284; none were in the core_400
seen set, so the 112/400 figure above is unaffected) →
`data/finetune/train_ult_final.jsonl` (1,014 records), the file
`configs/finetune_qwen1_5b_ult_30ep.yaml` actually points at. Surviving
distribution: mean 940 tokens, p99 1,987 — comfortably under 3,072 for the
remainder.

**core_400 coverage: 112/400 (28.0%)** of the ULT evaluation problems have a
verified seen-in-training pair — well short of the ~90% target. Ceiling analysis:
STRUCTURAL (34.5%) is a hard floor under the no-touching-`code` constraint above,
so even a hypothetically perfect repair of every SHAPE_NOT_REPAIRABLE record could
reach at most (2986-1031)/2986 = 65.5% of the parseable pool, i.e. ~53.2% of the
full effective-ULT (3,676) — **90% core_400 coverage is not achievable within this
design's constraints, not just not-yet-achieved.** This is now itself a reportable
methodological finding (real-world scraped-benchmark ground truth is largely
internally inconsistent even for the dataset's own answers), not only a blocker —
flagged for the user/supervisor before proceeding past this point.

**Degenerate-repair caveat:** verify-via-scorer only checks internal consistency
(does the function, called this way, return the claimed value) — it can't check
that the value is a *meaningful* exercise of the function. A minority of repaired
records (164, the DEGENERATE bucket) come back with the same repaired value across
all 5 of ULT's differently-parameterised test cases, typically because the
function silently swallows an exception (e.g. a missing test-fixture file inside
this sandbox) and returns `None` regardless of input. These are flagged, not
excluded, and are individually inspectable via `source: "ult_ground_truth_repaired_degenerate"`
in the training JSONL.

**Bug found and fixed during the first full run (job 9488135, crashed):**
`repair_test()` blindly embedded `repr(actual)` as a source-code literal — invalid
for any type without a literal repr (an Enum member reprs as `<Matches.BothSame:
5>`, not valid Python syntax to re-embed; ULT-2453's `classify_match` hit this
exactly). The crash lost the entire partial run's output since results were only
written at the end. Fixed by (a) validating the candidate repaired source
re-parses before accepting it — falls through to SHAPE_NOT_REPAIRABLE instead of
crashing — and (b) switching to incremental, flushed-per-record writes so a future
edge case can't erase completed work. See `scripts/repair_ult_ground_truth.py`'s
module docstring and commit `2c5a2c3`.

## Tier / CC scoping — confirmed with the user (2026-07-08)

- ULT is CC-filtered by its own authors to **CC >= 10 exclusively** (min 10,
  max 82, mean 14.87 — **this is the paper/vendor's own claimed CC field**,
  not this project's recomputed value; see `tests/test_ult_plt_loader.py`'s
  note on why the vendored `cyclomatic_complexity` field is never trusted).
  This project's own AST-based `compute_cc()`, scoped to the target function
  only (via `cc_lookup()`), finds ULT's *actual* range is min **1**, mean
  13.93 — i.e. ~233/3909 (6%) of ULT records fall **below** this project's
  own CC_MIN=8 threshold and are dropped by `load()`. The "zero functions
  comparable to L1/L2/L3" framing above describes the vendor's own filter,
  not a guarantee this project's independently-recomputed CC agrees with it
  for every record — it doesn't, for that ~6%. This does not affect
  correctness: `load()` filters on its OWN recomputed CC, not the vendor
  field, so every record that reaches a model is genuinely CC>=8 regardless
  of what the vendor claims. (Verified 2026-07-13 via `cc_lookup()` — see
  `logs/verify-ult-plt-counts-9372877.out` for the exact drop counts: ULT
  3909->3676 kept, PLT 18310->13719 kept excl. ULT overlap.)
  Post-filter (CC>=8), ULT's recomputed quartiles are [8, 10, 12, 16, 82]
  and PLT (excl. ULT overlap)'s are [8, 10, 12, 16, 1729] — near-identical
  up to the extreme tail, which is what makes CC-quartile stratification a
  fair "matched CC" comparison between the two (see subsample_manifest.json
  section below). PLT is broader (~89-96% CC>=8-10, sampled).
- Comparison A/B against ULT/PLT are therefore **inherently L4-only**
  (`tier="L4"` for every loaded record, matching this project's CC>=8 band),
  sub-stratified by ULT/PLT's own CC spread for finer-grained analysis
  (see `src/Analysis` for the CC-band helper — computed at analysis time from
  `cc_lookup()`, not stored on the tidy record, matching how Dynamic sources
  are reconstructed on demand rather than stored redundantly).
- PLT records with CC < 8 are dropped by the loader (~4-11% of PLT, sampled)
  to keep ULT/PLT comparable on the same tier band.
- **ULT's 3,909 task_ids are a 100% subset of PLT's 18,310** (confirmed by
  direct ID overlap, not by trusting the paper's prose). For a fair
  Comparison B (ULT vs PLT), use PLT *excluding* ULT's own task_ids —
  otherwise the comparison is partly circular. `src/data/ult_plt.py`'s PLT
  loader excludes ULT's task_ids by default (`exclude_ult_overlap=True`).

## Mutation-engine correctness note

~19% of ULT / ~7% of PLT `code` fields include helper classes/functions
before the target function (the target still needs them to run). This
project's mutation engine (`template_corpus/templates/_smoke/mutator.py`)
originally mutated the *whole* parsed module, not just the target function —
harmless for the Dynamic benchmark (always single-function), but would have
polluted ULT/PLT mutants with mutations inside unrelated helper code. Fixed
by adding an optional `scope_fn_name` parameter (2026-07-08) that restricts
mutation candidate search to the named function; the ULT/PLT loader always
passes it.

## Canonical evaluation subsamples — `subsample_manifest.json` (2026-07-13)

Generated by `scripts/generate_ult_plt_subsample.py` (SLURM job 9374197,
k2-medpri). Two nested, fixed, CC-stratified (seed=42) tags, each with an
`ult` and `plt` block:

- **`core_400`** — 400-ULT + 400-PLT (excl. ULT overlap). The universal
  paired set: every closed-source model (Claude Sonnet/Haiku, Gemini
  Pro/Flash, GPT-5/-5-mini) AND Qwen's first pass (1.5B/7B/32B) all evaluate
  exactly this set, so per-problem paired comparisons (H1 Wilcoxon, RQ4
  Kendall tau) are computed over identical problems across all 9 models.
- **`qwen_1000`** — 1000-ULT + 1000-PLT, a **strict superset of `core_400`**
  (containment guaranteed by construction — `core_400`'s records are
  force-included, then topped up via CC-stratified sampling on the
  remainder — and asserted, not assumed, before the manifest is written).
  Qwen-only; the `qwen_1000 minus core_400` extension (600/bench) serves the
  within-L4 CC-gradient analysis (H4b) and is **deferred** behind the P4
  coverage-fill critical path.

### Why NOT "full set for local open-source" (deviation from PROJECT_BRIEF.md §9)

The brief's original spec (§9) was full ULT+PLT (~3,676 + ~13,719 problems)
for local Qwen. Projected cost (see `scripts/estimate_cost.py`-style
projection from measured L1 latency + GPT-5's real per-tier token growth,
2026-07-13): **~500 GPU-hours total** across the three Qwen sizes (1.5B
~112h, 7B ~94h, 32B ~293h) — every size individually exceeds this project's
12h per-submission approval threshold, and 32B needs the already-contended
`k2-gpu-a100`/`k2-gpu-h100` partitions across ~4 sharded 3-day jobs.
Decided (with the user) to scope down instead:

  (a) every cross-model statistical test is already capped at `core_400`
      (closed-source models cannot exceed N=400/bench), so full-set Qwen
      data would be inadmissible for the headline cross-model comparisons
      (H1, RQ4) regardless;
  (b) N=400 paired gives SE ≈ 0.025 on mutation-score metrics — adequate for
      the expected contamination-inflation deltas;
  (c) local GPU budget is queue-bound (shared partitions, 3-day wall-clock
      cap/job) and reserved for the P4 coverage-fill critical path first;
  (d) `qwen_1000` covers the one analysis (H4b, within-L4 CC gradient) that
      genuinely benefits from more open-source-only data, at a fraction of
      the full-set cost.

`core_400` Qwen runs (1.5B/7B/32B on both ULT and PLT) are in scope now; the
`qwen_1000` extension is queued after P4 coverage-fill, Qwen-only, low
priority.
