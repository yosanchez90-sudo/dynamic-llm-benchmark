# Metrics and findings, explained

**Purpose of this document.** A single, self-contained reference for anyone
who understands software testing but has never seen this project — how a
model response turns into a number, what every reported metric actually
means, why the sample size changes between tables, what the findings are
and how strong each one really is, what the data does *not* support, and a
full accounting of every measurement bug found and fixed along the way.
Written for explaining the work end to end, not as a quick-reference card —
favours completeness over brevity throughout.

Hand-written, not auto-generated, but every number in it is either quoted
from an auto-generated table (cited by file) or computed live from raw
result files while writing this (also cited). Treat any specific point
estimate as current-as-of 2026-08-10 (refreshed for the 2026-08-07/08 data
landing — GPT-5/GPT-5-mini's ULT/PLT batches submitted and scored, Claude
Sonnet/Haiku inst5 completed, Gemini Pro Preview's Dynamic-L4 crawl
partially landed); re-check the cited source before quoting it in the
dissertation itself, since several of these numbers have already moved
more than once as bugs were found or data landed (§6 documents this
explicitly).

---

## 1. The measurement chain

### Stage -1 — the task as actually posed (added 2026-08-05, settling a prompt-content question definitively)

Before any scoring happens, it matters exactly what the model was shown.
Quoted **verbatim** from `src/data/test_gen.py`, the single builder every
problem in this project — Dynamic and ULT/PLT alike — goes through:

```python
SYSTEM_INSTRUCTION = (
    "You are an expert Python developer writing a pytest test suite. "
    "You are given a Python function. "
    "Write a complete pytest test file that thoroughly tests this function, "
    "covering normal cases, edge cases, and boundary conditions. "
    "IMPORTANT: you must import the function under test with exactly "
    "`from under_test import <function_name>` — do NOT copy, redefine, or "
    "reimplement the function in your test file. "
    "Output only the test file, starting with the import statement."
)

def _build_messages(source, prompting_condition, supports_system_role=True):
    user = f"Function under test:\n\n```python\n{source}\n```\n\nWrite the pytest test file."
    ...
```

`source` is the **full function body** — for Dynamic, the complete
rendered implementation (docstring, control flow, `return`, everything —
see the `sum_values` worked example in Stage 2 below); for ULT/PLT,
`r["code"]`, the complete shipped implementation from the raw dataset. **This
is a "generate tests for this implementation" design, not a "generate
tests from this specification" one** — the model is never asked to write
tests from a signature-plus-docstring alone; it always sees, and can read,
the real control flow it's being asked to exercise.

**ULT/PLT poses the task identically to Dynamic, confirmed by code, not
assumed**: `src/data/ult_plt.py` imports `_build_messages` directly from
`src/data/test_gen.py` (its own import comment: `# identical prompting to
Dynamic`) and calls it the same way, `source = r["code"]` in place of a
template-rendered function. Same system instruction, same user-message
template, same full-body framing, same import-line requirement. The two
benchmarks differ in **where the function came from** (a parameterised
template vs. real, scraped code) and in the CC/complexity distribution
that follows from that — not in how the task is posed to the model. This
is a load-bearing fact for Comparison A specifically: its comparability
claim (Dynamic-L4 vs ULT, same model, same prompting structure) depends on
this, and it now has a direct code citation rather than an assumption.

One conditional wrinkle, already documented elsewhere and repeated here
for completeness: `supports_system_role=False`
(`configs/*starcoder2*.yaml`) folds `SYSTEM_INSTRUCTION` into the first
user turn instead of a separate `role="system"` message, for the one
model (StarCoder2-15B-Instruct) whose chat template rejects a system role
outright. The instruction **text** is byte-identical either way — only
its delivery position differs.

Every model response goes through the same three-stage pipeline before it
produces a single number. All three stages live in
`src/eval/test_gen_scorer.py`, and the stages are strictly sequential — a
response that fails stage 1 never reaches stage 2, and a response that
fails stage 2 never reaches stage 3.

### Stage 0 (before scoring): extraction and repair

**`extract_test_file()`** (`test_gen_scorer.py:91-101`) pulls a pytest file
out of the raw model response — prefers a fenced ` ```python ` block, falls
back to scanning for the first `import`/`def` line. This is purely
string-level; nothing is executed yet.

**`sanitize_test_file()`** (`test_gen_scorer.py:104-147`) then applies two
mechanical repairs, in order, and records which ones fired:

1. **Strip any reimplementation of the function under test.** Some models —
   overwhelmingly the smallest, Qwen2.5-Coder-1.5B — write a *second copy*
   of the function inside the test file instead of importing the real one,
   then test their own reimplementation instead of the function actually
   being evaluated. Any top-level `def <fn_name>(...)` block matching the
   target function's name is removed from the test source via `ast.parse`
   + line-range deletion.
2. **Ensure the import line exists.** If `from under_test import <fn_name>`
   is not present anywhere in the test source, it is prepended.

Both repairs are logged into the row's `notes` field
(`src/eval/test_gen_runner.py:266`, `"; ".join(...repairs)`), so any row
that was mechanically repaired is identifiable after the fact — this is
what powers the sanitizer-sensitivity check in §4.

**Real example** (`data/results/ult/Qwen__Qwen2.5-Coder-1.5B-Instruct__ult__zero_shot__instcore_400__20260713T123923.jsonl`,
problem `ULT-12886`, a function called `for_S` that prints a small ASCII
pattern and returns nothing): the model's raw response reimplemented
`for_S()` from scratch, with a signature that doesn't even match the real
one, then wrote assertions that treat its return value as a 2-D indexable
grid:

```python
def for_S():
    for row in range(9):
        ...
        print("*",end=" ")
    ...

@pytest.mark.parametrize('row', range(9))
@pytest.mark.parametrize('col', range(5))
def test_for_S(row, col):
    expected = ...
    assert for_S()[row][col] == expected, ...
```

The sanitizer stripped the fake `for_S` definition and prepended
`from under_test import for_S`; the row's `notes` field records exactly
this: `"suite failed on original; Mut@K excluded; stripped reimplementation
of 'for_S'; prepended 'from under_test import for_S'"`. Even after the
repair the test still fails at the baseline gate (stage 2 below) — the
sanitizer fixes *structural* problems (wrong import, a shadow
reimplementation), not *logical* ones (the test still assumes `for_S`
returns something indexable, which it never did). This is a real,
representative case, not a cherry-picked worst case — it is the shortest of
several dozen rows with this exact repair pattern in the same file.

### Stage 1 — the exec gate: does the suite even collect?

**`_collect_ok()`** (`test_gen_scorer.py:189-201`), called from
`score_problem()` at line 273. Runs `pytest --collect-only` against the
function-under-test plus the (sanitized) test file, in an isolated
temporary directory. This asks one question only: **does the test module
import and does pytest successfully discover its test functions**, with no
tests actually executed. A `SyntaxError`, a missing import, a name
collision, or a collection timeout all fail this gate.

If this gate fails, `score_problem()` returns immediately
(`test_gen_scorer.py:274-277`) with `exec_ok=False`, `baseline_passed=False`,
`mutation_score=None`, and every mutation-related field zeroed — nothing
downstream of this point is even attempted. **What it rejects**: malformed
Python, missing imports the sanitizer didn't catch, and any response so
badly cut off (e.g. by a token limit) that it isn't syntactically valid
Python at all.

### Stage 2 — the baseline gate: does the suite pass against the *real* function?

If (and only if) stage 1 passes, `score_problem()` runs the full suite
(with coverage instrumentation) against the **original, correct**
function-under-test (`test_gen_scorer.py:280-282`). `baseline_passed` is
`True` iff every test in the suite passes against that original
implementation (pytest exit code 0).

**This is a stricter, later condition than the exec gate, and the two are
tracked as separate fields for exactly this reason** — a suite can import
and collect perfectly (`exec_ok=True`) while still failing here because its
assertions encode the *wrong* expected behaviour (the model misunderstood
what the function does). If this gate fails, `score_problem()` again
returns immediately (`test_gen_scorer.py:284-287`), with
`mutation_score=None` and `notes="suite failed on original; Mut@K
excluded"` — no mutant is ever run.

**Worked example — the same problem, two real models, opposite outcomes at
this exact gate.** Dynamic-benchmark template `L3-clamp-seq-001`
(`template_corpus/templates/L3/L3-clamp-seq-001.py`), instance seed 1102.
The instantiated function under test (built by the project's own template
engine, quoted here exactly as shown to both models):

```python
def sum_values(values):
    """Build a list with values clamped within the floor and ceiling, or else unchanged."""
    agg = []
    for sample in values:
        if sample < 8:
            agg.append(8)
        elif sample > 33:
            agg.append(33)
        else:
            agg.append(sample)
    return agg
```

Despite the name (a deliberately generic, non-descriptive identifier — see
the "why the naming is misleading" note below), this function **clamps**
every element of `values` into `[8, 33]`; it does not sum anything.

**Qwen2.5-Coder-1.5B-Instruct's full response** (from
`data/results/dynamic/Qwen__Qwen2.5-Coder-1.5B-Instruct__dynamic__zero_shot__inst1__20260609T221336.jsonl`):

```python
import pytest
from under_test import sum_values

@pytest.mark.parametrize("values, expected", [
    ([10, 25, 40], [10, 25, 40]),
    ([-5, -10, -15], [-5, -10, -15]),
    ([8, 33, 17], [8, 33, 17]),
    ([1, 99, 200], [1, 99, 200]),
    ([100, 200, 300], [8, 33, 33]),
    ([34, 67, 98], [34, 67, 98])
])
def test_sum_values(values, expected):
    assert sum_values(values) == expected
```

This response misunderstands the function entirely — most cases assert the
input is returned **unchanged** even where elements are clearly out of
`[8, 33]` (e.g. `40`, `-15`, `200` all left untouched), and the one case
that does predict clamping (`[100, 200, 300] -> [8, 33, 33]`) gets the
clamped values wrong too (everything above 33 should clamp to `33`, giving
`[33, 33, 33]`, not `[8, 33, 33]`). Result: `exec_rate=1.0` (the file
collects fine — valid Python, correct import) but `baseline_passed=False`
(the assertions fail against the real function), so
`mutation_score=None`, `notes="suite failed on original; Mut@K excluded"`.
This row is **entirely excluded** from this model's Mut@K mean under the
pre-registered definition (§2).

**Claude Sonnet 4.6's full response for the identical problem** (from
`data/results/dynamic/claude-sonnet-4-6__dynamic__zero_shot__inst1__20260714T141018.jsonl`,
abbreviated — 33 test functions in total covering the empty-list case,
both boundaries from both directions, negative values, floats, a
return-type check, and a non-mutation "input not modified" check):

```python
def test_empty_list():
    assert sum_values([]) == []

def test_all_below_floor():
    assert sum_values([1, 2, 3, 4, 5, 6, 7]) == [8, 8, 8, 8, 8, 8, 8]

def test_exactly_at_floor():
    assert sum_values([8]) == [8]

def test_one_below_floor():
    assert sum_values([7]) == [8]

def test_ceiling_boundary_just_above():
    assert sum_values([34]) == [33]

def test_original_list_not_modified():
    original = [1, 15, 50]
    original_copy = original.copy()
    sum_values(original)
    assert original == original_copy
# ... (27 more, same style)
```

`exec_rate=1.0`, `baseline_passed=True` — every one of the 33 assertions
holds against the real function. This row proceeds to Stage 3.

**Why the function is named `sum_values` despite summing nothing**: the
identifier is drawn from `IdentifierBank(role="function_L3")` at template-
instantiation time (`L3-clamp-seq-001.py`'s `parameter_spec`), independent
of what the function actually does. This is deliberate — it is part of the
project's contamination-resistance design (PROJECT_BRIEF.md §5.2's
"variable names, values, constants, and docstring synonyms vary across
instances"): a model that has memorised a "clamp" pattern under a
conventional name (`clamp`, `clip`, `bound`) gets no benefit from that
memorisation when the same logic appears under an unrelated name and a
paraphrased docstring. Qwen 1.5B's failure above is exactly the kind of
result this design is meant to surface honestly rather than mask.

### Stage 3 — mutation scoring: only reached if stages 1 and 2 both passed

`score_problem()` (`test_gen_scorer.py:289-308`) runs the test suite
against every mutant of the function, in parallel (a thread pool — one
worker per mutant, since each worker just coordinates a `subprocess.run`
call). For each mutant, `_evaluate_mutant()` (`test_gen_scorer.py:222-252`)
does:

1. Try `python -c "import under_test"` against the mutated source. If this
   raises or times out, the mutant is **`dropped`** — it never got a fair
   chance to be tested, so it counts in neither the killed nor the
   survived tally.
2. Otherwise run the full suite against the mutant. **`killed`** if the
   suite fails (or times out) against the mutant; **`survived`** if it
   still passes.

For the Sonnet example above: `mutants_total=21`, `mutants_dropped=0`
(every mutant imported cleanly), `mutants_killed=17` — 17 of the 21
syntactic variants of the clamp logic (e.g. `<` swapped for `<=`, `8`
swapped for `9`, the `append` in one branch swapped for a no-op) were
caught by at least one of the 33 tests; 4 survived undetected.
`mutation_score = 17/21 = 0.8095`.

---

## 2. Every metric, defined once

All formulas below use `mutation_score`, `baseline_passed`, `exec_rate`,
`mutants_total`, `mutants_killed`, `mutants_dropped_for_import_failure` —
the per-row fields written by `score_problem()` and read by
`src/Analysis/loader.py::load_records()`.

### `exec_rate` (Exec@K)

**Formula**: 1.0 if the exec gate (§1 Stage 1) passed for this row, else
0.0 (the harness stores it as a rate because some earlier code paths
support K>1 attempts per problem; in this project's actual runs K=1, so it
is effectively a 0/1 indicator per row).
**Conditional on**: nothing — always defined for every row.
**Used in**: reported as a secondary metric alongside coverage; the
project's own docstring for the exec gate calls it "**Gate** (>0 to score
the rest)" (PROJECT_BRIEF.md §5.4).
**Known failure mode**: a high `exec_rate` says only that the response was
syntactically valid, importable Python — it says nothing about whether the
test asserts anything correct (see the Qwen 1.5B example above, which has
`exec_rate=1.0` and is still a complete miss).

### `baseline_pass_rate`

**Formula**: `n_defined / n_total` per model/benchmark/tier, where
`n_defined` = count of rows with `mutation_score is not None` and
`n_total` = count of all attempted rows. This equals the fraction of rows
with `baseline_passed=True` **exactly**, by construction of
`score_problem()` (`mutation_score` is `None` iff `baseline_passed=False`,
or — see the next entry — a rarer edge case) — computed this way (via
`n_defined/n_total`) rather than from a separate `baseline_passed` column
average because it's the same invariant `src/Analysis/stability.py`'s
coverage adjustment relies on (`comparison.py:75-85`'s docstring makes this
explicit).
**Conditional on**: nothing beyond the exec gate already having been
attempted.
**Used in**: the `coverage_adjusted` metric below; the conditioning/
survivorship diagnosis in §4; every "n_defined" column in the tables in §3.
**Known failure mode**: varies enormously between models (2.0% for Qwen
1.5B on ULT to 96.3% for GPT-5 on Dynamic-L4, updated 2026-08-10 — Gemini
Pro Preview's Dynamic-L4 slice is nominally higher still at 97.3%, but
from only 38 rows so far, its own partial-crawl caveat below, so GPT-5's
figure is the more robust "well-established high" example) — a model
with a very low baseline-pass rate has almost no rows contributing to its
own Mut@K mean, making that mean a shaky point estimate even when it
looks like a respectably high number (§4's thin-cell discussion).

### Mut@K — **two definitions, reconciled 2026-08-03**

This project computes Mut@K one way; the paper this project's ULT/PLT
benchmark is drawn from (Huang & Du et al., arXiv:2508.00408) states a
formula that, read literally, describes a different way — and, as of this
document's writing, that paper's *own published code* implements a third
thing again (which happens to match this project's own choice). Full
verbatim evidence and the algebraic proof live in
`analysis/RQ5_CROSS_DEFINITION_AUDIT.md`; the summary needed here:

**(a) This project's pre-registered primary — EXCLUDE / conditional mean.**

```
Mut@K = mean( mutation_score_i  for all i where baseline_passed_i = True )
      = mean( killed_i / scored_i )                over baseline-passing rows only
```

where `scored_i = mutants_total_i - mutants_dropped_i` for row `i`. Rows
that never reach Stage 3 (§1) are **excluded from the mean entirely**, not
counted as zero. This is what "Mut@K" means everywhere in this project
unless explicitly labelled otherwise (`test_gen_scorer.py:21-25`).
**Conditional on**: `baseline_passed=True`. **Used in**: the pre-registered
headline metric for Comparison A/B, RQ5's primary correlations, H1's
Wilcoxon test. **Known failure mode**: two models with very different
`baseline_pass_rate` are averaged over *different-sized, self-selected*
subsets of problems — a model that only ever produces a passing suite for
the 5 easiest problems in the benchmark can still show a high Mut@K, because
the mean never sees the problems it failed on. This is the single largest
source of the RQ5 diagnosis in §4.

**(b) The "definition-matched" co-primary — INCLUDE-AS-ZERO / unconditional
mean, i.e. `coverage_adjusted`.** See next entry — proven identical to
this, both algebraically and to floating-point precision on this project's
actual data.

### `coverage_adjusted`

**Formula**: `coverage_adjusted = Mut@K(a) × baseline_pass_rate`, computed
per model/benchmark/tier.
**Proven** (`analysis/RQ5_CROSS_DEFINITION_AUDIT.md` §3) to be **exactly**
the zero-filled unconditional mean — `mean(mutation_score_i, with 0
substituted for every row where it's None)` — because in every one of this
project's model×benchmark cells, the count of baseline-passing rows equals
the count of rows with a defined `mutation_score` (i.e., there is no row
where the baseline passed but zero mutants were scorable). Verified via two
independently-coded computation paths agreeing to 5.55e-17 (floating-point
noise). It is *this project's* best-effort match to the ULT/PLT paper's
stated Mut@k **formula** (its prose says the denominator is "the total
number of functions in the benchmark") — but that paper's own **code**
divides by the baseline-passing count instead (the same estimand as this
project's definition (a)), so `coverage_adjusted` should not be read as
reproducing what the ULT paper's authors actually computed, only what
their formula, taken literally, describes.
**Conditional on**: nothing (defined for every row with `n_total > 0`) —
this is the practical advantage of this metric over raw Mut@K: it is never
a "thin" estimate in the way (a) can be, because its own precision is
governed by `n_total` (typically 300-400), not `n_defined` (which can be
as low as 1).
**Used in**: reported as a co-primary alongside Mut@K throughout
Comparison A/B (`analysis/COMPARISON_PROVENANCE.md`) and as one of RQ5's
two headline correlation readings (τ=0.944 canonical, updated 2026-08-07
from 0.905, §4).
**Known failure mode**: it is a *product* of two different signals
("does the model clear the baseline-pass bar at all" and "how good are the
tests that already passed") collapsed into one number — a high
`coverage_adjusted` score does not tell you which of the two is driving it,
and §4's diagnosis shows that for this project's data, almost all of its
cross-benchmark agreement comes from the first signal (baseline-pass rate),
not the second (mutation-kill quality).

### `StableMut@K`

**Formula** (`src/Analysis/stability.py::stable_mut_at_k`): for one model,
compute Mut@K separately per instantiation (definition (a) above, or
optionally the coverage-adjusted variant — `coverage_adjust=True`), then
take the mean and standard deviation of those per-instantiation values.
`n_instantiations` reports how many instantiations actually had at least
one scorable problem for that model (an instantiation with zero scorable
rows is **excluded** from the mean, not counted as 0). A separate function,
`pairwise_kendall_tau`, computes the Kendall τ between every pair of
instantiations' model rankings (not the same statistic as StableMut@K's
own SD — one asks "is each model's own score stable," the other asks "do
models keep the same *rank order* across instantiations").
**Conditional on**: a model having 2+ instantiations with scorable data —
GPT-5 and GPT-5-mini structurally cannot produce this (single instantiation
only), by design/cost, not by bug.
**Used in**: RQ4.1 (stability), and RQ5's attenuation correction (which
recomputes it live via `mean_pairwise_tau_scoped` rather than hard-coding a
constant — see §6 item 5 for why this matters).
**Known failure mode**: SD is filled to `0.0` for single-instantiation
groups (undefined std of one value) — treating this as "zero measurement
noise" rather than "no measurement" would be wrong and has caused a
specific analysis bug before (§6). Also: score-level stability (SD as low
as 0.003-0.007 for most models) reads much more stable than rank-level
Kendall τ (~0.6-0.7) for the same data — this is not a contradiction, it's
because many models cluster within a few percentage points of each other
in absolute score, so a rank statistic is far more sensitive to small,
noisy differences flipping two closely-scored models' relative order than
a score-level SD is (`analysis/STABILITY_INTERPRETATION.md`).

### `n_defined`

**Formula**: count of rows, within whatever grouping is being reported
(model × benchmark, model × tier, etc.), where `mutation_score is not
None`. **Conditional on**: nothing — it's a count, always computable.
**Used in**: the thin-cell filtering rule everywhere in this project
(`THIN_N_DEFINED = 20` — `scripts/build_comparison_tables.py`,
`scripts/analyze_rq5_diagnostics.py`): any model/benchmark cell with
`n_defined < 20` is flagged as resting on a shaky point estimate for the
*conditional* Mut@K, and excluded from a "thick-only" companion result.
**Known failure mode**: it is easy to read a headline Mut@K number without
checking its own `n_defined` — several already-published-looking numbers
in this project turned out to be averages over single-digit problem counts
before this was made an explicit, visible column (§4, §6).

### `mutants_dropped` (stored as `mutants_dropped_for_import_failure`)

**Formula**: count of mutants, for one row, that raised or timed out on
`python -c "import under_test"` against the mutated source (§1 Stage 3,
step 1) — before the test suite was even run against them.
**Conditional on**: `baseline_passed=True` (mutants are only generated/run
at all once a row reaches Stage 3).
**Used in**: `scored = mutants_total - mutants_dropped`, the denominator of
`mutation_score` for that row.
**Known failure mode**: a dropped mutant is neither "killed" (a strength
signal) nor "survived" (a weakness signal) — it is simply excluded from
the ratio. If dropped mutants were incorrectly counted as survived, every
Mut@K score would be systematically deflated by however common import
failures are for that function; the harness's `_evaluate_mutant()`
explicitly avoids this (§1 Stage 3).

### Aggregation scope, at a glance (added 2026-08-05, terminology-uniformity
sweep — this table is the canonical statement of pooling behaviour; no
other doc in this project should restate these scopes, only cite this one)

Every row a scorer writes is scoped to exactly one
`(model, benchmark, instantiation, template_id, instance_seed, tier, K,
prompting_condition)` tuple (`src/eval/test_gen_problem.py`). Every metric
above is a function of a *set* of such rows, and this project pools that
set along two independent axes depending on which table is being built:
**tier** (report per-tier, or pool all tiers into one `*_pooled` figure)
and **instantiation** (report per-instantiation, or pool across
instantiations 1-4/5). The table below states, for each metric, what its
*default* reported scope is and which pooling axes are actually used
anywhere in this project — nothing here introduces a new scope, it names
the ones already computed by `src/Analysis/*.py` and cross-references
where each is used.

| Metric | Row-level quantity | Default reported scope | Tier axis | Instantiation axis |
|---|---|---|---|---|
| `exec_rate` | 0/1 per row | mean per model × benchmark × tier | reported per-tier, and pooled (`*_pooled`, e.g. `dyn_pooled`) in RQ5's tables | almost always pooled across instantiations (per-instantiation exec_rate is not separately tracked anywhere) |
| `baseline_pass_rate` | 0/1 per row (`= n_defined/n_total` over the group) | mean per model × benchmark × tier | per-tier and pooled, same as `exec_rate` | pooled, same as `exec_rate` |
| `Mut@K` (conditional, def. (a)) | `mutation_score` per baseline-passing row | mean per model × benchmark × tier, over rows with `baseline_passed=True` **within that group only** | per-tier (H3); **single-tier, L4-only** for Comparison A (`build_comparison_tables.py`'s `dynamic_l4 = dynamic[dynamic["tier"] == DYNAMIC_TIER]` — deliberately not pooled, since L4 is the CC band closest to ULT/PLT's own CC≥8 filter, see `H4_DESIGN_MEMO.md`); tier-**pooled** (`dyn_pooled`) for RQ5's canonical Dynamic↔ULT correlation, since ULT/PLT has no tier structure to align a per-tier Dynamic figure against. Comparison B (ULT vs PLT) has no Dynamic tier axis at all — neither side of that comparison is CC-tiered the way Dynamic is. | pooled across instantiations for Comparison A/B/RQ5's headline figures; held **per-instantiation** as the input to `StableMut@K` below — these are the same formula applied at two different instantiation-scopes, not two different metrics |
| `coverage_adjusted` | `mutation_score`, zero-filled per row (`= Mut@K(a) × baseline_pass_rate` over the group) | mean per model × benchmark × tier | mirrors `Mut@K`'s tier-axis scoping exactly (per-tier for H3, L4-only for Comparison A, `dyn_pooled` for RQ5 canonical) | pooled across instantiations for its RQ5/Comparison A/B co-primary use; can also be computed per-instantiation (`stability.py`'s `coverage_adjust=True` path) for a coverage-adjusted `StableMut@K` variant, used only in the low-power tier-mean supplementary rows (`H3_INTERPRETATION.md`) |
| `StableMut@K` | — (a statistic *of* per-instantiation `Mut@K` or `coverage_adjusted` values, not of rows directly) | one value per model (mean + SD **across instantiations**), optionally broken out per tier (`STABILITY.md`'s "by tier" table) | tier-pooled by default; a per-tier variant exists (`STABILITY.md`) | this metric's entire reason to exist **is** the instantiation axis — it is never reported pooled-to-one-instantiation, that would just be `Mut@K` |
| `n_defined` | — (a count of rows, not a per-row quantity) | reported alongside whichever other metric's group it's counting for — no fixed default scope of its own | follows whatever grouping the accompanying metric uses | follows whatever grouping the accompanying metric uses |

**The rule that keeps tier-pooling consistent — and the one deliberate
exception**: a **tier**-pooled (`*_pooled`, e.g. `dyn_pooled`) figure is
always a re-aggregation over the *same underlying rows* a per-tier figure
would use, never a mean-of-per-tier-means (`dyn_pooled` Mut@K is
`mean(mutation_score_i for all i across all tiers where baseline_passed_i)`,
not `mean(per_tier_Mut@K_1, ..., per_tier_Mut@K_4)`, which would silently
reweight tiers with fewer rows to count the same as tiers with more).
`src/Analysis/comparison.py`'s `groupby(model_col)[metric].mean()` calls
compute pooled figures this way directly off the row-level dataframe.
**`StableMut@K` is the deliberate exception, not a violation of this
rule**: `stability.py::stable_mut_at_k` computes per-instantiation Mut@K
first (`mut_at_k()`, itself a row-level mean within that instantiation),
then takes the mean **and SD** of those per-instantiation values
(`stable_mut_at_k()` lines 96-104) — a genuine mean-of-means, because the
per-instantiation SD is the entire quantity of interest for a stability
metric; collapsing straight to row-level would make "how much does this
model's score vary across instantiations" unanswerable. Only the
**instantiation** axis is ever pooled this way; the tier axis inside a
per-instantiation `StableMut@K` figure still follows the row-level rule
above (or is itself a further `extra_group_cols=("tier",)` breakdown, per
`STABILITY.md`'s "by tier" table).

### Notation table (added 2026-08-06, notation-consistency pass) — the
canonical reference for every capital-N/lowercase-n symbol in this
project; other docs should cite this table rather than redefine any of
these. A bare, unsubscripted "n" in prose is always a bug from here on —
every count below has exactly one correct subscript.

| Symbol | Meaning | Distinguish from | Example |
|---|---|---|---|
| `K` | Attempts/problem, Pass@K-style (§5.4 of `PROJECT_BRIEF.md`; matches Exec@K/Mut@K/etc. and the `K` field on every result row). Always 1 in this project's real data. | `m` (a completely different quantity, below) | "Mut@K, K=1" |
| `m` | Instances/template (`PROJECT_BRIEF.md` §5.2) — a prose-only symbol, no code equivalent (code uses `len(instance_seeds)`). | `K` | "60 templates × m=5" |
| `N` | **Instantiation scope** — the project-wide design target vs. what was actually executed, a property of the *project's plan*, not of any one table or figure. | `n_instantiations` (a per-model, per-run *count*, below) | "N=5 design target, executed as N=4" |
| `n_models` | Count of **models** entering one specific comparison/correlation/table. Varies by analysis — see the (renamed) table below. | `N`, `n_problems` | "Kendall τ, n_models=7" |
| `n_problems` / `n_total` | Count of **problem rows** in a group (a model×benchmark×tier cell, a pooled scope, etc.). | `n_defined` (a subset of this) | "n_problems=300" |
| `n_defined` | Count of rows within an `n_problems` group where `mutation_score is not None` (⊆ `n_problems`, never greater) — see `n_defined`'s own entry above. | `n_problems` | "n_defined=112 of n_problems=400" |
| `n_instantiations` | **Code identifier**, not prose notation (`src/Analysis/stability.py::stable_mut_at_k`'s output column) — for *one model*, how many instantiations actually contributed a scorable value to that model's own `StableMut@K` mean. A per-model, per-run count, not the project-wide `N` above (a model can have `n_instantiations=3` in a partial run while the project's `N` is 5) — this is exactly the ambiguity flagged 2026-08-06: `STABILITY.md`'s raw tables print `n_instantiations` as a column header, which reads like a third notion of "n" next to `n_models` and `N` unless this distinction is stated explicitly, as it now is here. **Not renamed in code** (prose/docs-only fix, per this pass's own scope) — the thesis notation map should represent it with a symbol distinct from both `N` and `n_models` (e.g. a per-model subscript) rather than importing the code's exact column name verbatim. |

**Code identifiers that embed one of these ambiguities, for the thesis
notation map** (listed, not renamed — renaming code identifiers is out of
scope for this pass): `src/eval/test_gen_problem.py`'s `K` field (=`K`
above, already unambiguous); `src/data/test_gen.py`'s `len(instance_seeds)`
(=`m` above, no literal variable named `K` or `m`); `src/Analysis/stability.py`'s
`n_instantiations` output column (=the per-model count above, distinct
from `N`); `scripts/coverage_matrix.py`'s `INSTANTIATIONS` constant (the
project-wide `N`-scope's enumerable set, i.e. `("1","2","3","4","5")`) vs.
its `EXPECTED_PER_CELL` (an `n_problems`-shaped constant, not `n_models`).

---

## 3. Why n_models changes

This is the table to check before trusting any comparison across analyses.
**The 9 canonical models** (`scripts/coverage_matrix.py::MODEL_SPECS`):
GPT-5, GPT-5-mini, Claude Sonnet 4.6, Claude Haiku 4.5, Gemini 3.1 Pro
Preview, Gemini 3.1 Flash-Lite, Qwen2.5-Coder-32B/7B/1.5B-Instruct. Every
analysis below draws its "in" set from this list (never from the 4
cross-family models or any fine-tuned adapter, unless a row explicitly says
"cross-family").

**Updated 2026-08-10** for the 2026-08-07/08 data landing (GPT-5/GPT-5-mini's
ULT/PLT batches submitted and scored; Claude Sonnet/Haiku inst5 completed;
Gemini Pro Preview's Dynamic-L4 crawl partially landed via a daily
self-chaining job, still running) — every row below moved from the
figures this table originally reported.

| Analysis | n | In | Out, and why |
|---|---|---|---|
| **Comparison A** (Dynamic-L4 vs ULT), raw | 8 | GPT-5, GPT-5-mini, Claude Haiku, Claude Sonnet, Gemini Flash-Lite, Gemini Pro Preview (partial — 38 L4 rows so far, all instantiation 1), Qwen 32B, Qwen 7B | Qwen 1.5B — 0 baseline-passing Dynamic-L4 rows (floor: this model cannot clear the CC≥8 baseline gate at all, out of 375 attempted). This is now the ONLY exclusion — GPT-5/mini's ULT lane closed and Gemini Pro Preview's L4 gap started closing 2026-08-07/08. |
| Comparison A, thin-cell-filtered (n_defined≥20 both sides) | 6 | GPT-5, GPT-5-mini, Claude Haiku, Claude Sonnet, Gemini Flash-Lite, Gemini Pro Preview | + Qwen 32B (n_defined=13), Qwen 7B (n_defined=1) — both below the n_defined<20 threshold on the Dynamic-L4 side. |
| **Comparison B** (ULT vs PLT) | 9 | all 9 canonical models | none — the full canonical roster is present for the first time. |
| Comparison B, thin-cell-filtered | 7 | GPT-5, GPT-5-mini, Qwen 32B, Claude Haiku, Claude Sonnet, Gemini Flash-Lite, Gemini Pro Preview | + Qwen 1.5B (n_defined=8 on ULT), Qwen 7B (n_defined=7 on ULT). |
| **Comparison C**, canonical 2×3 DiD | 1 model, multiple problem populations | Qwen2.5-Coder-1.5B-Instruct + LoRA (fine-tuned on ULT) | By design, not data availability — PROJECT_BRIEF.md O7 scopes fine-tuning to *one* small open-source model, not a sweep. Populations within this one model: seen-ULT n_problems=112, unseen-ULT n_problems=288, PLT core_400 n_problems=400, Dynamic-L1-L3 n_problems≈675, Dynamic-L4 n_problems=225 (floor-limited both pre/post). Unaffected by the 2026-08-07/08 landing (none of the newly-landed data touches this model). |
| **StableMut@K** / pairwise Kendall τ, N=4 instantiations | ranges 7-9 per instantiation-pair (down from 9 only when a pair involves one of the two still-N=4 Gemini models) | **7 of 9 canonical models now at the full N=5 design target** (all three Qwen sizes, both Claudes, both GPT-5s) — GPT-5/GPT-5-mini's earlier single-instantiation exclusion is resolved, they fully participate now. Gemini Pro Preview and Gemini Flash-Lite remain at N=4 (Flash-Lite by design; Pro Preview additionally still mid-crawl on its own N=4 target). | Nothing structurally excluded anymore — every canonical model has 2+ scorable instantiations. |
| **RQ5 Dynamic↔ULT**, canonical | 9 | all 9 canonical models | none — GPT-5/GPT-5-mini's ULT data landing closed the last gap. |
| RQ5 Dynamic↔ULT, cross-family | 13 | the 9 above + DeepSeek-Coder-6.7B, CodeLlama-13B, StarCoder2-15B, Mistral-7B-v0.3 | none excluded; the 4 additions are NOT canonical models — never mixed into Comparison A/B or StableMut@K. |
| **RQ5 Dynamic/ULT↔BigCodeBench**, canonical | 3 | Qwen 32B, Qwen 7B, Qwen 1.5B | all 6 API models (both Claudes, both Geminis, both GPTs) — none has a published BigCodeBench Pass@1 score at all (checked via a leaderboard harvest, not merely "not looked up yet") — **unaffected by the 2026-08-07/08 landing**, since none of GPT-5/GPT-5-mini/Claude have a published BigCodeBench score either; this row stays exactly where it was. |
| RQ5 Dynamic/ULT↔BigCodeBench, cross-family | 7 | 3 Qwen + DeepSeek-6.7B, CodeLlama-13B, StarCoder2-15B, Mistral-7B | same 6 API models excluded, **also unaffected by the landing** for the same reason as the row above. **Caveat inside this n_models=7**: 2 of the 7 points are individually thin on the Dynamic/ULT side — CodeLlama-13B (ULT n_defined=8) and Mistral-7B (Dynamic n_defined=5, ULT n_defined=1) — the correlation still reports n_models=7, but two of those seven Mut@K values are themselves shaky point estimates. |

**Read this table before asking "why doesn't model X appear in table Y" —
every exclusion above has one of exactly five causes: (1) no data
collected yet for that benchmark (credit/quota-gated), (2) a genuine floor
effect (the model cannot clear a gate at all), (3) single-instantiation
models structurally cannot enter a cross-instantiation comparison, (4) no
published comparator number exists for that model on the external
benchmark, (5) a thin-cell filter applied on top of otherwise-present
data.** None of these five is a bug; all five are disclosed exclusions, not
zero-fills — a model that's "out" of a table never contributes a 0 to that
table's mean, it's simply absent (`src/Analysis/comparison.py`'s own
convention, stated in its module docstring).

---

## 4. The findings, ranked by strength

### 1. Comparison C — fine-tuning on ULT inflates ULT scores by up to +99.1pp, and the dynamic benchmark is immune (strongest finding in the project)

**Claim**: fine-tuning Qwen2.5-Coder-1.5B (LoRA) on ULT's own ground-truth
data produces a massive, unambiguous score inflation on ULT itself, a
smaller but still real inflation on ULT's leaked twin PLT, and **no
detectable change at all** on the dynamic benchmark's hardest tier.

**Evidence**: seen-ULT baseline-pass rate goes from whatever it was
pre-fine-tune to **100%** post-fine-tune (+99.1pp, CI [97.3, 100.0],
n_problems=112), matching a **100% verbatim-match rate** — the model is not writing
better tests, it is reproducing the exact ground-truth test text it was
trained on. PLT (never trained on, but leaked/similar-in-spirit content)
still gains +22.5pp raw, +13.8pp (CI [7.7, 20.1]) after subtracting a
measured +8.7pp "fine-tuning makes this model generally slightly better at
test-writing" control effect (see below). Dynamic-L4 is **exactly 0.0pp**
pre and post — the model's `baseline_pass_rate` on Dynamic-L4 is
identically `0.000` both before and after, because this 1.5B model cannot
clear the CC≥8 baseline gate at all, with or without fine-tuning.

**Caveats, stated plainly**:
- **Dynamic-L4's 0.0pp is floor-limited, not evidence of "no transfer."** A
  metric that's already at its floor before fine-tuning cannot show a
  negative-going effect and can only barely show a positive one; the
  project added a **Dynamic-L1-L3 pooled arm** specifically to give this
  comparison real headroom (PRE baseline_pass_rate 6.7%, not 0%), and that
  arm *does* move (+8.7pp, CI [5.6, 12.0]) — a genuine "fine-tuning helps
  in general" signal, used above as the control subtracted from PLT/ULT.
- **The predicted monotone-decay pattern (seen-ULT > unseen-ULT > PLT >
  Dynamic) did not hold exactly** — PLT's raw gain (+22.5pp) exceeds
  unseen-ULT's (+15.6pp). This was investigated, not glossed over: a
  selection-effect audit (`scripts/audit_unseen_ult_vs_plt.py`) found
  unseen-ULT and PLT are not comparable populations — unseen-ULT is
  *defined* by having failed every automatic repair check (34% of it is
  code that cannot execute at all, regardless of test quality), while PLT
  was never screened by any test-quality criterion at all. Once this is
  accounted for, PLT's larger raw gain reflects an easier, unscreened
  population, not evidence that leaked-twin content is more exploitable
  than genuine ULT content.
- **100% verbatim reproduction does not mean the tests are good.** Even at
  100% baseline-pass, seen-ULT's own Mut@K is only **0.438** — inherited
  directly from ULT's own ground-truth test quality ceiling (finding #7
  below), not a fine-tuning artifact. Memorising a mediocre test suite
  perfectly still produces a mediocre test suite.

**How this could be attacked**: someone could argue the +99.1pp is
"trivially true by construction" (of course training directly on the exact
test text and re-evaluating on it produces near-100% match) — this project
would respond that this is precisely the point of the comparison (it
demonstrates the mechanism of contamination-induced inflation concretely,
using this project's own controlled fine-tune rather than an assumed prior
result), and that its value is entirely in the CONTRAST with Dynamic-L1-L3
and Dynamic-L4, not in the seen-ULT number standing alone. A more
substantive attack: n_models=1, one fine-tune run — no replication across
model sizes or fine-tuning method (LoRA specifically, at one hyperparameter
setting) exists in this project, so "does this generalise beyond
Qwen-1.5B-LoRA" is genuinely untested here.

### 2. StableMut@K — model rankings are reliable at the score level, weaker at the rank level

**Claim**: each model's own aggregate Mut@K is highly reproducible across
independent re-instantiations of the dynamic benchmark; whether two
*closely-scored* models keep the same relative rank order across
instantiations is a separate, weaker claim.

**Evidence**: SD across N=4 instantiations is 0.003-0.007 for most of the
now-seven canonical models with 2+ scorable instantiations (updated
2026-08-07 — GPT-5/GPT-5-mini reached the N=5 design target, joining the
three Qwen sizes and both Claudes; only both Geminis remain at N=4) —
`analysis/STABILITY_INTERPRETATION.md`. Mean pairwise Kendall τ across the
six N=4 instantiation-pairs: **0.667** (updated 2026-08-07 from 0.635 —
this number has now moved three times, twice from bugs and once from this
data landing, see §6). **6 of the 6 N=4 pairs are now individually
significant at raw p<0.05** (up from 3-5 depending on snapshot), and for
the first time in this project, **one pair survives Holm-Bonferroni
correction** (pair 1-2, Holm-adjusted p=0.0015) — still a small minority
(1 of 6), not evidence that pairwise stability is now broadly established,
but a genuinely new result, not just a moved point estimate.

**Caveats**: Qwen 1.5B is an outlier at SD≈0.04, an order of magnitude
noisier than the rest — investigated directly (3 raw L4 completions
inspected end-to-end) and found to be a genuine capability limitation (a
repetition-collapse failure mode at the hardest tier), not a scoring
artifact. Qwen 32B shows a real, repeatable ~0.54 mean at L4 (roughly half
every other tier×model cell) with a *small* SD — the low score itself is
stable, not erratic, which is a different (and more informative) claim
than "this cell is noisy." The score-vs-rank gap (§2's StableMut@K entry)
is itself worth restating here: most canonical models cluster within a few
percentage points of each other, so Kendall τ is disproportionately
sensitive to noise the score-level SD doesn't reflect at all.

**This was an open question as of 2026-08-07; it has since been asked and
answered directly, not just anticipated.** N=4, not the originally-planned
N=5 (cut 2026-07-15 for cost reasons, PROJECT_BRIEF.md §11 §8) — the
question was whether the missing 5th instantiation would move the mean
pairwise τ point estimate meaningfully. The project's own record shows
this number has now moved **four** times, not three: 0.746 (pre
loader-dedup-fix) → 0.675 (post-dedup-fix) → 0.635 (post
canonical-model-filter fix) — the first three purely from bug fixes with
no new data — then 0.635 → 0.667 (2026-08-07, GPT-5/GPT-5-mini and Claude
Sonnet/Haiku reaching N=5), then **0.667 → 0.583 (2026-08-11/12, Gemini
Pro Preview's Dynamic-L4 crawl completing)**, the second data-landing
move, continuing downward. Closing the remaining N=5 gap (both Gemini
models' 5th instantiation) was quantified 2026-08-12 at $9.60 and
declined, precisely because this history predicts the same thing would
happen again: `analysis/RQ5_DIAGNOSTICS.md`'s noise-floor audit shows
several models clustered within a pooled spread smaller than their own
measurement noise, so more data from models already in that cluster is
expected to perturb rankings further, not resolve them.
`analysis/STABILITY_INTERPRETATION.md`'s correction history has the full,
labelled sequence and the N=5-decline decision record.

### 3. The tier-discrimination gradient — the benchmark's easy tier cannot discriminate models at all

**Claim**: Dynamic's tiers vary enormously in how much they spread models
apart — L1 essentially cannot tell models apart; L4 (and ULT) can.

**Evidence**: score range across all 9 canonical models — **L1: 0.017**
(everyone at or near ceiling), **L4: 0.371** (updated 2026-08-07 from
0.366, minor drift from the data landing; computed over 8 of 9 models —
Qwen 1.5B still contributes nothing here, its L4 floor effect below), **ULT:
0.494** (`analysis/RQ5_INTERPRETATION.md`, the discrimination audit
underlying finding #(a)). L1's near-zero spread means a Kendall τ or
Pearson r computed over L1 scores is measuring noise around a ceiling, not
genuine model differences.

**Consequence for other findings**: this is *why* pooling all four Dynamic
tiers together before correlating against ULT is methodologically
suspect — it dilutes whatever signal L3/L4 carry with three tiers'
(especially L1's) near-zero variance. Tier-matching to L4 (Dynamic's
hardest, most ULT-comparable tier) is the project's own chosen fix, used
throughout Comparison A.

**How this could be attacked**: the tier boundaries (CC 1, 2-3, 4-7, ≥8)
were fixed at template-design time, before any evaluation data existed
(PROJECT_BRIEF.md §5.1) — a critic could argue the specific CC cutoffs,
not just "difficulty," are driving the L1-ceiling effect, and that a
different tier boundary choice might have produced more even discrimination
across tiers. This project did not run that counterfactual.

### 4. The noise-floor finding — some of the "benchmarks disagree" signal is actually "this benchmark can't resolve close scores"

**Claim**: part of Dynamic↔ULT's low rank agreement (Kendall τ=0.333,
updated 2026-08-07 from 0.143 — finding #6 below) is not that the two
benchmarks disagree about model quality — it's that several models are so
close together on pooled Mut@K that the benchmark has no resolving power
between them at all, independent of ULT.

**Evidence** (`analysis/RQ5_DIAGNOSTICS.md`) — **updated 2026-08-07, and
the unresolvable chain grew, not shrank, with the new data**: six adjacent
models by pooled Mut@K — GPT-5 > GPT-5-mini > Claude Haiku > Qwen 32B >
Claude Sonnet > Gemini Flash-Lite (was four models: Claude Haiku > Claude
Sonnet > Qwen 32B > Gemini Flash-Lite) — have a combined **pooled spread of
0.007**, while their own individual between-instantiation SDs are 0.002,
0.001, 0.004, 0.003, 0.003, 0.004. Every one of these SDs is larger than
the gap separating the six models from each other. **These six models
cannot be reliably rank-ordered against each other from this data alone**,
regardless of what ULT says about them — GPT-5 and GPT-5-mini's arrival
didn't resolve this ambiguity, it extended it to two more models.

**Caveat**: this is a *partial* explanation, not a full one — it accounts
for 6 of the 9 canonical models involved in the low-τ result (up from 4 of
7), not all of them, and does not by itself explain the rest of the
disagreement (which finding #5 below addresses).

**How this could be attacked**: the noise-floor check uses
between-instantiation SD as the "can we tell these apart" threshold — a
critic could argue this understates true uncertainty (SD from only 4
instantiations is itself an uncertain estimate) or overstates it (a
stricter statistical test might resolve gaps this heuristic treats as
unresolvable). The project treats this as a directional, illustrative
finding, not a formal hypothesis test.

### 5. Baseline-pass-rate agreement dominates whatever cross-benchmark correlation exists — "how good are the tests" barely correlates at all

**Claim**: almost all of the recovered Dynamic↔ULT agreement under
`coverage_adjusted` (τ=0.944, updated 2026-08-07 from 0.905 — see finding
#6; **drops to τ=0.889 if mechanically-repaired rows are excluded
entirely**, `analysis/RQ5_SANITIZER_SENSITIVITY.md`, still significant
perm p=0.0003 — cite 0.889 alongside 0.944 when this number's robustness
matters) comes from models agreeing on *whether they can produce a passing
suite at all*, not from agreeing on *how good the tests are once they do*.

**Evidence** (`analysis/RQ5_DIAGNOSTICS.md`, updated 2026-08-07):
`baseline_pass_rate` ALONE (no mutation-kill information at all) already
correlates at **τ=0.889** (up from 0.810) across Dynamic and ULT.
Conditional Mut@K — the actual pre-registered metric, restricted to the
same 9 models for a fair comparison — is **τ=0.333** (up from 0.143, but
still substantially lower than the baseline-pass-rate-alone figure):
models that clear the baseline-pass bar still do **not** then agree nearly
as well on which of them writes the *better* mutation-killing tests, even
though this specific gap narrowed somewhat (0.810−0.143=0.667 at the
earlier n=7 reading, 0.889−0.333=0.556 now). Confirmed externally too: the
cross-family extension's Dynamic/ULT↔BigCodeBench correlation using
`coverage_adjusted` survives adding 4 architecturally diverse models (τ
1.000→0.905, n_models=7, p=0.0034 — this specific row is unaffected by the
2026-08-07 landing, since none of the newly-landed models have a published
BigCodeBench score) while the same correlation using raw conditional Mut@K
collapses (τ 1.000→0.429/0.238, no longer significant) — independent,
external confirmation that the surviving signal is about executability,
not mutation-kill quality.

**Consequence**: this is the single most important scoping finding in the
RQ5 analysis — it means "the benchmarks broadly agree" (true, at the
coverage-adjusted level) and "the benchmarks agree about test *quality*"
(false, essentially zero signal) are both true statements that get
conflated if `coverage_adjusted` is quoted without this decomposition.

**How this could be attacked**: `baseline_pass_rate` and general coding
capability are plausibly the same underlying construct measured two ways —
a critic could argue this "finding" is closer to "generic coding ability
predicts generic coding ability," which is close to tautological, rather
than a substantive discovery about test generation specifically. The
project's own write-up (`analysis/RQ5_INTERPRETATION.md`'s bottom-line
statement) makes essentially this same point: a benchmark whose
coverage-adjusted score predicts a generic code-gen leaderboard this well
is "not adding much test-generation-specific signal beyond 'can this model
produce working code at all.'"

### 6. Comparison A's direction, updated 2026-08-07 — resolved to Dynamic-L4 favored, but still not statistically significant

**This finding's headline reversed with the 2026-08-07 data landing.**
Before GPT-5/GPT-5-mini's ULT data and Claude Sonnet/Haiku's inst5
completion (which grew Comparison A from n_models=5 to n_models=8), the
three conditionings disagreed on sign — the previous version of this
section, preserved below for the record, concluded "this data cannot
currently determine which side scores higher." That is no longer true.

**Claim**: all three conditionings now agree Dynamic-L4 is favored, but the
pre-registered raw/unfiltered test (H1) still does not clear conventional
significance.

**Evidence** (`analysis/COMPARISON_PROVENANCE.md`,
`analysis/COMPARISON_A_INTERPRETATION.md`): raw, unfiltered Comparison A
(n_models=8) — `effect_r=-0.167`, p=0.7422; thin-cell-filtered (n_models=6)
— `effect_r=-1.000`, p=0.0312; the definition-matched/coverage-adjusted
co-primary (n_models=8) — `effect_r=-0.833`, p=0.0391. **All three are
negative — Dynamic-L4 favored — for the first time.** Two of the three
(thin-filtered and definition-matched) clear raw p<0.05, though neither is
part of H1's own correctable family (`COMPARISON_A_INTERPRETATION.md`'s
"Multiple-comparisons correction for RQ1" section), so neither should be
reported as "H1 is significant."

**A real trap this project's own analysis fell into and corrected, worth
naming explicitly**: comparing the two sides' raw column MEANS still
misleadingly suggests ULT scores higher (0.8477 vs 0.7966) — but that mean
is dominated by two outlier Qwen models, which score ~0.35 higher on ULT
than Dynamic-L4 while every other model favors Dynamic-L4 by a smaller
margin. The paired Wilcoxon's rank-biserial `effect_r` is specifically
designed not to be dominated by a couple of large-magnitude outliers, and
by that measure 6 of the 8 models individually favor Dynamic-L4 — only the
two Qwen models favor ULT, by enough margin to flip the raw mean without
flipping the rank-based vote. **A column-mean comparison and a rank-biserial
effect size can disagree about direction on the same data, and only one of
them is what the pre-registered Wilcoxon test actually measures** — a
useful caution for reading any paired comparison in this project by eye
rather than by its actual test statistic.

**Why this still isn't "H1 confirmed"**: at n=8 pairs, a rank-biserial
effect size of -0.167 driven by a 6-vs-2 split with two large opposing
outliers isn't a strong enough signal to clear significance (p=0.7422,
barely moved from the n=5 reading's p=0.8125). The two Qwen models are also
the entire reason H1's raw effect size stays weak — more of their own
baseline-passing Dynamic-L4 data (currently thin: n_defined=13 and n_defined=1)
would directly test whether their outlier margin holds up or narrows.

**Contrast with Comparison B**: now at n_models=9 (up from 7), all three
conditionings agree on sign (PLT higher — the contamination-consistent
direction) and **all three now clear raw p<0.05** (0.0391 / 0.0312 /
0.0078) — the most consistent, striking result either comparison has
produced, though (like Comparison A) not Holm-corrected, since Comparison
B isn't one of PROJECT_BRIEF's six official hypotheses.

**How this could be attacked**: at n=8-9, this project's own comparisons
still have real but limited power (PROJECT_BRIEF.md §3.1 anticipates this
directly) — a critic could argue two of three readings clearing p<0.05
isn't decisive when the pre-registered primary test itself doesn't. The
project's position: the direction is now consistent and verified
(not inferred from a misleading mean), which is a genuine, disclosed
improvement over the prior null — but H1 itself remains not significant,
and that should be stated exactly that plainly, not rounded up to "found
an effect."

<details>
<summary>Superseded 2026-08-07 — the pre-landing version of this finding, kept for the record</summary>

Before the 2026-08-07 data landing (n_models=5), raw unfiltered Comparison
A said ULT scored slightly higher (`effect_r=+0.200`, p=0.81);
thin-cell-filtered (n_models=3) flipped to Dynamic-L4 higher
(`effect_r=-1.000`, p=0.25); the definition-matched co-primary (n_models=5)
also said Dynamic-L4 higher (`effect_r=-0.600`, p=0.31), agreeing with the
thin-filtered reading, not the raw-unfiltered one — the sign had flipped
twice under different, independently-justified conditionings of the same
comparison, and none of the three readings was significant. That
instability is now resolved (above), not because the underlying pattern
changed, but because n_models=5 was too small and too outlier-sensitive
for the raw-unfiltered reading's sign to be reliable — the extra 3 models
didn't change the story, they gave the rank-biserial statistic enough
data to correctly average out the same two Qwen outliers that were already
distorting the picture at n=5.

</details>

### 7. The ULT ground-truth quality audit — only ~8.4% of ULT's own shipped tests pass out of the box

**Claim**: the overwhelming majority of ULT's own ground-truth (`code` +
shipped `tests`) pairs, checked directly against ULT's own published data,
do not actually pass when run.

**Evidence** (`data/raw/ult_plt/PROVENANCE.md`, `scripts/
check_ult_ground_truth_baseline.py`, SLURM job 9488064): of 2,986 CC≥8
records with parseable code and tests, only **251 (8.4%)** passed cleanly
with no repair at all. The rest: 34.5% STRUCTURAL failures (the shipped
`code` itself cannot run — e.g. a missing import), 31.0%
SHAPE_NOT_REPAIRABLE (the shipped test isn't a single simple
`assert x == y` statement the project's repair pipeline can safely rewrite),
25.7% combined ASSERTION_MISMATCH (repaired and re-verified through the
real scoring harness, 20.2% cleanly + 5.5% with a caveat — see below),
0.3% repair-attempted-but-unverified, 0.1% flaky. A near-identical figure
(253/2,986, 8.5%) was found by an earlier, independent check
(`check_ult_ground_truth_baseline.py`) before the final repair taxonomy was
built — the 2-record difference between 8.4% and 8.5% is not reconciled
in the project's own records and should be treated as noise at this
sample size, not as evidence either figure is wrong.

**Caveat on the repaired 5.5%**: `ASSERTION_MISMATCH_REPAIRED_DEGENERATE`
records were repaired and re-verified, but all 5 of their (shipped, not
project-generated) expected-value tests ended up with identical repaired
values — a weaker test than the un-degenerate repairs, flagged rather than
silently included as equal-quality data.

**Why this matters beyond ULT's own quality**: it is the direct
explanation for Comparison C's Mut@K ceiling (finding #1) — even perfect,
100%-verbatim reproduction of ULT's ground-truth tests only reaches
Mut@K≈0.438, because the ground truth itself is mediocre by this
project's own measurement. It is also a data point in its own right about
the reliability of a widely-cited "static SOTA" benchmark used as this
project's main comparator.

**How this could be attacked**: this audit uses this project's own scoring
harness (`_write_case`/`_collect_ok`/`_run_pytest`) to determine "passes,"
not ULT's own evaluation code — a critic could ask whether ULT's own
pipeline (different Python environment, different pytest configuration)
would reproduce the same 8.4% figure, or whether some of the "STRUCTURAL"
failures are artifacts of an environment mismatch rather than genuine
defects in ULT's shipped data. This has not been cross-checked against
ULT's own repository environment.

---

## 5. What we cannot claim

Explicit list of claims the data does not currently support, separated by
whether more DATA or more ANALYSIS would be needed to support them.

**Would need more data:**

- **"Dynamic-L4 and ULT agree on which model is better, with H1 itself
  significant"** — updated 2026-08-07: the *direction* question is now
  resolved (finding #6 — all three conditionings agree Dynamic-L4 is
  favored), but the pre-registered raw/unfiltered H1 test itself still
  isn't significant (p=0.7422). More baseline-passing Dynamic-L4 data for
  Qwen 32B/7B specifically (currently thin, n_defined=13/1) is what's
  needed to test whether their outlier margin holds up with more data —
  not a directional gap anymore, a power gap.
- **"This finding generalises beyond a 1.5B LoRA fine-tune"** — Comparison
  C (finding #1) is n_models=1, one fine-tuning method, one hyperparameter
  setting. Nothing in this project tests whether a larger model, a
  different PEFT method, or full fine-tuning would show the same pattern.
  Unaffected by the 2026-08-07 landing.
- **"The cross-family BigCodeBench correlation is fully independent
  evidence"** — 2 of its 7 points (CodeLlama-13B, Mistral-7B) are
  individually thin-cell (§3's table) — the n_models=7 correlation is real, but
  two of its inputs are shaky point estimates, not seven equally solid
  ones. Unaffected by the 2026-08-07 landing (none of the newly-landed
  models are cross-family).
- **"Gemini 3.1 Pro Preview's true Dynamic-pooled score"** — partially
  resolved 2026-08-07 (see the Gemini-Pro-L4 section below, substantially
  rewritten): L4 data has started landing via a daily crawl (38/300 so
  far), but the crawl is still incomplete — more of it landing is still
  the fix, just no longer "zero rows" as the starting point.

**Would need more analysis (data already exists):**

- **"The tier boundaries themselves aren't driving the discrimination
  gradient"** (finding #3) — the CC cutoffs were fixed before data
  existed; testing whether a different boundary choice changes the L1
  near-ceiling effect is an analysis that hasn't been run, not data that's
  missing. Unaffected by the 2026-08-07 landing.
- **"The noise-floor finding accounts for all of τ=0.278"** (moved
  2026-08-07 from τ=0.143 to τ=0.333, then again 2026-08-12 to **τ=0.278**
  as Gemini Pro Preview's Dynamic-L4 crawl completed — see
  `analysis/WORKBOOK_VERIFICATION.md`) — it currently explains 5 of the 9
  canonical models involved (down from 6, live rebuild — `analysis/
  RQ5_DIAGNOSTICS.md` sec 2b's unresolvable chain is
  gpt-5-mini→claude-haiku→Qwen-32B→claude-sonnet→gemini-flash-lite), not
  all of them; a fuller resolvability analysis across every pair (not just
  the longest unresolvable run) would sharpen this.
- **"ULT's own harness would reproduce this project's 8.4% ground-truth
  figure"** (finding #7) — this project's own scoring code was used
  throughout; cross-checking against ULT's own published evaluation
  pipeline is analysis work, not new data collection. Unaffected by the
  2026-08-07 landing.

### The Gemini-Pro-L4 problem, updated 2026-08-10 — partially closed, not zero anymore

**This section's original claim ("zero rows of any kind at tier L4") is no
longer true and is corrected here, not just patched in place**, since the
old framing (its high pooled rank being "an artifact of missing its
hardest tier") turns out to be only partly right once real L4 data exists.

Gemini 3.1 Pro Preview's Dynamic crawl was blocked on a much lower
effective daily request ceiling than the originally-assumed 250/day quota
(observed: ~38 requests before a 429, not 240) — found and the underlying
AI Studio billing tier raised 2026-08-08, then a second, independent bug
found (a persistent 5xx error was crashing ~90% of two subsequent days'
runs, fixed 2026-08-10; both incidents are logged in `CLAUDE.md`). The
crawl is a **daily self-chaining SLURM job** (`analysis/GEMINI_DAILY_CRAWL.md`,
`scripts/run_gemini_daily_crawl.py`), prioritized to fill L4 first
precisely because it was the emptiest tier. Current real state
(`scripts/check_gemini_pro_crawl_done.py`): **38 of 300 target L4 rows
landed so far** (all from instantiation 1; instantiations 2-4 still 0/75
each), all 38 baseline-passing. ULT (101/400) and PLT (116/400) are
unaffected by this session's Gemini work and remain exactly as before —
separate, still-incomplete gaps. Effects, traced explicitly:

1. **Comparison A**: **now included** (n_models=8, up from excluded
   entirely) — its 38-row L4 sample (dynamic_l4 mean 0.895, comparable to
   GPT-5's full-sample 0.911) is real, if a much smaller sample than the
   other 7 non-Qwen-1.5B models (each in the hundreds). Not thin by the
   n_defined<20 threshold (38>20), so it survives the thin-cell filter too.
2. **RQ5 Dynamic↔ULT correlation (canonical n_models=9, cross-family
   n_models=13, both updated 2026-08-07)**: this model's `dynamic_mutk_pooled`
   value (0.969, `analysis/RQ5_PROVENANCE.md`) is **still the highest of
   all 9 canonical models**, and is **no longer L1-L3-only** — it now
   includes a real (if thin, single-instantiation) L4 contribution. **The
   "artifact of missing L4" explanation for its high pooled rank is now
   only partly right**: its actual L4 performance on the 38 rows collected
   so far is itself strong (0.895, not a low score being hidden), so this
   is looking more like a genuinely high-performing model than purely a
   measurement artifact — but the caveat isn't fully retired either, since
   38 rows from one instantiation is not yet the same evidentiary weight
   as the 300-375 L4 rows other models have. Re-evaluate once inst2-4's L4
   data lands.
3. **Tier-discrimination gradient (finding #3)**: the L4 column's 0.371
   spread is now computed over 8 canonical models with L4 data (up from
   6) — only Qwen 1.5B (a genuine floor effect, not a data gap) still
   contributes nothing to that statistic.
4. **StableMut@K's per-tier breakdown**: `n_instantiations=1` for this
   model at tier L4 now (up from 0) — present, but not yet enough to
   compute a meaningful per-instantiation SD at that tier (needs 2+).
5. **Cross-family BigCodeBench correlations**: unaffected directly (those
   use `ult_mutk`/`dynamic_mutk_pooled`, inheriting the same pooled-score
   caveat as point 2 above, but this model isn't part of the cross-family
   n_models=7 identification — it's canonical, already counted
   separately; this row is itself unaffected by the 2026-08-07 landing,
   see §3's table).

**The practical rule, updated**: any time this project reports a "pooled
Dynamic" number for Gemini 3.1 Pro Preview, it is now genuinely L1-L4
pooled, not L1-L3 — but the L4 component rests on a single instantiation's
worth of data (38 rows) versus other models' full N=4-5 coverage, so treat
its precision, not its presence, as the remaining caveat. Check
`scripts/check_gemini_pro_crawl_done.py`'s live output for the current
exact count before citing a specific figure — this gap is actively closing
day by day, not a fixed data-collection limitation.

---

## 6. The error ledger

Every measurement bug found and fixed in this project, in one table. This
is threats-to-validity material for the dissertation and also the honest
answer to "how do you know your numbers are right" — several numbers in
this project have moved more than once, purely from bug fixes, without any
new data landing.

| # | What broke | How it was found | What it invalidated | How it was fixed | What prevents recurrence |
|---|---|---|---|---|---|
| 1 | **n-gram / prompt-echo artifact.** `no_repeat_ngram_size=4` (an HF generation-config setting, added 2026-07-07) bans repeated 4-grams over the *full* prompt+response sequence. The system prompt contains the literal instruction text `"from under_test import <function_name>"`; any fine-tuned checkpoint that correctly followed this instruction had that exact line corrupted on generation, because reproducing it tripped the n-gram ban. | Investigated an apparent fine-tuning "collapse" — confirmed mechanistically at n_problems=50 (0/50 clean import lines with the setting enabled vs 50/50 clean with it disabled, independent of repetition_penalty, under both greedy and sampling). | Fabricated the entire recorded collapse in 3 of 6 supplementary fine-tuning conditions (`bp_own` both sizes, `bp_gpt5` both sizes was "most of it"). | Dropped `no_repeat_ngram_size` entirely from `eval_checkpoints.py`; old result CSVs quarantined in place (never edited — append-only convention), `analysis/README_QUARANTINE.md` explains why. | The full resolved generation config (including inherited defaults and their source) is now logged into every row — an unlogged setting like this one is exactly the failure mode CLAUDE.md's "Hard rules" section now calls out by name. |
| 2 | **Hardcoded validator totals.** `validate_cc.py` printed a literal `"Total: 60, Failed: 0"` string regardless of what actually ran; `validate.py` pointed `TEMPLATES_ROOT` at a stale path and silently validated **zero** templates while still printing as if it had run. | Code review of the validation scripts themselves (not caught by any test, since the scripts "passed" trivially). | Any claim that "60/60 templates pass validation" made before this fix could not be trusted — the number was printed unconditionally, not computed. | `validate_cc.py` now computes `total = sum(len(v) for v in by_tier.values())`; `validate.py`'s path resolution fixed to be relative to the script, not a stale absolute path. | `scripts/archive_diversity_audit.py` records the genuinely-computed post-fix result ("60/60 templates land inside their declared per-template stability band") as the citable figure. |
| 3 | **Pooled-tier-composition gap.** RQ5's initial Dynamic↔ULT correlation pooled all four Dynamic tiers (L1-L4) together before comparing against ULT's CC≥8-only band — an apples-to-a-narrower-slice-of-apples comparison that was never flagged as a choice until diagnosed. | Post-hoc diagnosis of a surprisingly low τ=0.143 result (`analysis/RQ5_DIAGNOSTICS.md`). | The initial framing implied pooling was a neutral default; tier-matching (Dynamic-L4 only) was found to not simply weaken the correlation but **flip its sign** (τ=0.143 → τ=-0.200, n_models=5) — meaning the pooled number's sign itself was composition-dependent, not a robust read. | Diagnosed and reported explicitly, not silently "fixed" (there is no single correct pooling choice) — both the pooled and L4-matched readings are now reported side by side with the tier-discrimination gradient (finding #3) as the explanation for why they differ. A related, proactively-applied fix: Comparison C's Dynamic control arm tier composition was pre-registered (`docs(comparison-c)` commit) *before* any POST data existed, specifically to avoid this same gap recurring post-hoc. | Every pooled-vs-tier-matched number in `RQ5_INTERPRETATION.md`/`RQ5_DIAGNOSTICS.md` is now labelled with which composition it uses. |
| 4 | **Loader had no deduplication logic at all.** `src/Analysis/loader.py::load_records()` loaded every `.jsonl` file in a results directory unconditionally — stale, superseded partial-tier retry files sitting next to their complete replacements were double-counted. | A 2026-07-26 integrity audit (`scripts/audit_result_integrity.py`) found 559 duplicate `(model_label, benchmark, instantiation_id, template_id, instance_seed, tier, K, prompting_condition)` keys; 117 of them were **content-conflicting** (two different recorded outcomes for the same key, both in API models), traced to bug #6 below. | Any StableMut@K or Kendall-τ figure computed before this fix silently double-counted ~560 problems. Comparison A/B were unaffected (A filters to L4, none of the stale files touched it; B reads ULT/PLT directly, which had zero duplicate keys). | Deduped on the natural key, keeping the newest row by `timestamp`. | `tests/test_analysis_loader.py` regression-tests the dedup logic directly. |
| 5 | **Canonical-model leaks, twice.** (a) A fine-tuned adapter's `model_label` leaked into Comparison B, appearing as a spurious 8th "canonical" model. (b) The same bug class, independently, in `analyze_stability.py` — two different adapter labels leaked into StableMut@K and pairwise Kendall τ once their own multi-instantiation data existed, inflating `n_models` for several instantiation-pairs from 7 to 9. | (a) noticed as an unexplained extra row in `comparison_b_paired.csv`. (b) noticed via the same "n_models" count looking wrong once traced back through why an earlier 8-vs-9-vs-7 discrepancy existed in a frozen snapshot table. | (a) inflated Comparison B's reported model count. (b) inflated `n_models` for 3 of the 6 N=4 stability pairs and moved the mean pairwise τ point estimate (0.675 → 0.635) purely from removing the leaked adapters, no new data. | Both fixed by filtering to `CANONICAL_MODELS` (`scripts/coverage_matrix.py`) immediately after `load_records()`. | `tests/test_canonical_models_boundary.py` covers all three consuming scripts (`build_comparison_tables.py`, `analyze_stability.py`, and StableMut@K itself) in one regression test. |
| 6 | **Tier-resume race.** `src/eval/test_gen_runner.py::_find_resume_file` matched an in-progress/retry job to its output file using only `(model_label, benchmark, prompting_condition, instantiation_id)` — not tier. A later L1L2 retry job (job 9468234, 2026-07-23) resumed into an already-running L3L4 job's own output file, and vice versa (2026-07-24), producing duplicate — sometimes content-conflicting — rows for the same (template_id, instance_seed). | Found via real job logs while investigating unexplained duplicate rows (feeds directly into bug #4's 117 content-conflicting keys). | No rows were *lost* (a separate coverage-matrix check confirmed every in-scope cell complete), but the affected rows' recorded outcomes were ambiguous between two different job runs until the loader's timestamp-based dedup resolved it. | `_find_resume_file` now keys on `_tier_signature()` (e.g. `L1L2` vs `L3L4`) in addition to the existing fields. | `tests/test_gen_runner_resume.py` regression-tests the tier-keyed matcher directly; CLAUDE.md additionally documents the operational rule (never submit two configs for the same model/instantiation with overlapping runtimes unless tiers differ or this fix is confirmed present). |
| 7 | **Unapplied thin-cell filtering.** Comparison A/B's headline Mut@K numbers were reported without any visibility into how many baseline-passing problems each model's own mean was actually averaged over — some were single or low-double-digit counts. | Explicit methodological review (external, 2026-07-30) asked for an `n_defined` floor to be applied and reported, not just computed. | No number was factually wrong, but several headline comparisons (e.g. Comparison A's 5-model result) rested partly on models with `n_defined` as low as 1 (Qwen 7B on Dynamic-L4) without that being visible anywhere in the reported table. | `THIN_N_DEFINED=20` introduced; every Comparison A/B table now reports both the unfiltered and thin-cell-excluded versions side by side, with the thin models named explicitly. | The threshold and its rationale are documented once (`scripts/build_comparison_tables.py`, `scripts/analyze_rq5_diagnostics.py`) and reused everywhere via the same constant, not re-derived per script. |
| 8 | **Metric-definition mismatch with the ULT/PLT paper.** This project's pre-registered Mut@K conditions on `baseline_passed=True` (excludes non-passing rows from the mean). An initial resolution of this exact question (2026-07-30), based on an LLM-summarized reading of the ULT/PLT paper, concluded the paper's own methodology used the *unconditional* (zero-fill) definition and that `coverage_adjusted` — not the pre-registered primary — was "the metric that actually matches the paper." | A follow-up, deliberately more rigorous pass (2026-08-03) re-fetched the paper's raw text directly (not through an LLM summarizer) and, crucially, also fetched and read the paper's own **published code**. The code (`Ray/main.py::mutation_statistic()`) divides by the baseline-passing count, not the total benchmark size — contradicting the paper's own prose and matching this project's pre-registered primary instead. | The 2026-07-30 conclusion was one-sided (checked only the paper's prose, never its code) and stated an inference as settled fact. Every place that had cited "coverage_adjusted matches the ULT paper's methodology" without qualification needed revision. | The pre-registered primary was **not** swapped (per explicit instruction not to retroactively change it) — `coverage_adjusted` is now reported everywhere as a "definition-matched co-primary," with the caveat that it matches the paper's *prose*, not its *code* (which matches this project's own primary instead). Algebraic proof that `coverage_adjusted` exactly equals the zero-filled reading added, verified to floating-point precision against the actual data. | `analysis/RQ5_CROSS_DEFINITION_AUDIT.md` documents both pieces of evidence side by side with verbatim quotes and file:line code citations, explicitly flagged as an unresolved paper-vs-code contradiction rather than picked one way — intended to prevent a future pass from re-asserting either side as settled without re-checking both. |
| 9 | **OpenAI Batch API discount never applied to `cost_usd`.** `scripts/process_batch.py` (the only script that scores OpenAI batch-derived rows) called `compute_cost()` with the standard real-time per-token rate; the Batch API's 50% discount was never applied, despite 100% of this script's rows being batch-derived. | Reconciling the logged `cost_usd` total ($106.30 across GPT-5/-mini's ULT/PLT + backfill batches) against an independent pre-flight cost estimate computed directly from token counts and the batch rate (`analysis/OPENAI_COST_AND_BILLING.md`'s $39-60 band) — halving the logged total landed within $1.68 of the estimate's midpoint, confirming the exact 2x mechanism. | Every `cost_usd` this script had ever written (~4,600 rows) was exactly 2x the real billed cost. | Fixed going forward (`_BATCH_DISCOUNT = 0.5` multiplier added). **Not corrected retroactively** — `cost_usd` is a logged-at-the-time field, not silently rewritten, same policy as bug #10 below. | Documented in `CLAUDE.md`'s Hard Rules with the exact arithmetic proof, so any future script summing `cost_usd` across these historical rows knows to expect a 2x-too-high number. |
| 10 | **Gemini's "thinking" tokens never counted in `cost_usd`.** `gemini-3.1-pro-preview` is a thinking-enabled model — Google bills internal reasoning tokens (`usage_metadata.thoughts_token_count`) separately from the visible response, at the same output-token rate. `src/models/gemini_model.py` only ever read `candidates_token_count` (the visible response). | Reconciling this project's own logged `cost_usd` sum across every Gemini row, all benchmarks (**$11.88**) against Google AI Studio's actual billed total for the same window (**£34.53, ≈$44**) — a ~4x gap, confirmed structurally by reading the SDK's own `GenerateContentResponseUsageMetadata` type definition directly (it has a `thoughts_token_count` field this project's code simply never accessed). | Every `cost_usd` this model had ever logged (~800 rows) undercounted real spend by roughly 4x, concentrated entirely in the thinking-enabled Pro Preview model (`gemini-3.1-flash-lite` isn't a thinking model and its own logged sum was already close to accurate). | Fixed going forward (`gemini_model.py` now adds `thoughts_token_count` into the cost calculation; `output_tokens` itself is left meaning "visible response tokens" for cross-provider comparability, with the thinking-token count preserved separately in `runtime_info` for audit). **Not corrected retroactively**, same policy as bug #9. | Regression tests added (`tests/test_gemini_model.py`) covering both the thinking-token and zero-thinking-token cases — the prior tests' mocked API response was a bare `MagicMock` that would have silently absorbed this exact bug forever. |
| 11 | **A generating script's own prose went stale while its tables stayed live.** `scripts/analyze_rq5_diagnostics.py` computed every table dynamically from disk, but five separate sentences of surrounding prose (its own docstring, the file's opening paragraph, three narrative asides) had the *pre-registered result's original numbers* (`tau=0.143, n=7`, `tau=0.905`, `n_models=7 per pair`) written as literal strings rather than computed values. | Re-reading the regenerated `RQ5_DIAGNOSTICS.md`'s own opening paragraph against its own tables, immediately after the 2026-08-07 data landing had already moved the tables to the new numbers — the prose still claimed the old ones. | Nothing in the underlying data or tables was wrong — but any reader who quoted the file's own narrative sentences (rather than its tables) would have cited stale figures, on a file whose whole purpose is to be the live, current diagnostic reference. | Every cited figure now computed live from the same data the tables use (a shared `_primary_res`/`res_adj` pattern), verified via a full grep sweep for literal old values after the fix. | This is the same failure mode CLAUDE.md already names for `archive_diversity_audit.py`'s hardcoded README summary — a script whose main loop is correctly dynamic can still have hand-written prose sitting next to it that silently doesn't update; grepping a regenerated file's own opening paragraph against its own tables after any data landing is now the concrete check this project uses to catch it. |

**Pattern worth naming explicitly**: bugs #2, #5, #7, and #11 all share the
same shape — a number was reported without the visibility needed to
sanity-check it (a hardcoded total, an unfiltered model list, an invisible
sample size, stale prose next to a live table). The recurring fix has been
the same in each case: make the previously-invisible or previously-static
quantity an explicit, computed-live value rather than trusting the
aggregate — or the prose — alone. Bugs #9 and #10 are a related but
distinct shape: not an invisible quantity, but an entire *component* of a
cost calculation that was never read from the API response at all,
findable only by reconciling this project's own logged total against an
independent, real-world source (a pre-flight token-based estimate for #9,
the provider's own billing dashboard for #10) — a reminder that internal
consistency checks alone cannot catch a bug that's consistently wrong in
the same direction every time.

---

## Reconciliation against `PROJECT_BRIEF.md`

Checked section by section for places where the brief's stated design no
longer matches what was actually done. Most of the brief is current — its
§11 ("Deviations from the original roadmap") already tracks the major
process changes (instantiation count 5→4, the Gemini model substitution,
the Comparison C two-experiment framing) and does not need correction here.
The gaps found while writing this document:

- **§5.4's metric table states "Mutation score | Mut@K | Killed / total
  mutants (raw); validated variant divides by total − est. equivalent" as
  the headline metric, with no mention of the conditional/exclude vs
  unconditional/include-as-zero distinction this document's §2 and
  `RQ5_CROSS_DEFINITION_AUDIT.md` treat as load-bearing.** The brief's
  phrasing ("killed / total mutants") most naturally reads as this
  project's `coverage_adjusted`/unconditional definition, but the metric
  actually used as the pre-registered primary throughout Comparison A/B
  and RQ5 is the *conditional* one (mean over baseline-passing rows only,
  §2). **This is worth an explicit brief update**: either add a sentence
  clarifying that the headline Mut@K is conditional on `baseline_passed`,
  or rename the brief's description to match what §2 documents as
  primary. As written, a reader relying on the brief alone would not know
  the two definitions exist, let alone which one is primary.
- **§5.4 also does not mention `coverage_adjusted` at all** — it is not a
  metric that existed at brief-writing time; it was introduced later as a
  robustness re-scoring and has since become a formally reported
  co-primary (§2 above). Worth adding as a named metric in §5.4 given how
  much of §4's findings 1, 5, and 6 depend on it.
- **§3.1's H1 test ("paired Wilcoxon signed-rank, dynamic vs ULT mutation
  score at model–problem level") is not what is actually computed.**
  `src/Analysis/comparison.py`'s own module docstring already flags this
  directly: Dynamic and ULT/PLT share no problem identity, so the actual
  implemented test pairs by **model**, not model–problem — one observation
  per model (that model's mean Mut@K on each side), Wilcoxon across the
  ≤9 model-level pairs. This is a sensible, disclosed adaptation (the
  code docstring explains why), but §3.1's phrasing should be corrected to
  say "at model level" rather than "at model–problem level" so the two
  documents don't describe different tests.
- **§9's data schema list (`mutants_dropped_for_import_failure`) matches
  the actual field name exactly** — no gap there, confirmed while writing
  §2 above.
- **§5.5's equivalent-mutant handling ("Default = raw score (pessimistic,
  comparable). Validation = 30 mutants/tier hand-inspected (120 total)")
  is a DIFFERENT thing from the ULT/PLT paper's own "non-equivalent
  mutants" language** that `RQ5_CROSS_DEFINITION_AUDIT.md` §1c found has
  no corresponding filtering mechanism in the paper's own code. Worth a
  one-line cross-reference in §5.5 noting that this project's own
  equivalent-mutant handling (a validated-sample estimate) and the ULT
  paper's stated-but-unimplemented "non-equivalent mutants" language are
  not the same thing and should not be assumed comparable.
- **No mismatch found** between the brief's §6 model roster and what
  `scripts/coverage_matrix.py::MODEL_SPECS` actually encodes — both list
  exactly the same 9 models with the same labels, and §6's own text
  already documents the Gemini substitution and the 2026-07-26
  model-ID consistency re-check. This document's §5 Gemini-Pro-L4 finding
  is a data-completeness issue, not a roster mismatch.
