# Mut@K cross-definition audit — this project vs the ULT/PLT paper

**Revision history**: first written 2026-07-30 to resolve the
`src/eval/test_gen_scorer.py` TODO ("KILLED DEFINITION ... CONFIRM this
against ULT's methodology"), using a `WebFetch`-summarized (LLM-mediated,
non-verbatim) reading of the paper. That version concluded, as settled
fact, that ULT uses an unconditional/zero-fill definition and that this
project's `coverage_adjusted` score matches it. **Fully rewritten
2026-08-03** after re-verification against raw HTML (`curl`, not
`WebFetch`) and the paper's own published implementation
(`github.com/huangd1999/UnLeakedTestBench`) surfaced a genuine contradiction
between the paper's prose and its own code — see "Which one is 'the' ULT
definition?" below. The 2026-07-30 conclusion was **not fully wrong** (the
prose reading was accurate) but was **incomplete and one-sided** — it never
checked the paper's own code, and stated an inference as settled fact.

## 1. Evidence, verbatim

### 1a. The paper's prose (Section 3.4.3)

Source: Huang & Du et al., arXiv:2508.00408v1, fetched via `curl` (not
`WebFetch`) to `arxiv.org/html/2508.00408v1` and HTML-tag-stripped with a
plain Python regex — no LLM summarization step between the source and this
quote:

> "3.4.3. Mutation Score (Mut@k) Finally, we follow the existing work
> (jain2024testgeneval) and measure the fault-detection capability of the
> generated test cases using mutation score. Mutation score is a widely
> used metric in software testing that evaluates the effectiveness of a
> test suite in detecting faults (papadakis2019mutation; jia2010analysis).
> This metric involves automatically introducing small, syntactic changes
> (e.g., changing "+" to "-", or "≥" to "≤") into the function under test to
> create faulty versions known as "mutants". In our evaluation, we use
> Cosmic-Ray to generate all possible mutants for each function in ULT. A
> test suite "kills" a mutant if it fails when run against the mutated code
> but passes on the original. **The mutation score is the percentage of
> non-equivalent mutants that are killed by the generated test suite.** In
> our evaluation, for each function, we set timeout = 120 to avoid the test
> suite running indefinitely on a mutant. The mutation score is calculated
> as follows:
>
> (2) Mut@k = Σ(i=1 to N) Mi / N
>
> where Mi is the number of mutants killed by the test suite generated for
> the i-th function, and **N is the total number of functions in the
> benchmark**. A higher score indicates a more [effective test suite —
> sentence continues past the excerpt captured here; not load-bearing for
> what follows]."

Two things follow directly from this text, both load-bearing for the rest
of this audit:

1. **N is stated as a fixed constant ("the total number of functions in
   the benchmark"), not a per-model passing-only count.** If Mi=0 were not
   intended for non-passing functions, N would have to vary per model (as
   the passing count does) to keep the formula's arithmetic sane — which
   contradicts N being introduced as a benchmark-size constant. Taken
   completely literally, this is definition **(b)**: include-as-zero,
   unconditional mean.
2. **Mi is described as "the number of mutants killed"** — i.e. an
   integer *count*, not a per-function ratio. Taken completely literally
   alongside point 1, `Σ Mi / N` is an average raw kill-count, which is
   NOT a percentage and is not bounded in [0,1] — directly contradicting
   the same paragraph's own claim two sentences earlier that "the mutation
   score is **the percentage** of non-equivalent mutants... killed." This
   paragraph is internally inconsistent unless Mi is actually meant as an
   already-normalized per-function rate (Mi := killed_i / non-equivalent_i),
   with "number of mutants killed" being loose language carried over from
   Eq 1's Ci (a genuine raw count there, because Ci is bounded by a FIXED
   per-function budget K — see 1b). This project reads Mi as a rate for
   this reason, flagged as an inference from internal consistency, not a
   second directly-quoted confirmation.

### 1b. The paper's structurally analogous Pass@k formula (Eq 1), for comparison

> "3.4.1. Test Generation Accuracy (Pass@k)... A test is treated as
> "correct" if it compiles, runs to completion, and its assertions reflect
> valid expectations of the function's behavior for the given inputs...
> Pass@k... represents the average number of correct tests generated per
> function, normalized by the total number of test cases requested (K)...
> Ci is the number of correct tests generated for the i-th function (where
> 0 ≤ Ci ≤ K). If N is the total number of functions in the benchmark, the
> accuracy is computed as follows:
>
> (1) Pass@k = Σ(i=1 to N) Ci / (N × K)"

This is genuinely useful evidence for how to read Eq 2, because Pass@k's
Ci really is a raw count — but K is the SAME fixed budget for every
function (every function gets exactly K requested test cases), so
`ΣCi/(N×K)` is mathematically identical to a per-function macro-average of
rates, `(1/N)Σ(Ci/K)` — the count-vs-rate distinction is moot for Pass@k
specifically BECAUSE K doesn't vary. Mut@k (Eq 2) has no analogous "×K"
normalization term at all, and mutant counts genuinely do vary per
function (Cosmic-Ray "generate[s] all possible mutants," not a fixed
number — confirmed empirically for this project's own mutants below, §2).
Reusing Eq 1's Ci-as-count notational pattern for Eq 2's Mi without an
equivalent normalization term is the most likely explanation for the
internal inconsistency flagged in 1a point 2 — a notational carryover, not
a considered decision to average raw counts.

### 1c. Executability gate / equivalent mutants / import-fail handling — paper prose

A full-text search of the fetched paper (same raw-HTML, non-LLM extraction
method) for `import error`, `skip`, `dropped`, `filtered_tasks`, and
`executab` found:

- **No mention at all** of import-failure or execution-failure handling
  for individual MUTANTS (this project's "dropped" category). The paper's
  only uses of "executab-" concern (i) LLM-generated tests being
  executable, and (ii) filtering ULT's *source functions* for
  self-containment/testability during dataset construction — neither is
  about what happens when a mutant itself fails to import.
- **"Non-equivalent mutants"** appears exactly once, in the sentence quoted
  in §1a ("the percentage of non-equivalent mutants that are killed") —
  with no further explanation anywhere in the paper of HOW equivalence is
  determined or filtered. Automated equivalent-mutant detection is a
  famously unsolved problem in mutation testing generally, and Cosmic Ray
  (the tool ULT uses) has no built-in equivalence detector to this
  project's knowledge. This reads as aspirational/imprecise language
  rather than a described mechanism — see §1d for what the code actually
  does with "surviving" (undifferentiated) mutants.

### 1d. The paper's own published code

Source: `github.com/huangd1999/UnLeakedTestBench`, file `Ray/main.py`
(fetched via `raw.githubusercontent.com`, saved in full; this is the
file with the repo's own `if __name__ == "__main__":` CLI entry point —
the code path actually invoked to produce the paper's published numbers,
not a dead/experimental alternative).

```python
def cosmic_ray_setup_wrapper(benchmark_name, model_name, task_id, num_test_cases=5):
    working_dir = f'data/{benchmark_name}/mutation_{num_test_cases}/{model_name}/{task_id}'
    try:
        subprocess.run(['cosmic-ray', 'init', 'cosmic-ray.toml', 'cosmic-ray.sqlite'], cwd=working_dir, check=True)
    except Exception as e:
        print(f'[-] Initialize Cosmic-Ray Error: {e}')
        return False
    try:
        subprocess.run(['cosmic-ray', 'baseline', 'cosmic-ray.toml'], cwd=working_dir, check=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60*num_test_cases)
        return True
    except Exception as e:
        return False

def cosmic_ray_setup(benchmark_name, model_generation_file, num_test_cases=5):
    model_name = model_generation_file.split('/')[-1].split('.')[0]
    total_tasks = list()
    correct_tasks = list()
    ...
    for file_name in tqdm(os.listdir(f'data/{benchmark_name}/mutation_{num_test_cases}/{model_name}'), ...):
        if file_name.startswith('task_'):
            total_tasks.append(file_name)
    task_results = process_map(cosmic_ray_setup_wrapper, ...)
    with open(f'data/{benchmark_name}/correct_tasks_tc_{num_test_cases}_{model_name}', 'w') as f:
        for task_id, result in zip(total_tasks, task_results):
            if result:
                correct_tasks.append(task_id)
                f.write(f'{task_id}\n')
    print(f'[+] Correct Tasks: {len(total_tasks)} -> {len(correct_tasks)} (Convert Rate: {len(correct_tasks)/len(total_tasks):.2%})')

def mutation_statistic_wrapper(benchmark_name, model_name, num_test_cases, task):
    working_dir = f'data/{benchmark_name}/mutation_{num_test_cases}/{model_name}/{task}'
    statistic_info = {"task": task, "complete_rate": 0.0, "surviving_mutants_rate": 0.0,
                       "total_jobs_number": 0, "completed_jobs_number": 0, "surviving_mutants_number": 0}
    response = subprocess.run(['cr-report', 'cosmic-ray.sqlite', '--show-pending'], cwd=working_dir, ...)
    total_jobs_match = re.search(r"total jobs:\s*(\d+)", response.stdout)
    completed_jobs_match = re.search(r"complete:\s*(\d+)\s*\(", response.stdout)
    surviving_mutants_match = re.search(r"surviving mutants:\s*(\d+)\s*\(", response.stdout)
    # ... populates statistic_info fields from these regex matches ...
    statistic_info['surviving_mutants_rate'] = (
        statistic_info['surviving_mutants_number'] / statistic_info['completed_jobs_number']
        if statistic_info['completed_jobs_number'] > 0 else 0
    )
    return statistic_info

def mutation_statistic(benchmark_name, model_generation_file, num_test_cases, baseline_test_cases=5):
    model_name = model_generation_file.split('/')[-1].split('.')[0]
    correct_tasks = list()
    correct_tasks_path = f'data/{benchmark_name}/correct_tasks_tc_{baseline_test_cases}_{model_name}'
    with open(correct_tasks_path, 'r') as f:
        for line in f.readlines():
            correct_tasks.append(line.strip())
    print(f'[+] Correct Tasks: {len(correct_tasks)}')
    surviving_mutants_rate = 0.0
    statistics = process_map(mutation_statistic_wrapper, ..., correct_tasks, ...)
    for statistic in statistics:
        surviving_mutants_rate += statistic["surviving_mutants_rate"]
    surviving_mutants_rate = (surviving_mutants_rate / len(correct_tasks)) if len(correct_tasks) > 0 else 0.0
    print(f'[+] Surviving Mutants Rate: {surviving_mutants_rate:.2%}')
```

Key facts this establishes:

- **`correct_tasks`** = tasks whose baseline (unmutated) run passed via
  `cosmic-ray baseline` — this is Cosmic Ray's own single combined
  execute-and-assert gate (there is no evidence of a separate
  "does it even import" pre-check distinct from "does it pass," unlike
  this project's own two-stage `exec_ok` / `baseline_passed` split). This
  is exactly analogous to this project's `baseline_passed=True` condition.
- **`mutation_statistic()`'s final `surviving_mutants_rate` is summed over
  `correct_tasks` ONLY and divided by `len(correct_tasks)`** — a clean
  CONDITIONAL macro-mean over baseline-passing tasks, with **no
  zero-filling anywhere** for non-passing tasks. `total_tasks` (the full,
  unconditioned benchmark size) is used only to print a "Convert Rate" —
  essentially `baseline_pass_rate` — as a side log line, never as the
  denominator of the reported score.
- **This is definition (a)** — the SAME estimand as this project's own
  pre-registered primary conditional Mut@K — **not** the unconditional
  reading the prose (§1a) implies.
- **Per-mutant executability-style gate found**: `surviving_mutants_rate`
  is computed as `surviving_mutants_number / completed_jobs_number`, NOT
  `/ total_jobs_number` — i.e. the denominator excludes mutation jobs that
  did not complete, paralleling this project's own `scored = total -
  dropped` construction (dropped = failed to import). This is inferred
  from the field names and Cosmic Ray's own `cr-report` output structure,
  not confirmed against Cosmic Ray's internal source in this audit — flagged
  as a plausible parallel, not a proven one.
- **No code-level equivalent-mutant filtering was found anywhere** in
  `Ray/main.py`, `Ray/generate_mutation_details.py`, or
  `Ray/result_exporter.py`. "Surviving" mutants are whatever Cosmic Ray
  reports as not-killed, undifferentiated by equivalence — consistent with
  §1c's reading that "non-equivalent" in the prose is aspirational
  language, not a described/implemented mechanism.

(`Ray/result_exporter.py` has a separate, apparently older/alternate
`mutation_statistic()` that additionally intersects `correct_tasks` with a
`filtered_tasks` list loaded from a `filtered_tasks.json` — but it is NOT
the function `Ray/main.py`'s CLI entry point calls, its `filtered_tasks.json`
provenance is undocumented in the paper, and it still divides by
`len(correct_tasks)`, not by a full-benchmark or filtered-benchmark count —
so it does not change the conditional-vs-unconditional conclusion above
even if it were the invoked path.)

## 2. Which one is "the" ULT definition? — the ambiguity, stated plainly

**The paper's prose and the paper's own code disagree, and this audit does
not resolve that disagreement by picking a side.** Prose (§1a), read
literally, describes definition (b) (unconditional, zero-fill, N = full
benchmark size). Code (§1d), which is what actually produced the paper's
published ~40.21% average mutation score, implements definition (a)
(conditional macro-mean over baseline-passing tasks only) — the same
estimand as this project's own pre-registered primary.

Two readings are both defensible and neither is certain:

- **Code is stronger evidence of what was actually measured.** Formulas in
  papers are frequently simplified/idealized relative to the exact
  implementation detail (here: what happens to the denominator when a
  suite doesn't pass) — this kind of prose/code gap is common and doesn't
  imply bad faith. Under this reading, ULT's *actual* achieved methodology
  matches this project's pre-registered primary, and the "coverage_adjusted
  is the literature-matching score" framing from the 2026-07-30 note is
  backwards.
- **Prose is what a reader replicating the paper from its text (without
  reading the code) would implement.** Anyone citing Eq 2 or trying to
  reproduce "Mut@k" from the paper's own stated formula, without consulting
  `Ray/main.py`, would build definition (b) — so there is real value in
  this project also reporting a definition-(b)-matched score, labelled as
  such, for comparability with anyone in that position.

**This project's resolution: report BOTH, do not privilege either as "the"
correct ULT definition, and do not claim either of this project's own
metrics reproduces the ULT paper's own published ~40.21% figure without
this caveat attached.** The pre-registered conditional Mut@K remains the
sole primary metric (never swapped, per item 3 of the reconciliation
request that produced this rewrite); `coverage_adjusted` is reported as a
"definition-matched co-primary" — matched to the paper's PROSE, explicitly
NOT matched to the paper's own CODE (which instead matches the
pre-registered primary) — everywhere it appears.

## 3. Algebraic check — is `coverage_adjusted` exactly definition (b)?

**Setup, using this project's own scorer** (`src/eval/test_gen_scorer.py`).
For one model on one benchmark side, over its N = n_total attempted
problems:

- D = n_defined = count of rows with `mutation_score is not None`.
- D' = count of rows with `baseline_passed=True`.
- By construction, `mutation_score is None` iff `baseline_passed=False` OR
  (`baseline_passed=True` AND all of that problem's candidate mutants were
  "dropped" — failed to import — leaving 0 scorable mutants). So D ≤ D' in
  general, with equality unless that second, rarer condition occurs for at
  least one row.
- `mutk` (conditional Mut@K, the pre-registered primary) = mean of
  `mutation_score` over the D defined rows = `(1/D) Σ_{i∈defined} s_i`,
  where `s_i = killed_i / scored_i` is already a per-PROBLEM rate (mutant
  counts are normalized away inside each row before any outer mean is
  taken — see §3a for why this matters).
- `bp_rate` = mean of `baseline_passed` over all N rows = D'/N.
- `coverage_adjusted := mutk × bp_rate = (D'/(N·D)) Σ_{i∈defined} s_i`.
- **True definition (b)**, per the "Mi is a per-function rate" reading
  from §1a: `def_b_macro := (1/N) Σ_{i=1}^{N} Mi`, with `Mi = s_i` for
  defined rows and `Mi = 0` otherwise = `(D/N) Σ_{i∈defined} s_i`.

**`coverage_adjusted = def_b_macro` exactly iff D = D'.**

### 3a. Does per-problem mutant-count variance break this? (the specific concern raised)

No — and confirming why matters. This project's mutant generator
(`template_corpus/templates/_smoke/mutator.py::generate_mutants`) applies
7 operators (AOR, ROR, LOR, CR, BM, SDL, RSM) exhaustively over whatever
mutation sites exist in a function — no fixed cap, no stratified
subsampling at scoring time (the "60-mutant cap, stratified sampler" this
prompt's premise referenced was not found in the mutation-scoring path;
`scripts/build_equiv_mutant_sample.py`'s stratified 30-per-tier sample is
a SEPARATE, later hand-inspection audit pack for equivalent-mutant review,
not part of `mutation_score` computation). Mutant counts genuinely vary
enormously: empirically, `mutants_total` across the ULT core_400 rows for
one model ranges from **4 to 771**, mean **94.4**.

This variance does NOT make `mutk`/`coverage_adjusted`/`def_b_macro` a
weighted-vs-unweighted-mean problem, because `mutation_score` is already a
per-PROBLEM ratio (`killed_i/scored_i`) computed once per row before any
outer average runs — the outer mean treats every PROBLEM as one equally-
weighted unit regardless of how many mutants that problem happened to
generate. A genuinely different, mutant-count-sensitive statistic DOES
exist — a MICRO/pooled average that treats every MUTANT as one unit
instead (`Σ killed_i / Σ scored_i`, summed across all rows) — and this one
DOES differ meaningfully from the macro version:

| Benchmark | Model | macro (`coverage_adjusted`/`def_b_macro`) | micro (pooled) | gap |
|---|---|---|---|---|
| ult | gemini-3.1-pro-preview | 0.6509 | 0.5918 | 0.059 |
| ult | gemini-3.1-flash-lite | 0.2176 | 0.1692 | 0.048 |
| ult | claude-sonnet-4-6 | 0.1474 | 0.1149 | 0.032 |
| plt | gemini-3.1-pro-preview | 0.6352 | 0.5563 | 0.079 |
| dynamic_l4 | claude-haiku-4-5 | 0.2235 | 0.2292 | -0.006 |

(Full per-model table: computed live by
`scripts/build_comparison_tables.py`'s def-b cross-check; see that
script's `a_defb_check`/`b_defb_check` frames if reproducing.) Dynamic-L4's
macro/micro gaps are small (≤0.006) — its template-generated functions are
more mutant-count-homogeneous within a tier than ULT/PLT's scraped
real-world functions are across the whole benchmark, which is why this
distinction was invisible in this project's own Dynamic-only work and only
surfaced once ULT/PLT (4–771 mutants/function) entered the comparison.

**The macro (per-problem-equal-weight) reading is the one this project
reports**, for two reasons: it is the one dimensionally consistent with
Pass@k's own per-function structure in the SAME paper (§1b — one unit of
analysis = one function, not one mutant), and it is the one that is
provably identical to `coverage_adjusted`, which was already being
reported. The micro/pooled alternative is noted here for completeness (it
IS what "weighted vs unweighted" was anticipating) but not adopted as a
co-primary — including it as a third row throughout would spread thin the
5–7 model comparisons already short on power, for a reading with weaker
textual support.

### 3b. Empirical confirmation

Checked directly against every row in `data/results/{dynamic,ult,plt}` for
all 9 canonical models: **D = D' in every one of the 21 model×benchmark
cells with any defined data** (zero occurrences of `baseline_passed=True`
with 0 scorable mutants). `coverage_adjusted` and `def_b_macro`, computed
via two INDEPENDENT code paths (`mutk × bp_rate` vs
`paired_model_table(..., conditional=False)`, which never multiplies two
pre-aggregated quantities together — it reduces from raw rows directly),
agree to within **5.55e-17** (floating-point noise) for every model in
Comparison A and B — see `scripts/build_comparison_tables.py`'s
`a_defb_max_diff`/`b_defb_max_diff`, printed into
`analysis/COMPARISON_PROVENANCE.md` on every regeneration, not a one-off
manual check.

**Conclusion for item 2: PROVEN equivalent, empirically exact in 100% of
this project's current data (not merely close) — but this is an empirical
fact about this dataset (no row happens to have baseline_passed=True with
zero scorable mutants), not a logical guarantee that would survive future
data with that edge case.** The per-problem mutant-count variance the
prompt anticipated as the mechanism for a discrepancy does not, in fact,
create one for the macro/`coverage_adjusted` statistic — it would only
matter for the micro/pooled alternative, which this project does not
adopt as a co-primary (§3a).

## 4. Consequence audit

What changes under this reconciliation, and what doesn't, for every result
in the project built from Mut@K:

**Comparison A (Dynamic-L4 vs ULT), raw n_models=5.** Unaffected numerically —
`coverage_adjusted` was already being computed and reported as a
robustness row before this reconciliation; only ITS JUSTIFICATION changes
(no longer "matches the ULT paper," now "algebraically proven zero-fill
reading of the paper's prose, NOT of its code"). What's genuinely new:
raw-unfiltered effect_r=+0.200 (p=0.81), thin-cell-filtered raw
effect_r=**-1.000** (n_models=3, p=0.25), definition-matched/coverage-adjusted
effect_r=**-0.600** (p=0.31) — **the sign now disagrees between the
raw-unfiltered reading and BOTH other readings** (thin-filtered and
definition-matched agree with each other, not with the unfiltered
headline). See §5 for the verdict this implies.

**Comparison B (ULT vs PLT), raw n_models=7.** Also numerically unaffected by
this reconciliation itself (same "already computed, now proven and
labelled" situation) — but newly extended here with a thin-cell audit and
a co-primary row that didn't exist before 2026-08-03 (Comparison A had
one; Comparison B didn't). Result: raw effect_r=+0.714 (p=0.109),
thin-filtered raw effect_r=+0.867 (n_models=5, p=0.125), definition-matched
effect_r=**+0.929 (p=0.031, the only one of any of these six numbers —
across both comparisons — that clears p<0.05)**. All three Comparison B
readings agree in sign (PLT scores higher than ULT, the expected
contamination direction) — the definition-matched/co-primary version is
not just consistent, it is the STRONGEST evidence for Comparison B's
contamination signal found anywhere in this project to date.

**RQ5's three correlation families** (Dynamic↔ULT, Dynamic↔public,
ULT↔public — `analysis/RQ5_INTERPRETATION.md`). **Numbers unchanged** —
τ=0.905 (canonical Dynamic↔ULT), 0.855 (cross-family Dynamic↔ULT), 0.905 /
0.714 (cross-family Dynamic/ULT↔BigCodeBench) were already computed from
`coverage_adjusted`, which this audit proves IS the definition-matched
score, not a different one. What changes is the CAPTION under those
numbers: they should no longer be described as "the metric that matches
the ULT paper's methodology" without the §2 caveat — they match the
paper's PROSE, not its CODE, and its CODE matches the OTHER metric
(conditional Mut@K, τ=0.143 / 0.345), the one whose cross-benchmark
agreement is near-zero. This is worth sitting with: **the metric that
happens to numerically match ULT's own published implementation is the
one this project's diagnosis found to have the WEAKER cross-benchmark
validity signal, not the stronger one** — a genuinely uncomfortable fact
for any framing that leans on "this matches the literature" as
validation. `analysis/RQ5_INTERPRETATION.md` is updated with this note
directly (see its "Cross-definition reconciliation" section).

**Pre-registered validity-zone verdict**
(`analysis/RQ5_ANALYSIS_PLAN.md`'s ρ 0.4–0.8 = validity-supporting,
near-perfect = redundant zones, applied in
`analysis/RQ5_INTERPRETATION.md`'s "Bottom-line construct-validity
statement"). **Unaffected.** That verdict is a function of the τ VALUE
(0.905, sitting at/above the "redundant" line) relative to the
pre-registered zones, not of which paper's methodology the metric happens
to match — τ=0.905 is τ=0.905 regardless of this section's findings. The
verdict ("neither candidate primary-metric reading lands in the
validity-supporting zone") stands exactly as written.

**H1's Wilcoxon.** This IS Comparison A's Wilcoxon test (there is no
separate H1 test elsewhere in the codebase) — covered above. Under the
pre-registered primary (raw, unfiltered) it was never significant
(p=0.81); under every other reading tried it remains non-significant
(p=0.25–0.31) — H1 was never supported and remains unsupported under this
reconciliation. What's new is that the DIRECTION (not just the
significance) is now shown to be unstable across conditionings, which is a
stronger caution than "not significant" alone.

## 5. Recompute + directional-stability verdict

Full tables: `analysis/COMPARISON_PROVENANCE.md` (regenerated by
`scripts/build_comparison_tables.py`, which now computes the
definition-matched co-primary and thin-cell filtering for BOTH Comparison
A and B, not just A as before this reconciliation).

**Comparison A: no version of this comparison supports a directional
claim at the current n.** Three conditionings were tried (raw-unfiltered,
raw-thin-filtered, definition-matched), and they do not agree on sign:
raw-unfiltered says ULT > Dynamic-L4 (effect_r=+0.200); thin-filtered and
definition-matched both say Dynamic-L4 > ULT (effect_r=-1.000, -0.600).
This is the SECOND sign flip found for Comparison A under different
conditionings this project has tried (first: raw vs coverage-adjusted,
found 2026-07-30 and re-confirmed here; second: raw-unfiltered vs
thin-cell-filtered, found in this reconciliation). None of the three
readings reaches significance (p=0.25–0.81) at n≤5. **The honest
conclusion is not "the effect is X, but weak" — it is that this project's
current data cannot establish which of Dynamic-L4 or ULT scores a given
model higher, under any definition of Mut@K tried so far.** This should be
stated exactly this plainly in any write-up that reports Comparison A.

**Comparison B: directionally stable, and gets STRONGER, not weaker,
under the definition-matched score.** All three conditionings agree PLT
scores higher than ULT (the expected direction if PLT's "leaked" functions
give models an unfair advantage): raw effect_r=+0.714 (p=0.109),
thin-filtered +0.867 (p=0.125), definition-matched +0.929 **(p=0.031)**.
This is the one result in this audit where the reconciliation makes the
project's existing story MORE defensible, not less — worth foregrounding
in any discussion-chapter treatment of the contamination signal, with the
appropriate caveat that "definition-matched" still means "matches the
ULT paper's prose, not its code" per §2.
