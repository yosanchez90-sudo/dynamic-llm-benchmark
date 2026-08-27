# Supporting Report

**ECS8056 MSc AI Themed Research Project (25/26)**

**Memorisation-Robust Benchmarking of LLM Test Generation: A Dynamic, Template-Based Benchmark with Complexity-Tiered Mutation Analysis**

Yohan Sneider Sanchez Vega (40492566)
Supervisor: Pinzhen Chen
School of Electronics, Electrical Engineering and Computer Science, Queen's University Belfast

This report's title and the paper's own ("Dynamic, Template-Based Benchmarking Resists Contamination-Induced Score Inflation in LLM Unit-Test Generation") describe the same project, DyMuT, from two angles: this title names the module-lifecycle artefact this report documents, the paper's names the research contribution and finding.

---

## 1. Project development

### 1.1 Research questions and hypothesis

Six hypotheses, pre-registered in `docs/Approved_Hypotheses.md`, drive this project. Section 5 states their verdicts. The wording below compresses each approved prediction to one line, see that file for the full text.

| # | RQ | Approved prediction |
|---|---|---|
| H1 | RQ1 | Dynamic mutation scores are lower than static, CC-controlled (Test 1: Dynamic vs ULT). The leaked twin PLT scores higher than decontaminated ULT (Test 2) |
| H2 | RQ1 | Fine-tuning a small open-source model on a static benchmark's ground truth inflates its static-benchmark score more than its dynamic-benchmark score |
| H3 | RQ2 | Mean mutation score never increases from tier L1 to L4 |
| H4 | RQ3 | The static-dynamic score gap is larger at L1-L2 than at L3-L4 |
| H5 | RQ4 | Kendall's τ between model rankings across N=5 dynamic-benchmark instantiations exceeds 0.7 |
| H6 | RQ5 | Dynamic mutation score correlates positively but imperfectly with an external code-generation proxy's Pass@1, more weakly than the static benchmark's correlation with the same proxy |

### 1.2 Where this project sits

This project builds DyMuT (Dynamic Mutation-based Testing), a benchmark for LLM unit-test generation, and tests whether it resists contamination-induced score inflation better than a state-of-the-art static alternative. Concretely, this project does:

- Template-based, seeded regeneration of fresh problem instances at evaluation time.
- A mutation-testing oracle as the scoring mechanism, in place of coverage or a fixed reference suite.
- An observational and a causal contamination comparison against the current static state of the art. The observational comparison measures nine models against DyMuT, ULT, and ULT's leaked twin PLT. The causal comparison fine-tunes a small open-source model on ULT's ground truth and measures whether the resulting score inflation transfers to DyMuT.
- A construct-validity check against BigCodeBench [32], an external benchmark this project had no part in building, confirming DyMuT measures a capability an independent instrument recognises.

### 1.3 The pipeline, end to end

Section 2 verifies this pipeline phase by phase. Here is what it does, in one diagram:

{{IMAGE:paper/supporting_report/media/flow_diagram_handdrawn.png|Figure 1. DyMuT's pipeline, from template corpus to hypothesis test. Steps 6-7 are the two scoring gates. Step 9 feeds Comparisons A, B and C, which in turn feed the six hypothesis tests.}}

### 1.4 Basic flow sample

A hand-authored template:

```
def {FN_NAME}({ARG}):
    """{DOCSTRING}"""
    if {ARG} > {THRESHOLD}:
        return {ARG} * {FACTOR}
    return {ARG}
# domain: THRESHOLD in {0,5,10}, FACTOR in {2,3}, names from identifier bank
# smoke_test_inputs: [3, 7]
```

`instantiate(seed=1101)` substitutes the sampled values and produces concrete, runnable code. That function is the oracle for this problem: there is no separate "reference implementation" sitting alongside instance 1101, the instantiated function is the reference implementation, correct by construction because its semantics came from the hand-written template.

```
def scale_above(value):
    """Return value doubled when it exceeds 5, otherwise unchanged."""
    if value > 5:
        return value * 2
    return value
```

Corpus validation: CC = 2 (the L2 band is 2 to 3), oracle smoke test `scale_above(3) == 3`, `scale_above(7) == 14` both hold. Admitted to the corpus. Three mutants are precomputed once here and reused by every model, for fairness and speed: M1 `>` to `>=`, M2 `*` to `+`, M3 the constant `5` to `6`.

Three models get the same prompt, built from the real system instruction every problem in this project uses, Dynamic and ULT/PLT alike (section 1.6):

```
SYSTEM_INSTRUCTION = (
    "You are an expert Python developer writing a pytest test suite. "
    "You are given a Python function. "
    "Write a complete pytest test file that thoroughly tests this function, "
    "covering normal cases, edge cases, and boundary conditions. "
    "IMPORTANT: you must import the function under test with exactly "
    "`from under_test import <function_name>` -- do NOT copy, redefine, or "
    "reimplement the function in your test file. "
    "Output only the test file, starting with the import statement."
)
```

**Model A**:
```
from under_test import scale_above
def test_above():    assert scale_above(7) == 14
def test_below():    assert scale_above(3) == 3
def test_boundary(): assert scale_above(5) == 5
```
Runs and collects (`exec=True`), passes against the original function (`baseline_passed=True`). Against the mutants: M1 makes `scale_above(5)` return 10, so `test_boundary` fails, killed. M2 makes `scale_above(7)` return 9, killed. M3 (threshold 6): all three assertions still hold, since none of the three inputs sits at the new boundary, survived. `Mut@K = 2/3`.

**Model B**:
```
from under_test import scale_above
def test_it(): assert scale_above(7) == 7
```
Valid Python, imports fine (`exec=True`), but `scale_above(7)` is really 14, so it fails against the correct function (`baseline_passed=False`). `Mut@K` is undefined, not zero: asking "does it fail on the mutant" makes no sense when it already fails on the original. This is the same mechanism behind a real, project-wide pattern: Mistral-7B's actual dynamic-benchmark exec_rate is 96.7% against only a 1.7% baseline_pass_rate, most attempts run cleanly and still fail the baseline gate, so most of them never reach a mutant at all.

**Model C**: misspells the import, `ImportError` at collection, `exec=False`, never reaches the baseline gate.

A model that had memorised a previous instantiation of this template would have absorbed constants like `threshold=5, factor=2`. A fresh seed changes the threshold, the factor, the identifier names, and the docstring's wording, so memorised assertions now disagree with the new oracle: `baseline_passed=False`, `Mut@K` undefined, memorisation buys nothing. Comparison C (section 1.7) demonstrates the same mechanism from the other direction: on ULT, whose problems are fixed forever, memorisation took a model from 0.9% to 100% baseline-pass, because the memorised answers stayed valid. Dynamic has no fixed artefact to memorise.

### 1.5 Equivalent mutants

An equivalent mutant is one no test could ever kill, because the domain makes the change unobservable, for example `len(x) > 0` mutated to `len(x) != 0` when length is never negative. These sit in `Mut@K`'s denominator and deflate every model's score regardless of test quality. In the example above, M3 survived because no test exercised the value 6, a real test-suite weakness, and killable in principle, not an equivalent mutant. Section 1.8 shows the real, still-unfilled inspection sheet this project uses to estimate how much of that denominator is equivalent, not weak, mutants.

The benchmark's actual scale, and how one instantiation's per-model scores combine into the cross-instantiation stability metric StableMut@K, sketched structurally (not filled in with live numbers, `analysis/STABILITY.md` and section 4.3's H5 discussion carry those):

{{IMAGE:paper/supporting_report/media/instantiation_structure_sketch.png|Figure 2. One instantiation is 4 tiers x 15 templates x 5 seeds = 300 problems. N such instantiations, each scored independently, give each model N Mut@K values. Their mean and standard deviation are StableMut@K, the RQ4/H5 stability metric section 4.3 discusses.}}

### 1.6 How ULT and PLT problems are prepared

Section 1.4 traces a dynamic problem from template to test file. ULT and PLT reach the same `TestGenProblem` object by a different route: adapting an existing artefact instead of building a fresh one.

A real ULT record, abridged:

```
{"func_name": "Velocidad", "code": "def Velocidad(d, f): ...",
 "prompt": "Determina la velocidad de las bolas", "cyclomatic_complexity": 13}
```

`src/data/ult_plt.py::load("ult")` turns every record like this into the same `TestGenProblem` the dynamic path produces: recompute cyclomatic complexity from `code` (never trust the shipped field, it disagrees with a live recompute on 26.7% of all 3,909 ULT records, and would have wrongly admitted 233 of them past this project's CC≥8 gate), drop anything still below `CC_MIN=8`, tag the survivor `tier="L4"`, drop any PLT record whose task_id also appears in ULT (PLT's `code` is a superset, so this keeps Comparison B non-circular), and for models scored against a fixed subsample, not the full pool, draw it once by a seeded quantile-stratified sample and freeze it to `data/raw/ult_plt/subsample_manifest.json` so every model sees the identical 400-problem `core_400` set. Mutants are generated the same way as Dynamic, scoped to the named function only (`scope_fn_name`) since a real-world `code` blob can carry helper functions that must never be mutated.

The dynamic path builds a problem: a new seed produces a problem that did not exist before. The ULT/PLT path adapts one: the same 400 real functions every run. Both call the same message builder from section 1.4. (A different, unrelated "reconstruct": `process_batch.py::build_problem_map()` re-derives an already-built `TestGenProblem` from its own key when an OpenAI batch result returns, not a build-vs-adapt distinction.)

**Repairing ULT's ground truth for fine-tuning.** ULT's own shipped tests are not reliable enough to train on directly. `scripts/repair_ult_ground_truth.py` ran all 2,986 CC≥8 ULT records through the real scoring harness (section 2.3) and classified each:

| Category | Count | % |
|---|---|---|
| Clean out of the box | 251 | 8.4% |
| Repaired (wrong literal, rewritten to the real output) and verified | 602 | 20.2% |
| Repaired but degenerate (same output for every input) | 164 | 5.5% |
| Shape not repairable, not guessed at | 927 | 31.0% |
| Structural (code itself doesn't run), never repaired, would diverge from the already-scored pre-fine-tune baseline | 1,031 | 34.5% |
| Verify failed or flaky | 11 | 0.4% |

1,017 repaired-and-verified pairs, 1,014 after a tokenizer-length filter (3,072-token training context). Of the 400 `core_400` problems, 112 have a verified pair (Comparison C's seen-ULT). The remaining 288 are held out as unseen-ULT.

### 1.7 The three comparisons side by side

One table, before the results in section 4, places the project's three central comparisons next to each other: what each one compares, what data it draws on, which hypothesis it tests, and what it found.

| | Comparison A | Comparison B | Fine-tuning probe (Comparison C) |
|---|---|---|---|
| Compares | DyMuT's hardest tier against ULT | ULT against its leaked twin, PLT | One model, before and after fine-tuning on ULT's ground truth |
| Design | Observational: the same 9 canonical models scored on both benchmarks, no intervention | Observational: the same 9 canonical models scored on both benchmarks, no intervention | Causal: Qwen2.5-Coder-1.5B-Instruct, LoRA fine-tuned, scored pre and post on ULT, PLT, and Dynamic |
| Data | DyMuT L4 vs ULT `core_400`, paired at model level | ULT vs PLT `core_400`, CC-band matched, paired at model level | 112 seen-ULT, 288 unseen-ULT, PLT `core_400`, DyMuT L1-L3, DyMuT L4, pre and post |
| Tests | H1 Test 1: dynamic scores lower than static, controlling for complexity | H1 Test 2: leaked PLT scores higher than decontaminated ULT | H2: fine-tuning inflates the static score more than the dynamic score |
| Statistic | Paired Wilcoxon signed-rank, rank-biserial effect size | Paired Wilcoxon signed-rank, rank-biserial effect size | 2×3 difference-in-differences on `baseline_pass_rate`, bootstrap CI |
| Verdict | Not supported: effect_r = -0.167, p=0.7422, opposite to the predicted direction | Supported in direction on every reading. Significance depends on which reading is quoted after Holm correction (section 2.9) | Supported, the strongest result in the project: +99.1pp on seen-ULT, +13.8pp on PLT after subtracting a generic fine-tuning control, 0.0pp on DyMuT L4 |

Full statistics, caveats, and the paper-ready wording for all six hypotheses are in section 5. `analysis/HYPOTHESIS_DEVIATIONS.md` is the source these figures are read from.

### 1.8 Algorithms

Readable pseudocode for the four procedures behind sections 1.4, 1.6, and 1.7, each with the real file and function a reader can open to see the executable version. Kept under twenty lines each, so some real error handling and logging is left out. The cited modules carry the full version.

**(a) Dynamic instantiation** (`src/data/test_gen.py::load`, `template_corpus/templates/_smoke/engine.py::instantiate`)

```
for tier in tiers:
    for template in templates_in(tier):
        for base_seed in instance_seeds:
            seed = instantiation_seed * 1000 + base_seed
            instance = instantiate(template, seed)       # engine.py
            if instance.validation_errors:
                skip                                       # never silently coerced
            fn_name = extract_function_name(instance.source)
            mutants = generate_mutants(instance.source)    # mutation_adapter.py
            messages = build_messages(instance.source)     # same builder as ULT/PLT
            emit TestGenProblem(template_id, tier, seed, instance.source,
                                 instance.docstring, mutants,
                                 oracle=template.oracle, messages)
```

**(b) ULT/PLT adaptation** (`src/data/ult_plt.py::load`)

```
records = read_jsonl(benchmark)                     # 3,909 for ULT
if benchmark == "plt":
    drop records whose task_id appears in ULT        # keeps Comparison B non-circular
for record in records:
    fn_node = parse(record.code).find(record.func_name)
    cc = compute_cc(fn_node)                          # recomputed, shipped field ignored
    if cc < CC_MIN:                                   # CC_MIN = 8
        drop record
if a fixed subsample is requested:
    candidates = stratified_sample(candidates, seed)  # or read a pinned manifest
for record in candidates:
    mutants = generate_mutants(record.code, scope_fn_name=record.func_name)
    emit TestGenProblem(f"{PREFIX}-{task_id}", tier="L4", instance_seed=task_id,
                         record.code, record.prompt, mutants, oracle=None, messages)
```

**(c) Scoring, shared by both benchmarks** (`src/eval/test_gen_scorer.py::score_problem`)

```
extract test file from the model's raw response
sanitize: strip a reimplementation of the function under test, ensure the import line
if not collect_ok(function, test_file):               # EXEC GATE
    return exec_ok=False, mutation_score=None
if not run_pytest(function, test_file) passes:         # BASELINE GATE
    return exec_ok=True, baseline_passed=False, mutation_score=None
killed = dropped = 0
for mutant in mutants:                                  # parallel, one thread per mutant
    if mutant does not import cleanly:
        dropped += 1; continue                           # neither killed nor survived
    if run_pytest(mutant, test_file) fails:
        killed += 1
mutation_score = killed / (len(mutants) - dropped)
```

**(d) The contamination probe** (`src/Contamination/did.py::compute_did`)

```
for benchmark in {control=Dynamic, treatment in {ULT, PLT}}:
    pre_mean  = mean(metric over PRE rows for this benchmark)
    post_mean = mean(metric over POST rows for this benchmark)
control_delta = post_mean(Dynamic) - pre_mean(Dynamic)
for treatment in {ULT, PLT}:
    delta = post_mean(treatment) - pre_mean(treatment)
    DiD   = delta - control_delta
    ci    = bootstrap_percentile_ci(pre, post, pre_control, post_control, n_boot=2000)
emit DiD, ci per treatment benchmark                     # DiD > 0, CI excluding 0: contamination signal
```

**A complete, unedited example.** Section 1.4 walks through a constructed, hand-simplified illustration. Here is a real one: the raw test file Claude Sonnet 4.6 produced for an actual dynamic-benchmark problem (`L3-clamp-seq-001`, a threshold-style function like section 1.4's), exactly as `extract_test_file()` extracted it from the model's response, nothing added or removed:

```
from under_test import sum_values

def test_empty_list():
    assert sum_values([]) == []

def test_all_below_floor():
    assert sum_values([1, 2, 3, 4, 5, 6, 7]) == [8, 8, 8, 8, 8, 8, 8]

def test_exactly_at_floor():
    assert sum_values([8]) == [8]

def test_one_above_ceiling():
    assert sum_values([34]) == [33]

def test_original_list_not_modified():
    original = [1, 15, 50]
    original_copy = original.copy()
    sum_values(original)
    assert original == original_copy

# ... 25 more, same shape: one assertion per boundary/edge case
```

Scored: `mutants_total=21`, `mutants_killed=17`, `mutation_score=0.8095`. 30 tests, all passing. 17 of 21 mutants caught, 4 real survivors.

**The equivalent-mutant inspection sheet.** Section 4.3 discloses this hand-inspection was not complete when this report was written. 120 mutants are drawn (fixed seed) and staged in `analysis/equiv_mutants/inspection_sheet.xlsx`, one row per mutant, `verdict` column still blank in every row:

```
template_id: L1-arithmetic-003   operator: AOR
  -    return item * x - x * 1
  +    return item * x + x * 1
verdict: (not yet filled in)
```

### 1.9 Complementary literature review

Sections 1.1-1.8 describe what this project built and why. This section places that work against the field it sits in: which prior systems attempt something similar, what each one cannot do that motivated a design choice here, and which literature shaped a specific decision already described above. It complements the paper's own related-work section rather than repeating it: the paper argues the gap in three paragraphs; this section shows the comparison the argument rests on, and evaluates the closest individual works critically rather than only placing them on a map.

**Dynamic and contamination-resistant benchmarks.** The shared idea across this group is generating evaluation instances at test time instead of drawing from a fixed, publishable set. They differ in domain and in what "contamination-resistant" actually buys them.

| System | Generation mechanism | Domain | Contamination evidence offered | What it cannot do |
|---|---|---|---|---|
| DyVal [31] | Dynamic computation graphs sampled per evaluation | Logical/reasoning tasks | Demonstrates score stability under resampling | No execution-based oracle; not code |
| LiveBench [29] | Monthly refresh from newly published sources | Mixed (math, reasoning, coding, language) | Newer problems post-date training cutoffs | Refresh-based, not generative: static between refreshes, and the maintenance burden repeats every cycle |
| LiveCodeBench [18] | Draws from programming contests held after model training cutoffs | Code generation | Contamination window is bounded by contest date | Depends on a continuing supply of fresh contests, not a generator; existing problems still age into contamination |
| BeyondBench [27] | Generates algorithmic problems with provable correctness constraints | Algorithmic reasoning | Correctness is guaranteed by construction, similar in spirit to this project's oracle-by-construction design | Targets reasoning problems with a checkable mathematical answer, not free-form generated code artefacts like a test suite |
| MATHEMAGIC [23] | Same generative-template principle applied to mathematics | Mathematics | Demonstrates the approach transfers across at least one other domain | No code-execution oracle; a correct mathematical answer is checked differently from a passing, mutation-resistant test suite |
| LLM-as-an-Interviewer [20] | Replaces a static test set with a dialogue-driven, adaptive evaluation | General LLM evaluation | Removes the fixed artefact a static test set would be | Dialogue-driven evaluation has no notion of an executable, scoreable code artefact |
| DyCodeEval [5] | Dynamic regeneration applied to code-reasoning problems | Code reasoning | Regenerated per evaluation, same principle this project applies | Scores reasoning about code, not the quality of a generated test suite |
| Guan et al. [12] | Studies whether/when a benchmark's usefulness degrades and proposes dynamic regeneration as the fix | Code language models | Direct empirical argument for why static benchmarks decay | A usefulness study and a proposed direction, not a released test-generation instrument |
| Code2Bench [30] | Scales dynamic benchmark construction directly from real source repositories | Code generation | Scale and rigor of construction from real code | The source corpus itself is a static artefact once assembled: it inherits the same leak risk once published, which is why this project rejected the same approach (section 4.1) |

None of these nine targets unit-test generation specifically, where the artefact under evaluation is itself executable code paired with a correctness oracle, checkable by running it rather than by comparing to a reference string. That gap is what DyMuT fills, not a claim that dynamic regeneration itself is novel; the paper's own related-work section states this directly.

**LLM test-generation evaluation.** This second group evaluates LLM test-writing ability specifically, the task DyMuT also evaluates, and predates or runs alongside the dynamic-benchmarking line above.

| System | What is scored | Oracle | Contamination handling | Why not adopted here |
|---|---|---|---|---|
| EvoSuite [11] | Test-suite quality via evolutionary search (pre-LLM) | Coverage/mutation-based fitness function | Not applicable; not an LLM benchmark | Predates the LLM test-generation task this project evaluates; included as the pre-LLM search-based baseline the field moved on from |
| Pynguin [21] | Automated Python unit-test generation via search (pre-LLM) | Coverage-based fitness function | Not applicable | Same reason as EvoSuite; considered and not adopted as a comparator tool in section 3.4, since it evaluates a different (non-LLM) generation mechanism |
| TestEval [28] | LLM-generated test cases, correctness and coverage | Reference test suite / coverage | None: a fixed, published problem set | Closest test-generation benchmark by task; not adopted as the static comparator because it does not pair a decontaminated set with a leaked twin the way ULT/PLT does, so it offers no direct contamination-evidence design to reuse |
| Schäfer et al. [25] | Empirical evaluation of LLMs for automated unit-test generation | Reference/compilation-based | None | An empirical study of the task, not a released contamination-aware benchmark |
| Siddiq et al. [26] | LLM-generated JUnit tests | Reference/compilation-based | None | Java/JUnit, a different language ecosystem; no contamination design |
| Haroon et al. [13] | LLM test generation, tracked as the codebase under test evolves | Reference-based, evolution-tracked | Evolution over time is itself a form of drift-awareness, but not contamination-specific | Tracks software evolution, not contamination; a different axis of the same general problem |
| MuCoCo [7] | Code-LLM output consistency under automated mutation-style perturbation | Consistency across perturbed variants | Perturbation-based robustness check, the closest methodological parallel to this project's own mutation-based scoring | Evaluates consistency of code-generation outputs under perturbation, not the quality of a generated test suite against mutants of the function under test |
| ULT/PLT [16] | Unit-test generation on real-world functions, decontaminated (ULT) vs. deliberately leaked (PLT) | Fixed reference tests, prose-vs-code-inconsistent scoring formula (section 1.6, Finding 3 below) | The closest prior contamination-evidence design: a decontaminated set and a leaked twin, compared directly | Static once published: the same leak risk this project's own design was built to avoid, since ULT/PLT's own content is now a fixed, citable artefact |

ULT/PLT is the closest static comparator for exactly this reason, and is why it is this project's own main static baseline (section 1.6) rather than TestEval or the Schäfer/Siddiq empirical studies: it is the only one of this group that already offers a contamination-evidence design (a decontaminated set paired with a leaked twin) for this project's own design to reuse and extend with a dynamic alternative.

**Critical evaluation of the four closest works.**

*ULT/PLT [16].* The closest and most extensively used comparator, and also the subject of this project's own most substantial original finding against a third-party artefact: three independent, converging quality issues, discovered while preparing ULT for fine-tuning (section 1.6). First, only 8.4% of ULT's shipped test-and-code pairs pass this project's own scoring harness unmodified; the rest needed repair before they were usable as fine-tuning targets, and 34.5% could not be repaired at all because the shipped code itself does not run. Second, ULT's self-reported cyclomatic-complexity field disagrees with an independent, AST-based recomputation at exactly the boundary that decides whether a record clears this project's own CC-8 filter: 233 of ULT's 3,909 records that the vendor's own metadata claims exceed its stated complexity floor do not, under a first-party recompute. Third, and most consequentially for any project that cites ULT's own reported mutation-score formula, ULT's source paper's stated prose formula for mutation score contradicts its own published scoring code: the prose formula scores a non-passing suite as zero, matching this project's own coverage-adjusted definition, while the published code excludes non-passing suites from the average entirely, matching this project's own conditional definition instead. A reader who trusted only the paper's prose, without independently reading the code, would report the wrong formula as canonical, exactly the mistake an earlier pass of this project's own analysis made before a more careful re-read caught it (error-ledger bug 8). None of these three findings are reported to discredit ULT, a genuine and useful contribution; they are reported factually, with the evidence and method behind each, because a project that leans as heavily on ULT as this one does has an obligation to disclose what an independent, first-party recomputation actually found.

*Code2Bench [30].* The methodologically closest dynamic-benchmarking system in its ambition to avoid a fixed artefact, and the one rejected alternative this project's own design most needs to distinguish itself from (section 4.1). Its weakness is structural, not an implementation flaw: scaling benchmark construction directly from real source repositories means the resulting corpus, however large or rigorously constructed, is a static artefact from the moment it is assembled. Publishing it, or even using it repeatedly across evaluation rounds without regenerating from a private grammar, reintroduces exactly the leak risk dynamic benchmarking is meant to remove. This project's template-grammar approach answers the same ambition with a different mechanism: the corpus behind DyMuT is never published as a fixed set at all, only the generator and its seeds are, so there is no static artefact for a future model to absorb.

*MuCoCo [7].* The closest methodological parallel in mechanism rather than task: both MuCoCo and this project use a form of controlled perturbation (mutation, in this project's case) as the scoring instrument rather than comparison to a fixed reference answer. The difference is what is perturbed and what the perturbation is scored against. MuCoCo perturbs a code-generation model's own inputs or outputs and checks consistency of its generated code across the perturbed variants; this project perturbs the function under test and checks whether a model-generated test suite detects the resulting behavioural change. MuCoCo's oracle is agreement with itself under perturbation; this project's oracle is a per-problem reference implementation, generated by construction alongside every instance. The two approaches are complementary rather than competing: MuCoCo asks whether a code-generation model is internally consistent, this project asks whether a test-generation model's output can distinguish correct code from a broken variant.

*TestEval [28].* The closest test-generation benchmark by task (evaluating LLM-generated tests directly, the same object this project evaluates) and the clearest illustration of why task similarity alone does not make a benchmark a viable comparator here. TestEval draws its problems from a fixed, published set with no leaked-twin design and no generative regeneration mechanism, so it offers this project nothing to reuse for either of its two central comparisons (the observational contamination check against a leaked twin, or a dynamic alternative to compare against a static one). It is included here to make an honest case for the gap this project fills: a benchmark that evaluates the right task but was never designed to answer the contamination question this project asks.

**The contamination-measurement motivation.** The premise this entire project rests on, that benchmark contamination is real, common, and worth measuring rather than assumed away, comes from two sources cited throughout the paper as well as here. Sainz et al. [24] argue that contamination measurement should be standard practice for every benchmark, not an occasional afterthought; Balloccu et al. [3] supply the empirical weight behind that argument, tracing leaked benchmark references directly into closed-source model cards and quantifying how much evaluation data has already leaked into commercial training pipelines, the same leak channel this project's own AI Ethical Considerations section discloses it participates in by evaluating six closed-source APIs. Codex/HumanEval [6] is the founding code-generation benchmark and is itself reported as contaminated in later models, the clearest illustration available that even a carefully constructed static benchmark is not immune once it is widely used for long enough. Dong et al. [9] extend the same contamination question specifically to code generation, distinguishing genuine generalisation from memorisation in code-LLM evaluation, the code-specific version of the general concern Sainz and Balloccu raise.

**Trends and what they imply.** Read across both tables, the field's response to contamination has converged on one mechanism, regenerating or refreshing evaluation content so no single instance stays fixed long enough to be memorised, applied now across reasoning (DyVal, LLM-as-an-Interviewer), mathematics (MATHEMAGIC), general benchmarks (LiveBench), and code (DyCodeEval, Guan et al., Code2Bench, LiveCodeBench). What is missing from every one of these, including the code-focused subset, is a domain where the generated artefact itself carries an executable, unambiguous correctness check, so that scoring never needs a human-curated reference string that could itself become a target for memorisation. Unit-test generation is the case where this gap is solvable by construction rather than merely desirable: a test suite's job is to be executed against code, so the same execution that produces a model's score can also produce the reference implementation and the mutants it is scored against, with no separately curated answer key anywhere in the loop. This is precisely DyMuT's design (section 1.4), and it is why test generation, not reasoning or mathematics, is the domain where dynamic, contamination-resistant benchmarking and an execution-based oracle combine most naturally.

**Literature that shaped specific decisions.** Several citations above and elsewhere in this report are not background reading; they directly produced a design choice already described.

- Carlini et al. [4] establish that LLMs reproduce training sequences at rates that grow with model scale. This is the direct reason the *smallest* of the three open-source model sizes, not the largest, was chosen for the causal contamination probe (section 4.1): a clear memorisation signal, if present, is least likely to be masked by a larger model's raw capability at the smallest scale.
- Jia and Harman [19] survey the equivalent-mutant problem in mutation testing, that some mutants are semantically unkillable by any correct suite and deflate every model's score regardless of test quality. This is the citation behind section 1.5's equivalent-mutant discussion and the pre-specified, bounded correction design described there.
- Andrews et al. [1] establish mutation score as a proxy for a test suite's actual fault-detection ability, the argument behind choosing mutation score, not coverage, as this project's headline metric (section 4.1).
- McCabe [22] is the origin of the cyclomatic-complexity measure this project's four-tier design is built on (section 2.2's corpus validation).
- Angrist and Pischke [2], Efron and Tibshirani [10], and Holm [14] are the statistical foundations behind section 2.9's procedure: the difference-in-differences design, the bootstrap confidence intervals, and the Holm-Bonferroni correction respectively, each cited at the point it is used rather than only in this section.

---

## 2. Project Life Cycle, Verification and Validation

Figure 1 (section 1.3) already sets out what the finished pipeline does end to end. This section verifies it phase by phase.

### 2.1 The six gated phases, as executed

This section uses this project's own Phase 1-6 vocabulary throughout, since that is how the work was actually planned and gated. The rubric's own five lifecycle stages map onto those phases as follows, so a reader working from the rubric's own terms has a direct way in:

| Rubric stage | This project's phase(s) | Deliverable | Gate | Evidenced in |
|---|---|---|---|---|
| Planning | Phase 1 | Frozen scope, research questions, template-grammar specification | Written checklist sign-off | Section 1.1; `docs/Approved_Hypotheses.md` |
| Development | Phase 2 | Sixty validated templates, the instantiation engine | Supervisor sign-off, 2026-07-25 | Section 2.2 |
| Implementation | Phase 3 | End-to-end scoring pipeline, piloted on thirty problems | Pilot run passed | Section 2.3; Algorithm (c), Section 1.8 |
| Implementation (continued) | Phase 4 | Comparison A table, stability runs, a sensitivity sweep | Data-completeness check | Section 1.7; `analysis/COMPARISON_PROVENANCE.md` |
| Testing | Phase 5 | Comparison B (observational) and Comparison C (causal) results | Both comparisons completed, 2026-07-27 | Section 1.7; Section 4.1 |
| Evaluation | Phase 6 | The paper and this report, six hypothesis tests written up | Experimental freeze, 2026-08-12 | Section 5 |

The project plan set out six gated phases over sixteen weeks. Phase *k+1* could not start until phase *k*'s deliverable passed a written checklist. A failed gate meant dropping a lower-priority item from a fixed cut list, not slipping the schedule.

Phase 1 froze the scope, the research questions, and the template-grammar specification. Phase 2 built and validated sixty templates and the instantiation engine. Phase 3 built the end-to-end scoring pipeline and piloted it on a thirty-problem subset. Phase 4 built the main Comparison-A table, the stability runs, and a sensitivity sweep. Phase 5 ran the two contamination comparisons. Phase 6 wrote up the six hypothesis tests and produced the submission.

Phases 1 to 3 ran close to plan. From Phase 4 onward, the supervisor asked for the stability and contamination work to be brought forward, so it did not wait for Phase 5 to start in the strict order the plan set out. Early stability signal from a still-partial Comparison-A data set fed into the decision to cut the fifth benchmark instantiation on 2026-07-15, months before Phase 6 began. The construct-validity check against BigCodeBench, the "bottom-up" comparison the supervisor asked for on 2026-07-27, was designed and run as a zero-compute analysis against whatever data existed on that date, instead of waiting for a complete data set a strict phase order would have required.

Phase 2's gate closed with the supervisor's sign-off on the sixty-template corpus on 2026-07-25. Phase 5's two contamination comparisons completed on 2026-07-27. Phase 6 began at the experimental freeze on 2026-08-12: data collection for the main study closed, and the write-up proceeded on the data as it stood, not as a moving target. At that point, 172 of 180 model by tier by instantiation cells were complete, 95.6%. The one remaining gap, both Gemini models' fifth instantiation, 600 problems across eight cells, was costed at $9.60 and declined, for the reasoning in section 2.6.

{{FIGURE:project_timeline|Figure 3. Top: the six phases in planned, strict sequential order. Bottom: the four real, dated deviations described above, plotted on an actual calendar axis. The Phase 2 gate (2026-07-25) closes chronologically after the Phase-4-era stability signal that drove the 2026-07-15 cut decision -- the "brought forward, out of strict order" deviation stated in prose above, shown rather than only described.}}

### 2.2 Corpus validation

Every template's cyclomatic complexity is computed at validation time and recomputed on every instance the template generates, since parameter sampling can shift a generated instance's control-flow shape out of its declared tier, the same recompute-not-trust principle section 1.6 describes for ULT/PLT. A within-tier diversity check compares every template against every other template in its tier and flags near-duplicate structure. The full sixty-template corpus passed with zero flags. A tier-separation sanity check confirms the four tiers do not overlap in complexity, and every template's reference oracle passes a property-based smoke test before acceptance into the corpus. Mutant density is checked against a target band per tier, five to ten mutants for the trivial tier up to twenty-five to forty for the compositional tier, and the evaluated population falls inside these bands 92.9% to 100% of the time across all seeds and instantiations.

### 2.3 The scoring harness

A model's response passes through three strictly sequential stages before it produces a score: an exec gate (does the test file import and collect), a baseline gate (does it pass against the real function), and mutation scoring (how many mutants does it kill). A response that fails a stage never reaches the next one, and a row that fails the baseline gate is excluded from the mutation-score average, not counted as a zero. Algorithm (c) in section 1.8 gives the exact procedure, with the real function it corresponds to.

Untrusted code, whether a model's generated test file or a scraped ground-truth function, is always executed from an isolated temporary directory, never from the project's working directory. Section 4.2 describes the incident that made this rule necessary.

### 2.4 The test suite, made concrete

The project's automated test suite collects 152 tests across the `tests/` directory, run with pytest. 16 of these are marked `torch` (need a working torch import) and are skipped in an environment without a working CPU torch install. The other 136 run everywhere:

{{FIGURE:evidence_test_suite|Figure 4. A real run of the test suite, tail output, captured live.}}

A count alone says nothing about what the tests actually guard. Three examples below are regression tests tied to a real bug that was found, cost something, and is also entered in the error ledger (section 2.7).

**`tests/test_canonical_models_boundary.py`, guards error-ledger bug 5** (a fine-tuned adapter's label leaking into two downstream comparisons and inflating their model count):

```
def test_filter_to_canonical_drops_adapter_and_cross_family_labels():
    df = pd.DataFrame({
        "model_label": [
            CANONICAL_MODELS[0],
            CANONICAL_MODELS[0] + "__ft_qwen1_5b_lora_ult_30ep",
            "deepseek-ai__deepseek-coder-6.7b-instruct",
        ],
        "value": [1, 2, 3],
    })
    out = filter_to_canonical(df)
    assert list(out["model_label"]) == [CANONICAL_MODELS[0]]
```

**`tests/test_analysis_loader.py`, guards error-ledger bug 4** (no dedup logic, so a stale retry file sitting next to its replacement was double-counted. Roughly 560 rows were affected before the fix):

```
def test_stale_rerun_is_superseded_by_newer_row(tmp_path):
    _write(tmp_path / "old.jsonl", [_record(mutation_score=1.0, timestamp="2026-07-14T14:10:33+00:00")])
    _write(tmp_path / "new.jsonl", [_record(mutation_score=0.5, timestamp="2026-07-23T13:35:58+00:00")])

    df = load_records(tmp_path, benchmark="dynamic")

    assert len(df) == 1
    assert df.iloc[0]["mutation_score"] == 0.5
    assert df.iloc[0]["source_file"] == "new.jsonl"
```

**`tests/test_gen_runner_resume.py`, guards error-ledger bug 6** (the resume matcher ignored tier, so an L1L2 retry job resumed into an L3L4 job's own output file and vice versa, producing conflicting rows for the same problem):

```
def test_resume_does_not_cross_tier_groups(tmp_path):
    l3l4_file = tmp_path / "modelX__dynamic__zero_shot__inst4__tiersL3L4__20260714T141409.jsonl"
    _write(l3l4_file, [{"template_id": "L3-bucket-001", "instance_seed": 4101}])

    resume_path, done = _find_resume_file(
        tmp_path, "modelX", "dynamic", "zero_shot", "4",
        n_shards=1, shard_id=0, tier_sig="L1L2",
    )

    assert resume_path is None
    assert done == set()
```

None of the three fails today. Running them on every change, not just once after the fix, is the point.

### 2.5 The citation gate

Every hand-written number in the project's analysis documents and in the paper is checked by `scripts/check_doc_citations.py` against the project's live, auto-regenerated output: a number that no longer matches anything the pipeline currently produces fails the check. This exists because numbers in this project have moved, more than once, purely from a bug fix or new data arriving, with no change to the analysis method, and a hand-written document can silently fall out of sync with the table beside it. Section 2.8 shows what the check actually looks for and a real run of it.

### 2.6 Pre-registration discipline

Each hypothesis test's design was committed to a written analysis plan before the result existed. The construct-validity check against BigCodeBench is a direct example. Its plan was written and committed before any correlation was computed, including the specific validity band the result would be judged against. The result contradicted the plan's prediction in one respect: DyMuT's agreement with BigCodeBench turned out to be at least as strong as the static benchmark's, not weaker, and the result is reported as found, including the failed prediction.

This discipline also produced the reasoning behind declining the fifth benchmark instantiation for both Gemini models at the 2026-08-12 freeze. A quantified $9.60 was available to close the gap. It was declined for two stated reasons, both checked before the decision, not assumed: the stability verdict does not change at any plausible resulting value, and a diagnostic check on the existing data showed several models clustered within a spread smaller than their measurement noise, so more data was expected to move the result further from the threshold, not closer to it.

### 2.7 The error ledger

Every measurement bug found in the project is recorded here, with what it cost, how it was caught, and what stops it recurring. Eleven real bugs were found, several by reconciling against an independent source, not by re-reading the same code a second time. None is folded into a later number without a record.


| # | What broke | How it was found | What it cost | How it was fixed | What stops it recurring |
|---|---|---|---|---|---|
| 1 | An uncommitted change to a decoding setting, `no_repeat_ngram_size=4`, banned repeated four-word sequences across the full prompt and response. The system prompt contains the import line every response must reproduce, so a model that followed the instruction correctly had that line corrupted on generation. | An apparent fine-tuning collapse was investigated and confirmed at fifty problems: zero of fifty clean import lines with the setting on, fifty of fifty with it off. | Three of six supplementary fine-tuning conditions showed a fabricated collapse. Roughly a week of GPU sweeps ran against the broken, uncommitted script before the fix landed. | The setting was dropped from the evaluation script. Old result files were quarantined in place, not edited, matching the project's append-only convention. | Every model call now logs its full resolved decoding configuration, including inherited defaults and their source, so a setting like this one is visible in the run record even before it is committed to git. |
| 2 | Two validator scripts reported success without checking anything. One printed a fixed pass count regardless of what ran. The other pointed at a stale path, so its loop validated zero templates while still printing as if it had run. | Found by reading the validator scripts, since neither one's output would ever have shown the fault. | Any claim that the template corpus passed validation, made before this fix, could not be trusted. | Both scripts now compute their totals and their checked path from the current run, not from a fixed string or a stale constant. | A later thirteen-script audit of every validator in the project, described below, checked for the same pattern across the codebase. |
| 3 | The first construct-validity correlation pooled all four complexity tiers together before comparing against a static benchmark that contains only the hardest tier. | The pooled result looked low and was traced back to this composition choice. | Matching the comparison to the one tier both benchmarks share did not just weaken the correlation. It reversed its sign. | Both the pooled and the tier-matched readings are now reported side by side, with the composition of each stated. | Every correlation in the project's analysis documents is labelled with the tier composition it uses. |
| 4 | The result loader had no deduplication logic. Every file in a results directory was loaded without a check for a stale, superseded retry sitting next to its replacement. | An integrity audit found several hundred duplicate keys, some with two different recorded outcomes for the same problem. | Any stability or ranking figure computed before this fix double-counted a meaningful share of the affected rows. | The loader now keeps the newest row by timestamp for each unique problem key. | A regression test covers the deduplication logic. |
| 5 | A fine-tuned model's label leaked into two downstream comparisons, appearing as an extra canonical model that was never meant to be counted. | Noticed as an unexplained extra row in one comparison table, then traced to the same cause in a second script. | Two stability figures were computed with an inflated model count until the leak was found. | Every downstream script now filters to the canonical model list right after loading results. | One regression test covers every script that consumes the canonical model list. |
| 6 | A retry job's file matcher keyed on model, benchmark, and instantiation, but not tier, so a retry for two lower tiers could resume into a running job's file for the two higher tiers, and the reverse. | Found through job logs while investigating duplicate rows, the same duplicates behind bug 4. | No row was lost, but the affected rows carried a conflicting outcome until the loader's timestamp-based fix resolved it. | The matcher now keys on the tier set as well as the other three fields. | A regression test covers the tier-aware matcher, and the operational rule is written into the project's standing instructions. |
| 7 | Comparison tables reported a mean mutation score with no visibility into how many problems that mean was taken over. Some of those counts were in the single digits. | Raised in an external methodological review, which asked for a visible floor on sample size. | No number was factually wrong, but a reader had no way to tell a mean over three hundred problems from a mean over one. | A fixed threshold was introduced, and every comparison table now reports both the full and the threshold-filtered version, with any thin model named. | The threshold and its reasoning are defined once and reused everywhere, not re-derived per script. |
| 8 | An early reading of the static benchmark's mutation-score formula, based on a summarised reading of its paper, concluded the paper's method matched one of this project's two metric definitions. | A more careful pass re-read the paper's text and also read its published scoring code, which divides the score a different way than its prose describes. | The earlier conclusion had checked one side of the paper's contradiction, its prose, not its code, and stated a guess as settled fact. | The project's primary metric was not changed. Both readings are now reported side by side, each labelled with which part of the source paper it matches. | An audit document holds both pieces of evidence with quotes and code references, so a future check has to weigh both again instead of repeating one side. |
| 9 | A batch-processing script never applied the batch discount to its logged cost figures, so every cost total it wrote was twice the real billed amount. | Found by comparing the logged total against an independent estimate built from token counts and the real billed rate. | Roughly 4,600 written rows carry a cost figure twice the true value. | Fixed for every run going forward. Historical rows were not rewritten, since a logged cost is a record of what was believed true at the time, not a value to edit later. | The arithmetic proof is written into the project's standing rules, so any later script summing historical costs knows to expect the discrepancy. |
| 10 | A model-cost calculation never read the token count for a provider's internal reasoning step, only its visible response, undercounting real spend for that model by close to a factor of four. | Found by comparing the project's logged total against the provider's billing dashboard for the same period. | Around eight hundred rows undercounted real spend for the affected model. | The reasoning-token count is now added to the cost calculation, and kept separately in the row for audit. | Two regression tests cover the reasoning-token and the no-reasoning-token case, since the previous test's mocked response would have hidden this bug indefinitely. |
| 11 | A diagnostic script computed its tables correctly from live data on every run, but five sentences of its surrounding prose had the original result's numbers typed in as fixed text, not read from the same data. | Found by reading the script's opening paragraph against its regenerated tables after a data update, and noticing they disagreed. | Nothing in the data was wrong, but a reader who quoted the file's prose instead of its tables would have cited a stale figure. | Every cited figure in the file's prose is now computed from the same live data its tables use. | Checking a regenerated file's opening paragraph against its tables after any data update is now a standing check in the project. |

Four of these eleven share one shape, a number reported without the visibility needed to sanity-check it (a fixed total, an unfiltered list, a hidden sample size, prose beside a table that had moved on), fixed the same way each time: make the hidden or static quantity a computed, visible one. Two more, the batch-discount and reasoning-token bugs, are a whole cost-calculation component never read from the source, both found by checking the project's total against an independent bill, not by re-reading the code. A follow-up audit (prompted by bug 2) checked all thirteen validation/audit/sweep scripts in the project for the same failure shape: the two known bugs confirmed fixed, two new ones found and fixed, one hardened pre-emptively, seven already clean. A shared guard function now lets a future script raise loudly on an empty population by calling one function, not by writing the check by hand.

### 2.8 The asset pipeline

`scripts/build_thesis_assets.py` is a single-command registry: every table, figure, and provenance document the paper and this report cite is a registered step, regenerated from whatever result files exist on disk. `--list`, 32 steps at the time of writing:

```
comparison_ab             Comparison A (DyMuT L4 vs ULT) + Comparison B (ULT vs PLT)
stability                 StableMut@K + pairwise Kendall tau (RQ4.1)
comparison_c              Comparison C canonical 2x3 DiD + gradient + Mut@K tables
rq5                       RQ5/H6 model-ranking table + cross-benchmark correlations
execution_evidence_figure Live-captured execution evidence, structural
check_doc_citations       GATE: fails the build on any unsuppressed stale citation
... 26 more steps
```

The last step is the gate: `scripts/check_doc_citations.py` checks every statistic-shaped value in `analysis/` and `paper/sections/*.tex` against a reference corpus built fresh from the pipeline's own output, and fails the build on anything that matches nothing live:

{{FIGURE:evidence_citation_gate|Figure 5. A real run of the citation gate, tail output, captured live.}}

A value is exempt only with an explicit reason, an inline `<!-- cite:historical -->`/`<!-- cite:external -->` marker or an `analysis/CITATION_ALLOWLIST.md` entry, logged as `SUPPRESSED`, counted separately from a genuine `MATCH`.

### 2.9 Statistical procedure

Every RQ family with more than one significance test applies Holm-Bonferroni correction through one shared function, `src/Analysis/multiple_comparisons.py::holm_bonferroni()`, before any document cites the result.

| RQ family | Tests corrected together | n |
|---|---|---|
| RQ1 | H1 Test 1 (Dynamic vs ULT), H1 Test 2 (ULT vs PLT). H2 is a bootstrap CI, not part of this family. | 2 |
| RQ4 | Pairwise instantiation-stability comparisons, N=4 set and the all-pairs set, corrected separately | 6, and 10 |
| RQ5 | Correlation tests behind H6 clauses 1 and 2 (canonical/cross-family, raw/coverage-adjusted, three statistics) | 12 |

Correction changed a verdict, not just a number: H1 Test 2's raw p=0.0391 becomes p=0.0782 once corrected, no longer clearing 0.05. Its definition-matched co-primary, p=0.0078, becomes p=0.0156 and still clears it, which is why that verdict (section 1.7) is reported as significance-conditional.

### 2.10 Verification and validation, named explicitly

The word "verification" appears only once elsewhere in this report, in a section heading. The activities themselves are all present in sections 2.1-2.9 above; this table names each one and states which of the two it is:

| Activity | V or V | What it guards | Where it runs | On failure |
|---|---|---|---|---|
| Corpus cyclomatic-complexity recompute | Verification | That every template's declared tier matches its actual control-flow shape | Section 2.2, template validation and every generated instance | Instance dropped, not silently admitted |
| Within-tier diversity check | Verification | That the sixty templates are not near-duplicates of each other | Section 2.2, corpus validation gate | Flagged template rejected from the corpus |
| Tier-separation sanity check | Verification | That the four complexity tiers do not overlap | Section 2.2 | Corpus fails the gate |
| Oracle smoke tests | Verification | That every template's reference implementation is actually correct | Section 2.2, pre-acceptance | Template rejected |
| The 152-test pytest suite | Verification | That the harness itself does what it was specified to do | Every change, Section 2.4 | Change blocked until fixed |
| The three regression tests (Section 2.4) | Verification | That three specific, previously real bugs do not recur | Every change | Change blocked until fixed |
| Exec gate | Verification | That a generated test file is syntactically valid, importable code | Every scored problem, Section 2.3 | Row scored `exec_ok=False`, excluded from further scoring |
| Baseline gate | Verification | That a generated suite passes against the real function | Every scored problem, Section 2.3 | Row excluded from the mutation-score average, not scored zero |
| Mutant-drop handling | Verification | That a mutant which fails to import cleanly is neither killed nor survived, not miscounted | Section 1.8, Algorithm (c) | Mutant excluded from that problem's denominator |
| Citation gate | Verification | That a hand-written number still matches live pipeline output | Every build, Section 2.5 | Build fails |
| The thirteen-script validator audit | Verification | That no other validator shares the "reports success while checking nothing" defect | One-off audit, prompted by error-ledger bug 2 | Two further instances found and fixed |
| Dedup-by-timestamp | Verification | That a stale, superseded result file is not double-counted | Every result load, error-ledger bug 4 | Older row silently dropped, newer kept |
| Canonical-model filter | Verification | That a fine-tuned adapter's label does not leak into a downstream model count | Every downstream analysis script, error-ledger bug 5 | Non-canonical row dropped before aggregation |
| Independent-billing reconciliation | Verification | That a logged cost figure matches what was actually billed | One-off, error-ledger bugs 9-10 | Discrepancy investigated and the calculation fixed |
| Construct-validity check against BigCodeBench (H6) | Validation | Whether a mutation score means test quality, not just whether the harness ran correctly | Section 4.3, one-off pre-registered analysis | Result reported as found, including a contradicted prediction |
| Mutation-score-declines-with-tier check (H3) | Validation | Whether higher structural complexity genuinely makes test generation harder, the benchmark's core validity argument | Section 4.3, one-off pre-registered analysis | Result reported as found |

The distinction matters beyond terminology. Verification asks whether the harness does what it was specified to do: does the exec gate actually gate, does the citation checker actually check. Validation asks a different question: does the number the (already verified) harness produces mean what this project claims it means, that a higher mutation score reflects a better test suite rather than an artefact of the scoring mechanism. A harness can pass every verification check and still measure the wrong thing; H3 and H6 are this project's answer to that second question, not a repeat of the first.

### 2.11 Risk register

Real risks this project identified, not a generic list assembled after the fact: every row below either fired, in a form this report already describes elsewhere, or was actively dodged by a decision already stated in this report.

| Risk | Likelihood / impact | Mitigation | Did it fire? |
|---|---|---|---|
| A specified provider model is retired or made unavailable before evaluation completes | Medium / high (blocks a whole model's data) | Track provider deprecation notices; keep the model list in config, not hardcoded, so a substitution is a config change | **Fired.** Gemini 2.5 Pro/Flash returned model-unavailable errors ahead of their own stated retirement schedule; substituted with Gemini 3.1 Pro Preview/Flash-Lite (section 2.1's methods, paper section 3.4) |
| Shared HPC queue contention delays the evaluation schedule | High / medium | A documented fallback partition (V100, eight nodes) when the shared A100 queue is busy | **Fired, mitigated.** Section 3.2's own job-accounting figure shows the wide `Elapsed` spread across nominally identical jobs this risk describes; the V100 fallback is used routinely, not held in reserve |
| API spend exceeds the project's budget | Medium / medium | Per-call cost logging; price any remaining gap before deciding to close it, not after | **Dodged, not fired.** The one priced, declined gap (the fifth Gemini instantiation, section 2.6) was a deliberate choice not to spend $9.60, not an overrun already incurred |
| A third-party benchmark's ground truth is less reliable than its publication implies | Medium / high (undermines a comparator this project depends on) | Recompute correctness and complexity independently rather than trusting shipped metadata | **Fired.** ULT's own ground truth passes this project's harness at only 8.4% out of the box, and its complexity metadata disagrees with an independent recompute at the CC-8 boundary (section 1.9) |
| Untrusted, scraped, or model-generated code damages the working environment when executed | Low probability per run, high impact if it fires | Execute from an isolated temporary directory, never the project root | **Fired once, then fixed.** An early ground-truth quality check littered the project root with stray files before this rule was adopted (section 4.2) |
| A second concurrent working session is mistaken for unauthorised external modification | Low / low-to-medium (costs investigation time, not data) | One working session per checkout; a second session uses a separate git worktree | **Fired once.** A July 2026 second session briefly looked like an intrusion before being confirmed benign (section 4.2); the worktree rule was adopted afterward |
| Generated data or checkpoints are lost when scratch storage is purged after inactivity | Low probability, high impact (months of compute) | A dated, manually verified backup of results, adapters, and analysis outputs on the home filesystem, not scratch | **Dodged, not fired.** The 2026-08-12 pre-flight backup exists specifically to prevent this before scratch's three-month purge policy could ever test it |

---

## 3. Tools

The table below gives every tool this project relies on a version, the lifecycle stage(s) it supports, and why it was chosen. Where a genuine alternative was considered, it is named; several of these are the ecosystem's standard choice for the job, with no serious alternative weighed, and are described honestly as such rather than a rationale invented after the fact.

| Tool | Version | Stage(s) | Why chosen (alternative, if one was genuinely weighed) |
|---|---|---|---|
| Python | 3.10 | All | The benchmark evaluates Python code; the same language runs the harness, the templates, and the models under test |
| `uv` | 0.11 | All (environment) | Reproducible, lock-file-based installs across the developer machine and the cluster, faster and simpler than a `pip`/`conda` combination for this project's scale |
| SLURM / Kelvin2 | -- | Implementation, testing | Institutional HPC allocation; not a choice among alternatives |
| `transformers` | 4.57.6 | Implementation | Standard local-model-serving library for the open-source Qwen sweep and the LoRA fine-tune; no serious alternative for HuggingFace-hosted checkpoints |
| `peft` | 0.19.1 | Implementation | LoRA implementation on top of `transformers` (over full fine-tuning: fits a single shared GPU slice, see Section 4.1) |
| `torch` | 2.5.1 | Implementation | Underlying tensor framework `transformers`/`peft` require |
| `pytest` | 9.0.3 | Verification, testing | Runs this project's own 152-test suite and, via `--collect-only`, the scoring harness's exec gate (Section 2.3) |
| `coverage` | 7.14.1 | Testing | Statement/branch coverage secondary metrics, inside the isolated-subprocess pattern (Section 2.3) |
| `pandas` | 2.3.3 | Evaluation, analysis | Loading and aggregating result files across every analysis script |
| `scipy` | 1.15.3 | Evaluation, analysis | Wilcoxon signed-rank test, Spearman and Pearson correlation |
| `matplotlib` | 3.10.9 | Evaluation | Every figure in the paper and this report, script-generated, never hand-built |
| `openpyxl` | 3.1.5 | Planning, evaluation | Reads/writes the hypothesis workbook (`docs/Research_questions.xlsx`) that Table I/Table II of the paper and report are generated from |
| `git` | 2.43 | All | Version control throughout, commits grouped by logical change |
| git worktrees | -- | Implementation | Isolates a second concurrent session from the main checkout (Section 4.2's lesson), over pointing a second session at the same checkout |
| VS Code Remote-SSH | -- | Implementation | Development environment on the cluster itself, avoiding a local/remote code-drift problem |
| `python-docx` | 1.2.0 | Evaluation, write-up | Renders this report's markdown source to a formatted Word document |
| `python-pptx` | 1.0.2 | Evaluation, write-up | Builds the presentation slide deck |
| `latexmk` (TeX Live 2023) | 4.80 | Evaluation, write-up | Compiles the paper from its LaTeX source, resolving the bibliography and cross-reference passes automatically |

### 3.1 Language and environment

The project is written in Python 3.10, with type hints throughout. Dependencies and the virtual environment are managed with `uv`, chosen for reproducible, lock-file-based installs across the developer machine and the compute cluster. Python fits this project's subject matter: the benchmark evaluates Python code, so the same language runs the harness, the templates, and the models under test.

### 3.2 HPC cluster and job scheduler

Compute runs on Kelvin2, Queen's University Belfast's HPC cluster, under SLURM. Interactive sessions are used only for short tests, since they end if the connection drops. Every real workload is submitted as a batch job. The cluster offers several GPU partitions, chosen per job by size: a shared A100 in sliced mode for most fine-tuning and inference work, a bank of eight V100 nodes as a fallback when the shared A100 queue is busy, full A100 and H100 cards for larger models, and experimental AMD and Intel partitions not used in this project. Scratch storage, not the home filesystem, holds the HuggingFace model cache and all generated data, since scratch carries no quota and home does.

A slice of this project's own real job accounting on Kelvin2, from the week the main evaluation sweep ran:

{{FIGURE:evidence_slurm_jobs|Figure 6. This project's own SLURM job accounting (`sacct`), a fixed historical window, captured live.}}

The `FAILED` row is real, not curated out of the panel: this is exactly the kind of job the error ledger and section 4.2's lessons trace back to, a bug that only shows up after a real submission, not in a local dry run. The wide spread in `Elapsed` across otherwise identical `eval-mig` jobs, nineteen minutes to just over an hour, is why the partition choice described above is made per job by measured size, not by a single default.

### 3.3 Model-serving and fine-tuning stack

Six closed-source models are served through OpenAI's, Anthropic's, and Google's own APIs. Three open-source Qwen2.5-Coder [17] sizes run locally through HuggingFace's `transformers`. Every model call is logged with its identifier, snapshot or revision, and full resolved decoding configuration, for the reason given in error-ledger bug 1. The causal contamination probe fine-tunes the smallest open-source model with low-rank adaptation, LoRA [15], using the `peft` library on top of `transformers`, on a single GPU slice. OpenAI's Batch API is used for the closed-source model calls that support it, at half the real-time cost.

### 3.4 Testing and coverage tools

The project's own test suite (section 2.4) and the benchmark's scoring harness (section 2.3, Algorithm (c) in section 1.8) both run on pytest, but are separate things: the harness uses `pytest --collect-only` for the exec gate, always inside the isolated-subprocess pattern section 2.3 describes. Python's `coverage` library is available in the environment for statement/branch instrumentation but is not currently wired into any reported metric; mutation score, not coverage, is this project's own answer to "does the suite exercise the code meaningfully" (section 4.1's "mutation score as the headline metric").

### 3.5 Analysis and plotting stack

Result files are loaded and aggregated with `pandas`. Statistical tests, the Wilcoxon signed-rank test, Spearman and Pearson correlation, use `scipy`; the Holm-Bonferroni correction is a hand-implemented function over `numpy` (`src/Analysis/multiple_comparisons.py::holm_bonferroni()`), not a `statsmodels` call, `statsmodels` is not a dependency of this project. Every figure in the paper and in this report, including the flow diagram in section 2, is produced with `matplotlib`, run as a script and never built by hand, so a figure regenerates from the same data its caption describes.

### 3.6 Version control

The project is tracked in git throughout, commits grouped by logical change, not by working session. Large binary or generated files, model weights, raw result archives, and this report's rendered outputs, are excluded from the repository and backed up separately (section 6). One working session per checkout is a standing rule, section 4.2 explains why.

### 3.7 Document toolchain

The paper is written in IEEEtran LaTeX and compiled with `latexmk`. Every quantitative value the paper's prose cites is a macro read live from the analysis pipeline's output, checked by the citation gate described in section 2.5, so no result value is typed by hand into the paper's text. This report is written first as markdown, checked by the same citation gate, then rendered to a formatted Word document with `python-docx`. The slide deck is built with `python-pptx`. The flow diagram and every other figure are exported at print resolution as both PNG and PDF from the same `matplotlib` script.

### 3.8 AI coding assistant

Claude Code, an AI coding assistant, was used throughout development: implementing the template engine, the scoring harness, and the analysis scripts from a specification the author wrote; investigating and fixing the bugs recorded in the error ledger; and drafting documentation, including this report and the paper, from the author's project records and decisions. Every design decision, every hypothesis, every interpretation of a result, and the decision to fine-tune, to cut an instantiation, or to decline further data collection, was the author's, made in consultation with the supervisor. The assistant did not choose what to test or what a result meant; it wrote code and prose to a specification and had its output reviewed before being relied on. This declaration is stated here in full and in the paper's own AI Ethical Considerations section, consistent with the module's AI-assistance declaration requirement.

---

## 4. Critical Appraisal

### 4.1 Design and implementation decisions

**Template-generated problems instead of real-world code.** A benchmark built from real, scraped functions is a fixed artefact once published, and can leak the same way any other benchmark can. Template-generated problems are drawn fresh from a private grammar at evaluation time, so a specific problem instance need never be published. The alternative, drawing problems from a corpus of real repositories the way Code2Bench does, was rejected because that corpus is static content once assembled, and inherits the same leak risk this project set out to remove. The cost of this choice is disclosed in section 4.3: template-generated code may not carry the full structural variety of production code.

**Mutation score as the headline metric.** Coverage does not check whether a test suite would catch a real fault. A fixed reference suite needs a human-curated answer key that can leak. Mutation score needs neither: each problem's reference implementation can generate its mutants (mutation testing itself dating to DeMillo et al. [8]), and the suite is scored by execution, not by comparison to hand-written text.

**Four complexity tiers.** Test-generation difficulty is not uniform across all code. A trivial, single-path function and a nested, multi-branch one are different tasks. Stratifying the corpus by cyclomatic complexity lets the benchmark report how test-generation quality changes with structural difficulty, and lets a comparison against a static benchmark be matched to the one complexity band both sides share. The four bands, and the target mutant-count range for each, were fixed before any evaluation data existed, so the boundaries could not be tuned to a result after the fact.

**Oracle-by-construction.** Every generated problem carries a reference implementation generated from the same template that produced the problem. Scoring never depends on a separately maintained answer key. The alternative, a hand-written or scraped set of expected outputs, would reintroduce the same static-content leak risk mutation testing is meant to avoid, and would need maintenance as the template grammar grows.

**Precomputed, shared mutant sets.** A problem instance's mutants are generated once, at instantiation time, and the same set is reused to score every model's response to that instance. Generating mutants per model call was rejected: it would let two models be scored against two different mutant populations for what is meant to be the identical problem, undermining any comparison between them.

**LoRA on a small open-source model for the contamination probe.** The causal contamination experiment needs a model whose weights can be fine-tuned, which rules out every closed-source API model in the panel. Low-rank adaptation was chosen over full fine-tuning because it fits inside a single shared GPU slice and trains in hours, not days, letting the experiment run within the project's compute budget. The smallest of the three open-source sizes was chosen so a clear memorisation signal, if present, would not be masked by a larger model's capability.

**Repairing ULT's ground truth before training on it.** Only 8.4% of ULT's shipped test-and-code pairs pass cleanly out of the box (section 1.6's taxonomy). Training a fine-tune on unrepaired ground truth would teach the model to reproduce broken tests, and the resulting score change would reflect that corruption, not contamination. The alternative rejected here was training on the shipped tests as-is: it would have confounded "the model learned this test" with "the model learned this broken test," the opposite of a clean contamination signal.

**Conditional and unconditional mutation score, both reported.** The project's pre-registered primary metric averages mutation score only over problems whose suite passes against the correct implementation, excluding the rest from the mean. A second reading includes every attempted problem, scoring a non-passing suite as zero. These are different estimands, and a model with a low pass rate can look strong under one and weak under the other. Reporting only one would let a reader draw a conclusion the other reading would contradict, so both are reported as co-primaries, never as one replacing the other.

**The four-instantiation stability scope, and the fifth instantiation's cost declined.** The design target was five independent benchmark instantiations, to measure whether model rankings hold up across repeated regeneration. Completing the fifth instantiation for the two remaining models was priced at $9.60 once the other seven had reached it. It was declined because the stability verdict does not move at any plausible resulting value, a reasoning set out in section 2.6, and because a diagnostic on the existing four instantiations predicted more data would not resolve the ranking question it was meant to answer.


### 4.2 Lessons learnt

**A single decoding setting fabricated a fine-tuning collapse.** A generation setting meant to stop a model from repeating text instead banned the import line every response had to reproduce, since that line also appeared in the system prompt. Three of six supplementary fine-tuning conditions showed what looked like a capability collapse. It was not. Diagnosing this took a controlled check at fifty problems, comparing the setting on against off, and cost roughly a week of GPU time spent evaluating checkpoints against a broken script before the mechanism was confirmed. The lesson: a model's full decoding configuration is part of what a result means, not a footnote, and an unlogged setting can change a result with no code or data difference visible anywhere else.

**Hand-written documents can fall out of date while the tables next to them stay current.** Several figures in this project moved more than once with no change to the analysis method, only a bug fix or new data arriving. A hand-written interpretation quoting one of those figures does not update when the table beside it does. This happened at least once for real: a diagnostic script's opening paragraph kept citing a superseded correlation value after its tables had moved on. The rule adopted was not "proofread more carefully." It was to build a script that checks every hand-typed statistic in the project's documents against the live pipeline output automatically, described in section 2.5, so drift is caught by a program, not by a person's memory of what a number used to be.

**The decoding-setting bug was also an uncommitted-change bug.** The setting responsible for the fabricated collapse above sat in the working tree, added but never committed, for five days before it was fixed. During that time it shaped a week of real GPU sweeps with no visible trace of the change, though a `git diff` would have shown it clearly, had anyone thought to check. The rule this produced is not only "commit more often." It is that a model call's full resolved run configuration, including anything an uncommitted change might have touched, is now logged with the run, so the record does not depend on the state of a script that may or may not have been saved to version control at the time.

**Two people can work on one checkout and look like an intrusion.** A second working session on the same project directory, in July 2026, produced changes that briefly looked like an unexplained external modification to the tree, since nothing distinguished "a second legitimate session" from "someone else touched this." The change turned out to be benign, but confirming that cost real time that would not have been needed under a clearer rule. The rule adopted: one working session per checkout. A second concurrent session uses a separate git worktree instead, so two legitimate sessions can never again look indistinguishable from an unauthorised change.

**A validator can report success while checking nothing.** Two early scripts in this project passed every time they ran, for the wrong reason: one printed a fixed pass count regardless of what ran, and the other pointed at a path that no longer held any templates, so its loop validated zero of them while still printing a clean result. Neither failure would have been visible from the script's output. A project-wide audit of every validation and audit script in the codebase, described in section 2.7, found two further instances of the same shape and hardened a third against a risk it had not yet hit. The lesson generalises past this one project: a check that can pass over an empty population without a warning is not a check, and the fix is to make that population's size visible and to fail loudly if it is ever zero.

**Untrusted code needs an isolated working directory, not just a sandboxed process.** An early ground-truth quality check ran thousands of scraped functions to confirm they execute, with the working directory left at the project's root. A meaningful share of those functions did ordinary file input and output as a side effect of running, and littered the project root with stray files as a result. Running code in a subprocess is not the same guarantee as running it somewhere disposable. The rule adopted: untrusted code is always executed from a freshly created temporary directory, never from the repository's working directory, described in section 2.3.


### 4.3 Evaluation with hindsight

Section 5 states each hypothesis's verdict once. This subsection asks what reporting all six together says, not what each one says individually.

**Why the null and dropped results are reported in full, not minimised.** H1's first test, H4, and H5 are not comfortable results for a project whose central claim is that its benchmark works. They are reported at the same length and with the same numbers as H2's strong result, because a benchmark's credibility rests on reporting what a pre-registered test found, not on reporting only the tests that came out favourably. H1's non-significant result still narrows the space of believable outcomes: it rules out one specific concern, that DyMuT's harder tier would look easier than ULT for reasons unrelated to contamination. H5's shortfall says something specific: the diagnostic work behind it shows the shortfall traces to several models clustering close together in score, not to the benchmark producing unreliable numbers, which is a materially different and more precise finding than "the benchmark is unstable."

**What the project achieved.** A working, end-to-end dynamic benchmark, DyMuT, exists: sixty validated templates across four complexity tiers, a deterministic instantiation engine, and a mutation-testing harness that scores nine models with no dependence on a human-curated answer key. The causal contamination experiment produced clean, unambiguous evidence that fine-tuning on a static benchmark's ground truth inflates that benchmark's score while leaving DyMuT untouched. The project's central claim is demonstrated concretely, not assumed. The construct-validity check confirms DyMuT still tracks an external measure of code-generation capability, so contamination resistance was not bought at the cost of measuring nothing recognisable.

**What it did not achieve.** The causal result rests on one model, one fine-tuning method, and one hyperparameter setting. Nothing in the project tests whether the same clean separation between memorisation and transfer holds at a larger scale or under full fine-tuning. Rank-level stability across benchmark regenerations falls short of its pre-registered target, so a reader should trust each model's aggregate score more than a close ranking between two similarly scoring models. The equivalent-mutant validation, a hand-inspected sample meant to produce a corrected companion score alongside the raw headline figure, was not complete at the point this report was written, and the raw score is reported alone as a result.

**What would be done differently with the same time.** Generation-config logging and the citation gate would be built in week one, not discovered as a need partway through. Both would have prevented real, costly incidents, not only explained them after the fact. The fifth benchmark instantiation would be budgeted for from the start, not treated as a cut candidate, since stability turned out to be the hypothesis with the least margin to spare. More of the equivalent-mutant hand-inspection would be scheduled earlier, so it did not compete with write-up time at the end of the project.

**What the results do and do not support.** The results support treating a dynamic, template-based, mutation-scored benchmark as resistant to the specific contamination mechanism this project tested: direct fine-tuning on a static benchmark's ground truth. They do not support a claim that the benchmark's rankings are reliable enough to distinguish two closely scoring models with confidence, and they do not support any claim about contamination mechanisms this project did not test: indirect leakage through API logging, for one, a real route into contamination this project never isolated experimentally.

---

## 5. Results Summary

Section 4.3 discusses what these results mean. This section states them once, in one place, with no discussion attached.

| Hypothesis | Prediction | Verdict |
|---|---|---|
| H1 Test 1 | Dynamic scores lower than static, CC-matched | NOT SUPPORTED |
| H1 Test 2 | Leaked twin (PLT) scores higher than decontaminated ULT | MIXED |
| H2 | Static-benchmark gain from fine-tuning exceeds dynamic gain | SUPPORTED |
| H2-supplementary | Leaked instantiation inflates itself, not fresh instantiations (post-hoc) | SUPPLEMENTARY |
| H3 | Mutation score never increases from L1 to L4 | SUPPORTED (trend) |
| H4 | Static-dynamic gap larger at low tiers than high tiers | DROPPED |
| H5 | Cross-instantiation Kendall τ exceeds 0.7 | THRESHOLD NOT MET |
| H6 clause 1 | Dynamic-proxy correlation positive but imperfect | MIXED |
| H6 clause 2 | Dynamic-proxy correlation weaker than static-proxy | NOT SUPPORTED |

This table's verdicts are read live from the same workbook as the paper's own Table II (`paper/table1.tex`), not restated independently; the paper's version additionally carries a research-question column, an abbreviated hypothesis label, and a pointer to the reporting subsection.

H2's headline figures, the strongest result in the project: fine-tuning Qwen2.5-Coder-1.5B-Instruct on ULT's own ground truth moves seen-ULT's `baseline_pass_rate` by +99.1 percentage points (95% CI [97.3, 100.0]), moves PLT by +13.8 percentage points (CI [7.7, 20.1]) once a measured +8.7pp generic-fine-tuning-improvement control is subtracted, and moves DyMuT's hardest tier by exactly 0.0 percentage points.

Full per-problem results are submitted as separate appendix files, not reproduced here: `docs/Research_questions.xlsx` (this table's own source) and `analysis/results.xlsx` (the per-problem dynamic-benchmark export). Every intermediate table lives in `analysis/` as citation-gated markdown and CSV.

### 5.1 Supplementary figures

The paper's own page budget carries one figure; the four below are the visual companions its prose points back to here.

{{FIGURE:h3_tier_effect|Figure 7. H3: conditional Mut@K by complexity tier, one line per canonical model. Steep, monotone decline for the three open-source Qwen sizes; much more gradual for the six commercial models, which stay closer to ceiling through L3.}}

{{FIGURE:h5_stability|Figure 8. H5: StableMut@K, mean +/- SD across benchmark re-instantiations, per canonical model. Every error bar is a sliver of the score axis -- score-level stability is not the property RQ4's threshold falls short on.}}

{{FIGURE:collapse_vs_survival|Figure 9. H6 clause 1's cross-family extension, DyMuT (pooled) against BigCodeBench Pass@1: (a) raw conditional Mut@K's agreement collapses under added model diversity; (b) coverage-adjusted agreement survives. The red-ringed marker denotes a thin cell on the DyMuT axis ($n_{defined}<20$).}}

{{FIGURE:ranking_matrix_heatmap|Figure 10. Ranking matrix: Kendall tau rank agreement by metric and benchmark pair, both scopes. DyMuT is pooled across all four complexity tiers throughout; BCB abbreviates BigCodeBench. ** significant after Holm-Bonferroni correction (12-test family); * significant at raw p<0.05 only.}}

## 6. Reproducing This Work

**Repository.** `https://github.com/yosanchez90-sudo/dynamic-llm-benchmark`. The working checkout at the time of writing is `/mnt/scratch2/users/40492566/dissertation` on Queen's University Belfast's Kelvin2 cluster. Large binaries, model weights, and raw result archives are excluded from version control (section 3.6) and backed up separately, so a clone reproduces every script, template, and analysis document, not the multi-gigabyte raw data those scripts were run against.

**Prerequisites.** Python 3.11, the `uv` package manager, and a SLURM-scheduled GPU cluster for anything beyond the smallest local checks (section 3.2). `HF_HOME` must point at scratch storage, not the home filesystem, before any HuggingFace model download (section 3.2's own quota note).

**Install.**

```
git clone https://github.com/yosanchez90-sudo/dynamic-llm-benchmark
cd dynamic-llm-benchmark
uv sync
```

`uv sync` installs every pinned dependency from the project's lock file, the same versions the reported results were produced with.

**Run the tests.**

```
uv run pytest -q -m "not torch"
```

runs the 136 tests that need no working torch install. `uv run pytest -q` runs the full 152 on a machine with one. Figure 4 (section 2.4) is a real, live capture of this exact command.

**Regenerate every table and figure with one command.**

```
uv run python scripts/build_thesis_assets.py
```

runs all 28 registered steps end to end (section 2.8) and finishes with the citation gate. A nonzero exit means at least one hand-written document cites a number the pipeline no longer produces. `--list` shows every step. `--only <key>` reruns just one.

**What `data/` contains, and why it is not in version control.** `data/raw/` holds the vendored ULT/PLT source (`PROVENANCE.md` documents how). `data/results/` holds one append-only JSONL file per model-benchmark-instantiation run. `data/batches/` and `data/finetune/` hold OpenAI batch state and the fine-tuning sets from section 1.6. None of it is hand-edited or small; it is backed up outside git instead, a dated snapshot on the cluster's home filesystem, since scratch storage is purged after three months of inactivity.

---

## References

1. James H. Andrews, Lionel C. Briand and Yvan Labiche (2005). Is Mutation an Appropriate Tool for Testing Experiments?. Proceedings of the 27th International Conference on Software Engineering (ICSE 2005). https://doi.org/10.1145/1062455.1062530

2. Joshua D. Angrist and Jörn-Steffen Pischke (2009). Mostly Harmless Econometrics: An Empiricist's Companion. Princeton University Press. https://doi.org/10.1515/9781400829828

3. Simone Balloccu, Patrícia Schmidtová, Mateusz Lango and Ondřej Dušek (2024). Leak, Cheat, Repeat: Data Contamination and Evaluation Malpractices in Closed-Source LLMs. Proceedings of EACL 2024. https://aclanthology.org/2024.eacl-long.5/

4. Nicholas Carlini, Daphne Ippolito, Matthew Jagielski, Katherine Lee, Florian Tramèr and Chiyuan Zhang (2023). Quantifying Memorization Across Neural Language Models. The Eleventh International Conference on Learning Representations (ICLR 2023). https://arxiv.org/abs/2202.07646

5. Simin Chen, Pranav Pusarla and Baishakhi Ray (2025). Dynamic Benchmarking of Reasoning Capabilities in Code Large Language Models under Data Contamination. Proceedings of the 42nd International Conference on Machine Learning (ICML 2025). https://arxiv.org/abs/2503.04149

6. Mark Chen et al. (2021). Evaluating Large Language Models Trained on Code. arXiv preprint. https://arxiv.org/abs/2107.03374

7. Chua Jin Chou, Khant That Lwin and Ezekiel Soremekun (2026). MuCoCo: Automated Consistency Testing of Code LLMs. arXiv preprint. https://arxiv.org/abs/2604.19086

8. R. A. DeMillo, R. J. Lipton and F. G. Sayward (1978). Hints on Test Data Selection: Help for the Practicing Programmer. Computer. https://doi.org/10.1109/C-M.1978.218136

9. Y. Dong, X. Jiang, X. Zhang, H. Liu, Z. Jin, B. Gu, M. Yang and G. Li (2026). Generalization or Memorization: Data Contamination for Large Language Models in Code Generation. IEEE Transactions on Software Engineering (early access). https://doi.org/10.1109/TSE.2026.3713834

10. Bradley Efron and R. J. Tibshirani (1994). An Introduction to the Bootstrap. Chapman and Hall/CRC. https://doi.org/10.1201/9780429246593

11. Gordon Fraser and Andrea Arcuri (2011). EvoSuite: Automatic Test Suite Generation for Object-Oriented Software. Proceedings of the 19th ACM SIGSOFT Symposium and the 13th European Conference on Foundations of Software Engineering (ESEC/FSE 2011). https://doi.org/10.1145/2025113.2025179

12. Batu Guan, Xiao Wu, Yuanyuan Yuan and Shaohua Li (2025). Is Your Benchmark Still Useful? Dynamic Benchmarking for Code Language Models. arXiv preprint. https://arxiv.org/abs/2503.06643

13. Sabaat Haroon, Mohammad Taha Khan and Muhammad Ali Gulzar (2026). Evaluating LLM-Based Test Generation Under Software Evolution. arXiv preprint. https://arxiv.org/abs/2603.23443

14. Sture Holm (1979). A Simple Sequentially Rejective Multiple Test Procedure. Scandinavian Journal of Statistics. https://www.jstor.org/stable/4615733

15. Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang and Weizhu Chen (2022). LoRA: Low-Rank Adaptation of Large Language Models. International Conference on Learning Representations (ICLR 2022). https://arxiv.org/abs/2106.09685

16. Dong Huang, Jie M. Zhang, Mark Harman, Qianru Zhang, Mingzhe Du and See-Kiong Ng (2026). Benchmarking LLMs for Unit Test Generation from Real-World Functions. ACM Transactions on Software Engineering and Methodology. https://doi.org/10.1145/3805043

17. Binyuan Hui et al. (2024). Qwen2.5-Coder Technical Report. arXiv preprint. https://arxiv.org/abs/2409.12186

18. Naman Jain, King Han, Alex Gu, Wen-Ding Li, Fanjia Yan, Tianjun Zhang, Sida Wang, Armando Solar-Lezama, Koushik Sen and Ion Stoica (2025). LiveCodeBench: Holistic and Contamination Free Evaluation of Large Language Models for Code. The Thirteenth International Conference on Learning Representations (ICLR 2025). https://arxiv.org/abs/2403.07974

19. Yue Jia and Mark Harman (2011). An Analysis and Survey of the Development of Mutation Testing. IEEE Transactions on Software Engineering. https://doi.org/10.1109/TSE.2010.62

20. Eunsu Kim, Juyoung Suk, Seungone Kim, Niklas Muennighoff, Dongkwan Kim and Alice Oh (2025). LLM-as-an-Interviewer: Beyond Static Testing Through Dynamic LLM Evaluation. Findings of the Association for Computational Linguistics: ACL 2025. https://doi.org/10.18653/v1/2025.findings-acl.1357

21. Stephan Lukasczyk and Gordon Fraser (2022). Pynguin: Automated Unit Test Generation for Python. Proceedings of the 44th International Conference on Software Engineering: Companion Proceedings (ICSE-Companion 2022). https://doi.org/10.1145/3510454.3516829

22. T. J. McCabe (1976). A Complexity Measure. IEEE Transactions on Software Engineering. https://doi.org/10.1109/TSE.1976.233837

23. Dayyán O'Brien, Barry Haddow, Emily Allaway and Pinzhen Chen (2025). MATHEMAGIC: Generating Dynamic Mathematics Benchmarks Robust to Memorization. arXiv preprint. https://arxiv.org/abs/2510.05962

24. Oscar Sainz, Jon Ander Campos, Iker García-Ferrero, Julen Etxaniz, Oier Lopez de Lacalle and Eneko Agirre (2023). NLP Evaluation in Trouble: On the Need to Measure LLM Data Contamination for each Benchmark. Findings of the Association for Computational Linguistics: EMNLP 2023. https://doi.org/10.18653/v1/2023.findings-emnlp.722

25. Max Schäfer, Sarah Nadi, Aryaz Eghbali and Frank Tip (2024). An Empirical Evaluation of Using Large Language Models for Automated Unit Test Generation. IEEE Transactions on Software Engineering. https://doi.org/10.1109/TSE.2023.3334955

26. Mohammed Latif Siddiq, Joanna Cecilia da Silva Santos, Ridwanul Hasan Tanvir, Noshin Ulfat, Fahmid Al Rifat and Vinícius Carvalho Lopes (2024). Using Large Language Models to Generate JUnit Tests: An Empirical Study. Proceedings of the 28th International Conference on Evaluation and Assessment in Software Engineering (EASE 2024). https://doi.org/10.1145/3661167.3661216

27. Gaurav Srivastava, Aafiya Hussain, Zhenyu Bi, Swastik Roy, Priya Pitre, Meng Lu, Morteza Ziyadi and Xuan Wang (2026). BeyondBench: Contamination-Resistant Evaluation of Reasoning in Language Models. International Conference on Learning Representations (ICLR 2026). https://arxiv.org/abs/2509.24210

28. W. Wang, C. Yang, Z. Wang, Y. Huang, Z. Chu, D. Song, L. Zhang, A. R. Chen and L. Ma (2024). TestEval: Benchmarking Large Language Models for Test Case Generation. arXiv preprint. https://arxiv.org/abs/2406.04531

29. Colin White et al. (2025). LiveBench: A Challenging, Contamination-Limited LLM Benchmark. International Conference on Learning Representations (ICLR 2025, Spotlight). https://arxiv.org/abs/2406.19314

30. Zhe Zhang, Runlin Liu, Aishan Liu, Xingyu Liu, Xiang Gao and Hailong Sun (2025). Code2Bench: Scaling Source and Rigor for Dynamic Benchmark Construction. arXiv preprint. https://arxiv.org/abs/2508.07180

31. Kaijie Zhu, Jiaao Chen, Jindong Wang, Neil Zhenqiang Gong, Diyi Yang and Xing Xie (2024). DyVal: Dynamic Evaluation of Large Language Models for Reasoning Tasks. International Conference on Learning Representations (ICLR 2024). https://arxiv.org/abs/2309.17167

32. Terry Yue Zhuo et al. (2025). BigCodeBench: Benchmarking Code Generation with Diverse Function Calls and Complex Instructions. International Conference on Learning Representations (ICLR 2025, Oral). https://arxiv.org/abs/2406.15877

