# Supporting Report

**ECS8056 MSc AI Themed Research Project (25/26)**

**Memorisation-Robust Benchmarking of LLM Test Generation: A Dynamic, Template-Based Benchmark with Complexity-Tiered Mutation Analysis**

Yohan Sneider Sanchez Vega (40492566)
Supervisor: Pinzhen Chen
School of Electronics, Electrical Engineering and Computer Science, Queen's University Belfast

---

## 1. Context and Literature

### 1.1 The contamination problem

A benchmark is contaminated when the model being tested has seen the benchmark's problems during training. A high score then reflects recall. It does not reflect the capability the benchmark was built to measure. Sainz et al. (2023) argue that contamination should be checked for every benchmark. It should not be assumed away. Balloccu et al. (2024) quantify how often this happens: roughly 42% of 255 evaluation papers they reviewed leaked benchmark data to closed-source models, some 4.7 million samples across 263 benchmarks. This leak happens through two routes. A published benchmark can be scraped from the web into a future training corpus. It can also leak indirectly: problems sent to a commercial model's API during evaluation are logged and reused as training signal. Neither route requires bad faith from anyone involved. Both follow from publishing the benchmark's content.

Carlini et al. (2023) show the mechanism behind this. Large language models reproduce training sequences verbatim. The rate at which they do so grows with model scale and with how often a sequence is duplicated in the training corpus. A widely used benchmark, evaluated across many papers, is duplicated by construction. Dong et al. (2026) extend this line to code generation. Separating generalisation from memorisation is a live, unresolved problem for code-generation benchmarks.

These findings establish that contamination is real and detectable after training has happened. None of them offer a way to stop it at measurement time. That gap is the starting point for this project.

### 1.2 Dynamic evaluation

One response to contamination is to stop publishing a fixed set of problems. A benchmark that generates fresh problem instances at evaluation time cannot be memorised in advance. Its content did not exist when any past model was trained.

DyVal (Zhu et al., 2024) builds reasoning problems from dynamic graphs, so each evaluation run samples a new graph and a new problem. LiveBench (White et al., 2025) refreshes its problem pool on a schedule against continuously updated sources, so a model trained before a given refresh cannot have seen that refresh's content. BeyondBench (Srivastava et al., 2026) generates algorithmic problems with a mathematical correctness guarantee attached to each one. This removes the need for a curated answer key. MATHEMAGIC (O'Brien et al., 2025) applies the same generative principle to mathematics benchmarks. LLM-as-an-Interviewer (Kim et al., 2025) replaces a static test set with an adaptive, dialogue-driven evaluation, where the questions respond to the model's prior answers.

Each of these five systems shows that generative evaluation works at scale and resists the failure mode a static benchmark cannot avoid. None of them targets unit-test generation. A generated unit test is not scored the way a generated answer to a question is. It is scored by executing it.

DyCodeEval (Chen et al., 2025) and the benchmark-usefulness study of Guan et al. (2025) bring dynamic regeneration to code-reasoning benchmarks. Code2Bench (Zhang et al., 2025) scales dynamic benchmark construction from source repositories, generating problems from real code instead of a template grammar. LiveCodeBench (Jain et al., 2025) takes the scheduled-refresh route from LiveBench and applies it to code, drawing its problems from programming contests held after each evaluated model's training cutoff. None of these four systems evaluates test generation. They evaluate code generation. The object produced is a function, not a test suite, and its correctness is checked against a fixed reference answer or a fixed set of assertions.

### 1.3 Test-generation benchmarks and their limits

Automated test generation predates large language models. EvoSuite (Fraser and Arcuri, 2011) and Pynguin (Lukasczyk and Fraser, 2022) synthesise test suites for object-oriented and Python code, using evolutionary search instead of a language model. Both establish the scoring principle this project relies on. A generated test suite can be judged by running it. It does not need comparison to a reference suite's text.

Recent work evaluates LLMs on the same task. Schafer et al. (2024) and Siddiq et al. (2024) study LLM-generated test suites empirically. TestEval (Wang et al., 2024) and the software-evolution study of Haroon et al. (2026) evaluate LLM test generation as their central concern. Haroon et al. track test quality as the codebase under test changes over time. MuCoCo (Chou et al., 2026) evaluates the consistency of code-generating LLMs through automated mutation-style perturbation, a close methodological relative of the scoring approach used here.

The static comparator this project measures against, UnLeakedTestBench, or ULT (Huang et al., 2026), is a response to contamination. Its authors decontaminate a corpus of real-world functions and construct a second, leaked twin, PLT, from the same functions. A contamination-consistent score gap between ULT and PLT becomes observable. This design is reused here as one of the project's contamination-evidence comparisons. Codex, evaluated on HumanEval (Chen et al., 2021), established code-generation benchmarking as a discipline. It is now widely reported as contaminated in later models. That is the failure mode a static release cannot avoid over time, however carefully it was built at release. BigCodeBench (Zhuo et al., 2025) serves in this project as an external, independently maintained code-generation proxy. It checks whether the dynamic benchmark's ranking of models agrees with a benchmark this project had no part in building.

None of the systems in this section combines template-based, seeded regeneration with a mutation-testing oracle for unit-test generation. That is the gap this project fills.

### 1.4 Mutation testing as the quality measure

A generated test suite can be scored three ways. It can be checked for coverage, the fraction of lines or branches it executes. It can be checked against a fixed set of reference tests, matching the generated suite's assertions to a known-correct answer key. It can be checked by mutation testing, where the function under test is altered in small, controlled ways and the suite is judged by how many of those alterations it catches.

Coverage measures whether code was executed. It does not measure whether the test suite would notice if that code were wrong. A test with no assertions can still achieve full coverage. Fixed reference tests avoid that problem, but they need a human-curated answer key for every problem. That answer key is a form of static content, and it can leak the same way a benchmark's problems can.

Mutation testing avoids both weaknesses. McCabe (1976) is the source of cyclomatic complexity, the structural measure this project uses to stratify its problem set into four tiers. Mutation testing's foundational case was made soon after, by DeMillo, Lipton, and Sayward (1978): a test suite's real job is to distinguish a correct program from a class of plausible incorrect ones, not to exercise lines of code. Jia and Harman (2011) survey four decades of mutation-testing research and show the method has matured into a standard technique. Andrews, Briand, and Labiche (2005) supply the empirical justification this project leans on: mutation score is an established, validated proxy for a suite's fault-detection ability, and it correlates with that ability more reliably than coverage does.

This project uses seven semantic-altering-change mutation operators: arithmetic, relational, and logical operator replacement, constant replacement, boundary mutation, statement deletion, and return or statement mutation, applied as single-edit mutants. A generated suite's mutation score is the fraction of these mutants it kills. This score is oracle-by-construction. Every generated problem instance carries a reference implementation, generated from the same template. No curated answer key is needed, so none can leak.

### 1.5 Where this project sits

This project combines three things no prior system combines in one place. The first is template-based, seeded regeneration of fresh problem instances at evaluation time. The second is a mutation-testing oracle as the scoring mechanism, in place of coverage or a fixed reference suite. The third is both an observational and a causal contamination comparison against the current static state of the art. The observational comparison measures nine models against the dynamic benchmark, against ULT, and against ULT's leaked twin PLT. The causal comparison fine-tunes a small open-source model on ULT's ground truth and measures whether the resulting score inflation transfers to the dynamic benchmark. A construct-validity check against BigCodeBench, an external benchmark this project had no part in building, confirms the dynamic benchmark measures a capability an independent instrument recognises.

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
| Compares | The dynamic benchmark's hardest tier against ULT | ULT against its leaked twin, PLT | One model, before and after fine-tuning on ULT's ground truth |
| Design | Observational: the same 9 canonical models scored on both benchmarks, no intervention | Observational: the same 9 canonical models scored on both benchmarks, no intervention | Causal: Qwen2.5-Coder-1.5B-Instruct, LoRA fine-tuned, scored pre and post on ULT, PLT, and Dynamic |
| Data | Dynamic-L4 vs ULT `core_400`, paired at model level | ULT vs PLT `core_400`, CC-band matched, paired at model level | 112 seen-ULT, 288 unseen-ULT, PLT `core_400`, Dynamic-L1-L3, Dynamic-L4, pre and post |
| Tests | H1 Test 1: dynamic scores lower than static, controlling for complexity | H1 Test 2: leaked PLT scores higher than decontaminated ULT | H2: fine-tuning inflates the static score more than the dynamic score |
| Statistic | Paired Wilcoxon signed-rank, rank-biserial effect size | Paired Wilcoxon signed-rank, rank-biserial effect size | 2×3 difference-in-differences on `baseline_pass_rate`, bootstrap CI |
| Verdict | Not supported: effect_r = -0.167, p=0.7422, opposite to the predicted direction | Supported in direction on every reading. Significance depends on which reading is quoted after Holm correction (section 2.9) | Supported, the strongest result in the project: +99.1pp on seen-ULT, +13.8pp on PLT after subtracting a generic fine-tuning control, 0.0pp on Dynamic-L4 |

Full statistics, caveats, and the paper-ready wording for all six hypotheses are in section 4.3. `analysis/HYPOTHESIS_DEVIATIONS.md` is the source these figures are read from.

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

**A complete, unedited example.** The raw test file Claude Sonnet 4.6 produced for section 1.4's `sum_values` problem, exactly as `extract_test_file()` extracted it from the model's response, nothing added or removed:

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

---

## 2. Project Life Cycle, Verification and Validation

{{FIGURE:flow_diagram|Figure 1. The dynamic benchmark's pipeline, from template corpus to hypothesis test. The two scoring gates and the three experiments described in this section are marked.}}

Before the phase-by-phase account below, Figure 1 sets out what the finished pipeline does end to end: a template becomes a seeded problem instance with an oracle and precomputed mutants, a model's response to that problem passes through the two scoring gates described in section 2.3, and the resulting record feeds the three experiments named on the diagram and, in turn, the six hypothesis tests in section 4.3.

### 2.1 The six gated phases, as executed

The project plan set out six gated phases over sixteen weeks. Phase *k+1* could not start until phase *k*'s deliverable passed a written checklist. A failed gate meant dropping a lower-priority item from a fixed cut list, not slipping the schedule.

Phase 1 froze the scope, the research questions, and the template-grammar specification. Phase 2 built and validated sixty templates and the instantiation engine. Phase 3 built the end-to-end scoring pipeline and piloted it on a thirty-problem subset. Phase 4 built the main Comparison-A table, the stability runs, and a sensitivity sweep. Phase 5 ran the two contamination comparisons. Phase 6 wrote up the six hypothesis tests and produced the submission.

Phases 1 to 3 ran close to plan. From Phase 4 onward, the supervisor asked for the stability and contamination work to be brought forward, so it did not wait for Phase 5 to start in the strict order the plan set out. Early stability signal from a still-partial Comparison-A data set fed into the decision to cut the fifth benchmark instantiation on 2026-07-15, months before Phase 6 began. The construct-validity check against BigCodeBench, the "bottom-up" comparison the supervisor asked for on 2026-07-27, was designed and run as a zero-compute analysis against whatever data existed on that date, instead of waiting for a complete data set a strict phase order would have required.

Phase 2's gate closed with the supervisor's sign-off on the sixty-template corpus on 2026-07-25. Phase 5's two contamination comparisons completed on 2026-07-27. Phase 6 began at the experimental freeze on 2026-08-12: data collection for the main study closed, and the write-up proceeded on the data as it stood, not as a moving target. At that point, 172 of 180 model by tier by instantiation cells were complete, 95.6%. The one remaining gap, both Gemini models' fifth instantiation, 600 problems across eight cells, was costed at $9.60 and declined, for the reasoning in section 2.6.

### 2.2 Corpus validation

Every template's cyclomatic complexity is computed at validation time and recomputed on every instance the template generates, since parameter sampling can shift a generated instance's control-flow shape out of its declared tier, the same recompute-not-trust principle section 1.6 describes for ULT/PLT. A within-tier diversity check compares every template against every other template in its tier and flags near-duplicate structure. The full sixty-template corpus passed with zero flags. A tier-separation sanity check confirms the four tiers do not overlap in complexity, and every template's reference oracle passes a property-based smoke test before acceptance into the corpus. Mutant density is checked against a target band per tier, five to ten mutants for the trivial tier up to twenty-five to forty for the compositional tier, and the evaluated population falls inside these bands 92.9% to 100% of the time across all seeds and instantiations.

### 2.3 The scoring harness

A model's response passes through three strictly sequential stages before it produces a score: an exec gate (does the test file import and collect), a baseline gate (does it pass against the real function), and mutation scoring (how many mutants does it kill). A response that fails a stage never reaches the next one, and a row that fails the baseline gate is excluded from the mutation-score average, not counted as a zero. Algorithm (c) in section 1.8 gives the exact procedure, with the real function it corresponds to.

Untrusted code, whether a model's generated test file or a scraped ground-truth function, is always executed from an isolated temporary directory, never from the project's working directory. Section 4.2 describes the incident that made this rule necessary.

### 2.4 The test suite, made concrete

The project's automated test suite collects 152 tests across the `tests/` directory, run with pytest. 16 of these are marked `torch` (need a working torch import) and are skipped in an environment without a working CPU torch install. The other 136 run everywhere:

{{FIGURE:evidence_test_suite|Figure 2. A real run of the test suite, tail output, captured live.}}

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

Each hypothesis test's design was committed to a written analysis plan before the result existed. The construct-validity check against BigCodeBench is a direct example. Its plan was written and committed before any correlation was computed, including the specific validity band the result would be judged against. The result contradicted the plan's prediction in one respect: the dynamic benchmark's agreement with BigCodeBench turned out to be at least as strong as the static benchmark's, not weaker, and the result is reported as found, including the failed prediction.

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

`scripts/build_thesis_assets.py` is a single-command registry: every table, figure, and provenance document the paper and this report cite is a registered step, regenerated from whatever result files exist on disk. `--list`, 28 steps at the time of writing:

```
comparison_ab             Comparison A (Dynamic-L4 vs ULT) + Comparison B (ULT vs PLT)
stability                 StableMut@K + pairwise Kendall tau (RQ4.1)
comparison_c              Comparison C canonical 2x3 DiD + gradient + Mut@K tables
rq5                       RQ5/H6 model-ranking table + cross-benchmark correlations
execution_evidence_figure Live-captured execution evidence, structural
check_doc_citations       GATE: fails the build on any unsuppressed stale citation
... 22 more steps
```

The last step is the gate: `scripts/check_doc_citations.py` checks every statistic-shaped value in `analysis/` and `paper/sections/*.tex` against a reference corpus built fresh from the pipeline's own output, and fails the build on anything that matches nothing live:

{{FIGURE:evidence_citation_gate|Figure 3. A real run of the citation gate, tail output, captured live.}}

A value is exempt only with an explicit reason, an inline `<!-- cite:historical -->`/`<!-- cite:external -->` marker or an `analysis/CITATION_ALLOWLIST.md` entry, logged as `SUPPRESSED`, counted separately from a genuine `MATCH`.

### 2.9 Statistical procedure

Every RQ family with more than one significance test applies Holm-Bonferroni correction through one shared function, `src/Analysis/multiple_comparisons.py::holm_bonferroni()`, before any document cites the result.

| RQ family | Tests corrected together | n |
|---|---|---|
| RQ1 | H1 Test 1 (Dynamic vs ULT), H1 Test 2 (ULT vs PLT). H2 is a bootstrap CI, not part of this family. | 2 |
| RQ4 | Pairwise instantiation-stability comparisons, N=4 set and the all-pairs set, corrected separately | 6, and 10 |
| RQ5 | Correlation tests behind H6 clauses 1 and 2 (canonical/cross-family, raw/coverage-adjusted, three statistics) | 12 |

Correction changed a verdict, not just a number: H1 Test 2's raw p=0.0391 becomes p=0.0782 once corrected, no longer clearing 0.05. Its definition-matched co-primary, p=0.0078, becomes p=0.0156 and still clears it, which is why that verdict (section 1.7) is reported as significance-conditional.

---

## 3. Tools

### 3.1 Language and environment

The project is written in Python 3.11, with type hints throughout. Dependencies and the virtual environment are managed with `uv`, chosen for reproducible, lock-file-based installs across the developer machine and the compute cluster. Python fits this project's subject matter: the benchmark evaluates Python code, so the same language runs the harness, the templates, and the models under test.

### 3.2 HPC cluster and job scheduler

Compute runs on Kelvin2, Queen's University Belfast's HPC cluster, under SLURM. Interactive sessions are used only for short tests, since they end if the connection drops. Every real workload is submitted as a batch job. The cluster offers several GPU partitions, chosen per job by size: a shared A100 in sliced mode for most fine-tuning and inference work, a bank of eight V100 nodes as a fallback when the shared A100 queue is busy, full A100 and H100 cards for larger models, and experimental AMD and Intel partitions not used in this project. Scratch storage, not the home filesystem, holds the HuggingFace model cache and all generated data, since scratch carries no quota and home does.

A slice of this project's own real job accounting on Kelvin2, from the week the main evaluation sweep ran:

{{FIGURE:evidence_slurm_jobs|Figure 4. This project's own SLURM job accounting (`sacct`), a fixed historical window, captured live.}}

The `FAILED` row is real, not curated out of the panel: this is exactly the kind of job the error ledger and section 4.2's lessons trace back to, a bug that only shows up after a real submission, not in a local dry run. The wide spread in `Elapsed` across otherwise identical `eval-mig` jobs, nineteen minutes to just over an hour, is why the partition choice described above is made per job by measured size, not by a single default.

### 3.3 Model-serving and fine-tuning stack

Six closed-source models are served through OpenAI's, Anthropic's, and Google's own APIs. Three open-source Qwen2.5-Coder sizes run locally through HuggingFace's `transformers`. Every model call is logged with its identifier, snapshot or revision, and full resolved decoding configuration, for the reason given in error-ledger bug 1. The causal contamination probe fine-tunes the smallest open-source model with low-rank adaptation, LoRA, using the `peft` library on top of `transformers`, on a single GPU slice. OpenAI's Batch API is used for the closed-source model calls that support it, at half the real-time cost.

### 3.4 Testing and coverage tools

The project's own test suite (section 2.4) and the benchmark's scoring harness (section 2.3, Algorithm (c) in section 1.8) both run on pytest, but are separate things: the harness uses `pytest --collect-only` for the exec gate and Python's `coverage` library for the statement and branch coverage secondary metrics, always inside the isolated-subprocess pattern section 2.3 describes.

### 3.5 Analysis and plotting stack

Result files are loaded and aggregated with `pandas`. Statistical tests, the Wilcoxon signed-rank test, Spearman and Pearson correlation, and the Holm-Bonferroni correction, use `scipy` and `statsmodels`. Every figure in the paper and in this report, including the flow diagram in section 2, is produced with `matplotlib`, run as a script and never built by hand, so a figure regenerates from the same data its caption describes.

### 3.6 Version control

The project is tracked in git throughout, commits grouped by logical change, not by working session. Large binary or generated files, model weights, raw result archives, and this report's rendered outputs, are excluded from the repository and backed up separately (section 6). One working session per checkout is a standing rule, section 4.2 explains why.

### 3.7 Document toolchain

The paper is written in IEEEtran LaTeX and compiled with `latexmk`. Every quantitative value the paper's prose cites is a macro read live from the analysis pipeline's output, checked by the citation gate described in section 2.5, so no result value is typed by hand into the paper's text. This report is written first as markdown, checked by the same citation gate, then rendered to a formatted Word document with `python-docx`. The slide deck is built with `python-pptx`. The flow diagram and every other figure are exported at print resolution as both PNG and PDF from the same `matplotlib` script.

### 3.8 AI coding assistant

*Draft, pending confirmation.* Claude Code, an AI coding assistant, was used throughout development: implementing the template engine, the scoring harness, and the analysis scripts from a specification the author wrote; investigating and fixing the bugs recorded in the error ledger; and drafting documentation, including this report, from the author's project records and decisions. Every design decision, every hypothesis, every interpretation of a result, and the decision to fine-tune, to cut an instantiation, or to decline further data collection, was the author's, made in consultation with the supervisor. The assistant did not choose what to test or what a result meant; it wrote code and prose to a specification and had its output reviewed before being relied on.

---

## 4. Critical Appraisal

### 4.1 Design and implementation decisions

**Template-generated problems instead of real-world code.** A benchmark built from real, scraped functions is a fixed artefact once published, and can leak the same way any other benchmark can. Template-generated problems are drawn fresh from a private grammar at evaluation time, so a specific problem instance need never be published. The alternative, drawing problems from a corpus of real repositories the way Code2Bench does, was rejected because that corpus is static content once assembled, and inherits the same leak risk this project set out to remove. The cost of this choice is disclosed in section 4.3: template-generated code may not carry the full structural variety of production code.

**Mutation score as the headline metric.** Section 1.4 sets out the case against coverage and against a fixed reference suite. Coverage does not check whether a test suite would catch a real fault. A fixed reference suite needs a human-curated answer key that can leak. Mutation score needs neither: each problem's reference implementation can generate its mutants, and the suite is scored by execution, not by comparison to hand-written text.

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

Section 5 states each hypothesis's verdict once, with the numbers behind it. This subsection asks what reporting all six together says, not what each one says individually.

**Why the null and dropped results are reported in full, not minimised.** H1's first test, H4, and H5 are not comfortable results for a project whose central claim is that its benchmark works. They are reported at the same length and with the same numbers as H2's strong result, because a benchmark's credibility rests on reporting what a pre-registered test found, not on reporting only the tests that came out favourably. H1's non-significant result still narrows the space of believable outcomes: it rules out one specific concern, that the dynamic benchmark's harder tier would look easier than ULT for reasons unrelated to contamination. H5's shortfall says something specific: the diagnostic work behind it shows the shortfall traces to several models clustering close together in score, not to the benchmark producing unreliable numbers, which is a materially different and more precise finding than "the benchmark is unstable."

**What the project achieved.** A working, end-to-end dynamic benchmark exists: sixty validated templates across four complexity tiers, a deterministic instantiation engine, and a mutation-testing harness that scores nine models with no dependence on a human-curated answer key. The causal contamination experiment produced clean, unambiguous evidence that fine-tuning on a static benchmark's ground truth inflates that benchmark's score while leaving the dynamic benchmark untouched. The project's central claim is demonstrated concretely, not assumed. The construct-validity check confirms the dynamic benchmark still tracks an external measure of code-generation capability, so contamination resistance was not bought at the cost of measuring nothing recognisable.

**What it did not achieve.** The causal result rests on one model, one fine-tuning method, and one hyperparameter setting. Nothing in the project tests whether the same clean separation between memorisation and transfer holds at a larger scale or under full fine-tuning. Rank-level stability across benchmark regenerations falls short of its pre-registered target, so a reader should trust each model's aggregate score more than a close ranking between two similarly scoring models. The equivalent-mutant validation, a hand-inspected sample meant to produce a corrected companion score alongside the raw headline figure, was not complete at the point this report was written, and the raw score is reported alone as a result.

**What would be done differently with the same time.** Generation-config logging and the citation gate would be built in week one, not discovered as a need partway through. Both would have prevented real, costly incidents, not only explained them after the fact. The fifth benchmark instantiation would be budgeted for from the start, not treated as a cut candidate, since stability turned out to be the hypothesis with the least margin to spare. More of the equivalent-mutant hand-inspection would be scheduled earlier, so it did not compete with write-up time at the end of the project.

**What the results do and do not support.** The results support treating a dynamic, template-based, mutation-scored benchmark as resistant to the specific contamination mechanism this project tested: direct fine-tuning on a static benchmark's ground truth. They do not support a claim that the benchmark's rankings are reliable enough to distinguish two closely scoring models with confidence, and they do not support any claim about contamination mechanisms this project did not test, indirect leakage through API logging, for one, which was named as a real route into contamination in section 1.1 but not isolated experimentally here.

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

This table is identical to the paper's own (`paper/table1.tex`), read live from the same workbook, not restated independently.

H2's headline figures, the strongest result in the project: fine-tuning Qwen2.5-Coder-1.5B-Instruct on ULT's own ground truth moves seen-ULT's `baseline_pass_rate` by +99.1 percentage points (95% CI [97.3, 100.0]), moves PLT by +13.8 percentage points (CI [7.7, 20.1]) once a measured +8.7pp generic-fine-tuning-improvement control is subtracted, and moves the dynamic benchmark's hardest tier by exactly 0.0 percentage points.

Full per-problem results are submitted as separate appendix files, not reproduced here: `docs/Research_questions.xlsx` (this table's own source) and `analysis/results.xlsx` (the per-problem dynamic-benchmark export). Every intermediate table lives in `analysis/` as citation-gated markdown and CSV.

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

runs the 136 tests that need no working torch install. `uv run pytest -q` runs the full 152 on a machine with one. Figure 2 (section 2.4) is a real, live capture of this exact command.

**Regenerate every table and figure with one command.**

```
uv run python scripts/build_thesis_assets.py
```

runs all 28 registered steps end to end (section 2.8) and finishes with the citation gate. A nonzero exit means at least one hand-written document cites a number the pipeline no longer produces. `--list` shows every step. `--only <key>` reruns just one.

**What `data/` contains, and why it is not in version control.** `data/raw/` holds the vendored ULT/PLT source (`PROVENANCE.md` documents how). `data/results/` holds one append-only JSONL file per model-benchmark-instantiation run. `data/batches/` and `data/finetune/` hold OpenAI batch state and the fine-tuning sets from section 1.6. None of it is hand-edited or small; it is backed up outside git instead, a dated snapshot on the cluster's home filesystem, since scratch storage is purged after three months of inactivity.

---

## References

James H. Andrews, Lionel C. Briand and Yvan Labiche (2005). Is Mutation an Appropriate Tool for Testing Experiments?. Proceedings of the 27th International Conference on Software Engineering (ICSE 2005). https://doi.org/10.1145/1062455.1062530

Joshua D. Angrist and Jörn-Steffen Pischke (2009). Mostly Harmless Econometrics: An Empiricist's Companion. Princeton University Press. https://doi.org/10.1515/9781400829828

Simone Balloccu, Patrícia Schmidtová, Mateusz Lango and Ondřej Dušek (2024). Leak, Cheat, Repeat: Data Contamination and Evaluation Malpractices in Closed-Source LLMs. Proceedings of EACL 2024. https://aclanthology.org/2024.eacl-long.5/

Nicholas Carlini, Daphne Ippolito, Matthew Jagielski, Katherine Lee, Florian Tramèr and Chiyuan Zhang (2023). Quantifying Memorization Across Neural Language Models. The Eleventh International Conference on Learning Representations (ICLR 2023). https://arxiv.org/abs/2202.07646

Simin Chen, Pranav Pusarla and Baishakhi Ray (2025). Dynamic Benchmarking of Reasoning Capabilities in Code Large Language Models under Data Contamination. Proceedings of the 42nd International Conference on Machine Learning (ICML 2025). https://arxiv.org/abs/2503.04149

Mark Chen et al. (2021). Evaluating Large Language Models Trained on Code. arXiv preprint. https://arxiv.org/abs/2107.03374

Chua Jin Chou, Khant That Lwin and Ezekiel Soremekun (2026). MuCoCo: Automated Consistency Testing of Code LLMs. arXiv preprint. https://arxiv.org/abs/2604.19086

R. A. DeMillo, R. J. Lipton and F. G. Sayward (1978). Hints on Test Data Selection: Help for the Practicing Programmer. Computer. https://doi.org/10.1109/C-M.1978.218136

Y. Dong, X. Jiang, X. Zhang, H. Liu, Z. Jin, B. Gu, M. Yang and G. Li (2026). Generalization or Memorization: Data Contamination for Large Language Models in Code Generation. IEEE Transactions on Software Engineering (early access). https://doi.org/10.1109/TSE.2026.3713834

Bradley Efron and R. J. Tibshirani (1994). An Introduction to the Bootstrap. Chapman and Hall/CRC. https://doi.org/10.1201/9780429246593

Gordon Fraser and Andrea Arcuri (2011). EvoSuite: Automatic Test Suite Generation for Object-Oriented Software. Proceedings of the 19th ACM SIGSOFT Symposium and the 13th European Conference on Foundations of Software Engineering (ESEC/FSE 2011). https://doi.org/10.1145/2025113.2025179

Batu Guan, Xiao Wu, Yuanyuan Yuan and Shaohua Li (2025). Is Your Benchmark Still Useful? Dynamic Benchmarking for Code Language Models. arXiv preprint. https://arxiv.org/abs/2503.06643

Sabaat Haroon, Mohammad Taha Khan and Muhammad Ali Gulzar (2026). Evaluating LLM-Based Test Generation Under Software Evolution. arXiv preprint. https://arxiv.org/abs/2603.23443

Sture Holm (1979). A Simple Sequentially Rejective Multiple Test Procedure. Scandinavian Journal of Statistics. https://www.jstor.org/stable/4615733

Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang and Weizhu Chen (2022). LoRA: Low-Rank Adaptation of Large Language Models. International Conference on Learning Representations (ICLR 2022). https://arxiv.org/abs/2106.09685

Dong Huang, Jie M. Zhang, Mark Harman, Qianru Zhang, Mingzhe Du and See-Kiong Ng (2026). Benchmarking LLMs for Unit Test Generation from Real-World Functions. ACM Transactions on Software Engineering and Methodology. https://doi.org/10.1145/3805043

Binyuan Hui et al. (2024). Qwen2.5-Coder Technical Report. arXiv preprint. https://arxiv.org/abs/2409.12186

Naman Jain, King Han, Alex Gu, Wen-Ding Li, Fanjia Yan, Tianjun Zhang, Sida Wang, Armando Solar-Lezama, Koushik Sen and Ion Stoica (2025). LiveCodeBench: Holistic and Contamination Free Evaluation of Large Language Models for Code. The Thirteenth International Conference on Learning Representations (ICLR 2025). https://arxiv.org/abs/2403.07974

Yue Jia and Mark Harman (2011). An Analysis and Survey of the Development of Mutation Testing. IEEE Transactions on Software Engineering. https://doi.org/10.1109/TSE.2010.62

Eunsu Kim, Juyoung Suk, Seungone Kim, Niklas Muennighoff, Dongkwan Kim and Alice Oh (2025). LLM-as-an-Interviewer: Beyond Static Testing Through Dynamic LLM Evaluation. Findings of the Association for Computational Linguistics: ACL 2025. https://doi.org/10.18653/v1/2025.findings-acl.1357

Stephan Lukasczyk and Gordon Fraser (2022). Pynguin: Automated Unit Test Generation for Python. Proceedings of the 44th International Conference on Software Engineering: Companion Proceedings (ICSE-Companion 2022). https://doi.org/10.1145/3510454.3516829

T. J. McCabe (1976). A Complexity Measure. IEEE Transactions on Software Engineering. https://doi.org/10.1109/TSE.1976.233837

Dayyán O'Brien, Barry Haddow, Emily Allaway and Pinzhen Chen (2025). MATHEMAGIC: Generating Dynamic Mathematics Benchmarks Robust to Memorization. arXiv preprint. https://arxiv.org/abs/2510.05962

Oscar Sainz, Jon Ander Campos, Iker García-Ferrero, Julen Etxaniz, Oier Lopez de Lacalle and Eneko Agirre (2023). NLP Evaluation in Trouble: On the Need to Measure LLM Data Contamination for each Benchmark. Findings of the Association for Computational Linguistics: EMNLP 2023. https://doi.org/10.18653/v1/2023.findings-emnlp.722

Max Schäfer, Sarah Nadi, Aryaz Eghbali and Frank Tip (2024). An Empirical Evaluation of Using Large Language Models for Automated Unit Test Generation. IEEE Transactions on Software Engineering. https://doi.org/10.1109/TSE.2023.3334955

Mohammed Latif Siddiq, Joanna Cecilia da Silva Santos, Ridwanul Hasan Tanvir, Noshin Ulfat, Fahmid Al Rifat and Vinícius Carvalho Lopes (2024). Using Large Language Models to Generate JUnit Tests: An Empirical Study. Proceedings of the 28th International Conference on Evaluation and Assessment in Software Engineering (EASE 2024). https://doi.org/10.1145/3661167.3661216

Gaurav Srivastava, Aafiya Hussain, Zhenyu Bi, Swastik Roy, Priya Pitre, Meng Lu, Morteza Ziyadi and Xuan Wang (2026). BeyondBench: Contamination-Resistant Evaluation of Reasoning in Language Models. International Conference on Learning Representations (ICLR 2026). https://arxiv.org/abs/2509.24210

W. Wang, C. Yang, Z. Wang, Y. Huang, Z. Chu, D. Song, L. Zhang, A. R. Chen and L. Ma (2024). TestEval: Benchmarking Large Language Models for Test Case Generation. arXiv preprint. https://arxiv.org/abs/2406.04531

Colin White et al. (2025). LiveBench: A Challenging, Contamination-Limited LLM Benchmark. International Conference on Learning Representations (ICLR 2025, Spotlight). https://arxiv.org/abs/2406.19314

Zhe Zhang, Runlin Liu, Aishan Liu, Xingyu Liu, Xiang Gao and Hailong Sun (2025). Code2Bench: Scaling Source and Rigor for Dynamic Benchmark Construction. arXiv preprint. https://arxiv.org/abs/2508.07180

Kaijie Zhu, Jiaao Chen, Jindong Wang, Neil Zhenqiang Gong, Diyi Yang and Xing Xie (2024). DyVal: Dynamic Evaluation of Large Language Models for Reasoning Tasks. International Conference on Learning Representations (ICLR 2024). https://arxiv.org/abs/2309.17167

Terry Yue Zhuo et al. (2025). BigCodeBench: Benchmarking Code Generation with Diverse Function Calls and Complex Instructions. International Conference on Learning Representations (ICLR 2025, Oral). https://arxiv.org/abs/2406.15877
