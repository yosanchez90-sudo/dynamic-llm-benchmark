# ECS8056 — Rubric validation and action plan

Inputs reviewed: `paper_v3.pdf` (8 pp, IEEE, US Letter), `SUPPORTING_REPORT_v2.docx`
(~8,560 words of body text, 32 references), `Rubric_ECS8056.pdf`.

**How to use this file with Claude Code.** Each task has an ID (`P0-1`, `PA-3`, …), the
rubric criterion it serves and its weight, the file to touch, what to change, and an
acceptance check. Work top-down: P0 first, then P1, then P2. Every task is scoped so it
can be done without new experiments — no task here asks for more compute or new results.

Companion files:
- `FIGURE_TABLE_SPEC.md` — figure and table style rules (from the annotated screenshots).
- `REFERENCE_AUDIT.csv` — all 32 supporting-report references, with a home for each.

---

## 0. Where the two documents currently stand

The work itself is strong: pre-registration, a clean causal result, an error ledger, a
citation gate. Almost everything below is about **surfacing** work already done into the
place the rubric looks for it, not about doing more work.

### Research paper (70%)

| Criterion | Wt | Read | Why |
|---|---|---|---|
| Introduction | 10% | Mid | Aim and objectives are clear; RQ1–RQ5 exist only inside a table note, no contributions list, no explicit scope/boundaries |
| Literature review | 10% | Mid–upper | Coverage is good and current; gap is asserted in prose rather than shown; little critical evaluation of individual works |
| Methods | 25% | Mid | Benchmark design is detailed; **no hyperparameters anywhere** (LoRA config, decoding params, training schedule), statistical procedure scattered |
| Experimentation & Results | 30% | **Low relative to weight** | **No hardware/software reporting at all** (top band requires it explicitly); **no main results table**; H3 and H5 have no table or figure |
| Discussion | 5% | Upper | Genuinely good — threats to validity, the 0.438 observation, the ULT contradiction |
| Conclusion & Future Work | 5% | Upper | Present, summarises, names scoped-out work |
| **AI Ethical Considerations** | 5% | **~0** | **The section does not exist.** Zero occurrences of ethics/bias/privacy/fairness/transparency in the PDF |
| Quality & references | 10% | Mid | References are clean; figures carry titles and in-plot prose, Table I overflows the margin |

### Supporting material (30%)

| Criterion | Wt | Read | Why |
|---|---|---|---|
| **Complementary literature** | 20% | **~0** | **No literature section exists.** Zero in-text citations of any kind (no `[n]`, no author-year), yet 32 references are appended |
| Project life cycle + V&V | 30% | Mid–upper | Content is there and honest; uses its own Phase 1–6 vocabulary, never the rubric's stage names; "verification" appears once, only in a heading; no timeline artefact, no risk register |
| Tools | 30% | Mid–upper | Good coverage and some real justification; no versions, no tool→stage mapping, several tools named without a reason for choosing them |
| Critical appraisal | 20% | **Upper** | The strongest part of either document. Leave it alone apart from typo fixes |

---

## P0 — Blocking gaps

These three are the difference between a good submission and a distinction-level one.
Each is currently scoring near the bottom of a weighted criterion for the same reason:
the work exists, but not in the document the marker grades it in.

---

### P0-1 · Add an AI Ethical Considerations section to the paper
**Criterion:** AI Ethical Considerations · **5%** · currently unaddressed
**File:** `paper/sections/` — new section, place it after Discussion (§5), before Conclusion.

The rubric's top band asks for **biases, privacy, fairness, and transparency**. Write
~250–350 words, one short paragraph per theme, all four named explicitly. This project has
unusually good material for each — do not write generic AI-ethics filler:

- **Transparency / dual use.** Publishing DyMuT's template grammar would contaminate it,
  the exact failure the benchmark is built to avoid. State the resolution: release the
  generator and the seeds, not a frozen instance set, so results are reproducible without
  creating a memorisable artefact. This is the most interesting ethical point in the paper.
- **Privacy and the contamination channel.** Evaluating via commercial APIs sends benchmark
  content to providers who may retain it for training — the mechanism Balloccu et al. [2]
  document, and the mechanism this project itself participates in by evaluating six
  closed-source models. Disclose it, and state the mitigation (dynamic instances mean a
  leaked evaluation run does not leak the benchmark).
- **Bias and fairness in the instrument.** Template-generated problems reflect the author's
  own idea of what test-generation difficulty looks like; the identifier bank and docstring
  synonyms are English-only; ULT contains non-English prompts (the real record quoted in the
  supporting report is Spanish), so a language effect is a live confound the study does not
  control. Also: comparing frontier API models against small local models on a single
  prompt template advantages neither fairly — state it.
- **Safety of execution.** Model-generated code and scraped ground truth are executed. Say
  what the isolation guarantee is and what it is not (subprocess + temp cwd ≠ sandbox) —
  §5 already admits this; reference it rather than repeating.
- **Declared AI assistance.** One sentence, consistent with supporting-report §3.8 and with
  whatever the module's declaration rules require.

**Acceptance:** the words *bias*, *privacy*, *fairness*, and *transparency* each appear at
least once in the section, and each is attached to a specific fact about this project.

---

### P0-2 · Add hardware, software and reproducibility reporting to the paper
**Criterion:** Experimentation and Results · **30%** — the single highest-weighted criterion
**File:** `paper/sections/` — new §3.7 "Experimental Environment", or a §4.0 preamble.

The Excellent-Distinction wording is *"Exceptionally details about hardware and software
for full reproducibility."* The paper currently mentions hardware **once**, in the
acknowledgment. Everything needed is already in supporting-report §3.2/§3.3 — pull a
compact version into the paper (~150 words plus a small table if space allows):

- Cluster and scheduler: Kelvin2 (QUB), SLURM; GPU partitions actually used (shared A100 in
  MIG/sliced mode, V100 fallback, full A100/H100 for larger models) and the rule for
  choosing per job.
- Software: Python 3.11, `uv` lock-file environment, and pinned versions of
  `transformers`, `peft`, `torch`, `pytest`, `coverage`, `pandas`, `scipy`, `statsmodels`,
  `matplotlib`. Version numbers, not names alone.
- Scale actually run: number of instantiations (N = 4 headline, partial 5th), problems per
  instantiation (300), models (9 canonical + cross-family extension), total model calls,
  and the completeness figure — **172 of 180 model×tier×instantiation cells, 95.6%** — with
  the named gap (both Gemini models' 5th instantiation) and the cost that was declined.
- Cost and provenance: total spend, use of the OpenAI Batch API at half rate, and the fact
  that every call logs model id, snapshot, resolved decoding config, seed and timestamp.
- Repository URL and the single regeneration command (`build_thesis_assets.py`).

**Acceptance:** a reader with a cluster account could re-run the study from the paper alone,
without opening the supporting report.

---

### P0-3 · Add a complementary literature section to the supporting report
**Criterion:** In-depth investigation of context and literature · **20%** of the 30% component
**File:** `SUPPORTING_REPORT` source markdown — new §1.2 (renumber the rest) or a new §2.

This is the clearest scoring gap in either document. Measured facts:

- The body contains **zero in-text citations** — no `[n]`, no `(Author, year)`, not one.
- **24 of the 32 references have no trace in the body at all** (not even by name).
  The 8 with any trace — bootstrap, Holm, LoRA, ULT, Qwen, cyclomatic complexity,
  Code2Bench, BigCodeBench — are mentioned as concepts, never cited.
- The words *literature*, *ethics*, *bias*, *privacy* appear zero times.

So the reference list currently reads as decoration. **The fix is not to delete references
— it is to write the section the rubric is asking for**, which gives all 32 a home. See
`REFERENCE_AUDIT.csv`: every one of the 32 has a natural place once this section exists.

Write ~1,500–2,000 words that **complement** rather than repeat the paper's §2 (the top
band rewards *"profound analysis of methodologies, strengths, weaknesses, and trends"*):

1. **A comparison table of dynamic/contamination-resistant benchmarks** — one row per work
   (DyVal, LiveBench, LiveCodeBench, BeyondBench, MATHEMAGIC, LLM-as-an-Interviewer,
   DyCodeEval, Code2Bench, Guan et al.), with columns: *generation mechanism · domain ·
   correctness oracle · contamination evidence offered · what it cannot do*. This makes the
   gap visible instead of asserted, and is reusable as a paper table (see PA-2).
2. **A second table for LLM test-generation evaluation** (TestEval, Schäfer et al., Siddiq
   et al., Haroon et al., MuCoCo, ULT/PLT, plus EvoSuite/Pynguin as the pre-LLM baseline):
   *what is scored · oracle · contamination handling · why it was not adopted here*.
3. **Critical evaluation, not summary.** For the three or four closest works, state one
   concrete methodological weakness each and what this project does about it. The ULT
   prose-vs-code contradiction (error ledger bug 8) belongs here in full — it is original
   critical work on a SOTA baseline and currently only appears as a caveat in the paper.
4. **Trends and what they imply.** Regeneration-at-eval-time is converging across domains;
   what is missing is an executable oracle. Say why test generation is the case where the
   oracle problem is solvable by construction.
5. **Literature that shaped decisions, cited in place.** Carlini et al. on memorisation
   scaling → why the *smallest* open model was chosen for the probe. Jia & Harman on
   equivalent mutants → §1.5. Andrews et al. → mutation score as a fault-detection proxy.
   McCabe → the tier design. Angrist & Pischke, Efron & Tibshirani, Holm → §2.9.

**Also add in-text citation markers throughout the existing body** (tools, methods,
statistics, §4.1's rejected alternatives). Pick one style and use it in both documents —
IEEE numeric `[n]` is the safer choice given the paper is IEEE.

**Acceptance:** every reference in the list is cited at least once in the body; no
uncited entries remain.

**Fallback if a word limit blocks this:** trim the reference list to the ~10 that support
tool and method choices (rows marked `keep-minimum` in the CSV) and accept the lower band
on a 20% criterion. Check the word limit before choosing this path — see V-1.

---

## P1 — High-value additions (paper)

### PA-1 · Add the main results table
**Criterion:** Experimentation and Results · 30% · **File:** new `paper/tableN.tex` in §4

The paper reports hypothesis outcomes but **never reports the benchmark's headline
descriptive results**. There is no table anywhere showing how the nine models actually
scored. Add one, before §4.1:

Rows: 9 canonical models. Columns: `exec_rate`, `baseline_pass_rate`, conditional Mut@K
(primary), coverage-adjusted Mut@K (co-primary) — for **DyMuT (pooled)** and for **ULT**,
plus `n_defined` per cell. Mark thin cells (`n_defined < 20`) with the same symbol used in
Fig. 2 and define it in the caption.

This is the table a reader looks for first, and its absence currently reads as an omission
rather than a choice. It also gives Mistral-7B's exec 96.7% / baseline-pass 1.7% pattern
(quoted in the supporting report) a place to live in the paper.

### PA-2 · Add a related-work comparison table
**Criterion:** Literature review · 10% · **File:** `paper/sections/related_work.tex`

Condense P0-3's table 1 to five or six rows and one column set that ends in *"why it does
not answer this question"*. Top-band wording is *"identifies research gaps with compelling
evidence, clearly differentiates the proposed approach."* A table does that in a way the
current closing paragraph ("The gap. No prior study combines…") only asserts.

### PA-3 · Give H3 and H5 a visual
**Criterion:** Experimentation and Results · 30%

Two pre-registered hypotheses currently have **no table and no figure**:
- **H3 (§4.5)** — add mutation score by tier (L1→L4), one line per model, or a compact
  9×4 table. The monotone decline is the benchmark's core validity evidence and it is
  currently a sentence.
- **H5 (§4.6)** — add StableMut@K: per-model mean ± SD across the four instantiations, and
  the pairwise Kendall τ values. The claim "SD 0.001–0.004 but τ = 0.583" is much more
  convincing shown than stated, and it directly supports the argument that the shortfall is
  model clustering, not instrument noise.

If page budget is tight, PA-3's H3 table can be a 4-column tier summary rather than
per-model, and H5 can reuse the Fig. 3 heatmap style.

### PA-4 · Report the hyperparameters
**Criterion:** Methods · 25% — the top band asks for *"hyperparameter tuning detailed with strong rationale"*

Nothing in the paper states a single hyperparameter. Add to §3.5 and §3.4:
- LoRA: rank, alpha, dropout, target modules, learning rate, schedule, batch size, epochs
  (the epoch axis in Fig. 1 runs to 30 — say what a checkpoint at epoch 30 means), training
  context length (3,072 tokens, per the supporting report's tokenizer filter), and the
  train-set size (1,014 pairs after filtering; 112 of them in the evaluation subsample).
- Decoding: temperature, top-p, max tokens, and **K = 1**, stated once with a rationale.
- The rationale matters as much as the values: say what was and was not tuned, and that
  nothing was tuned on the outcome metric.
- Add one sentence on `no_repeat_ngram_size` — that it is explicitly *not* set and why
  (error-ledger bug 1). It is a genuine methodological warning other researchers would want,
  and it costs one line.

### PA-5 · Consolidate the statistical procedure into Methods
**Criterion:** Methods · 25%

Move the correction-family structure from supporting-report §2.9 into a short §3.x:
RQ1 family n=2; RQ4 families n=6 and n=10 corrected separately; RQ5 family n=12; H3's
all-tier (9/9) and ceiling-robustness (8/8) families. State the `n_defined < 20` thin-cell
threshold here rather than at first use in §4.7. State the pre-registered validity band
(0.4–0.8) here too.

Add one sentence justifying the **DiD parallel-trends assumption**, and point at Fig. 1 as
the evidence for it — the shared epoch-0→1 jump across all three arms is exactly the
diagnostic. Currently the design cites Angrist & Pischke but never states its identifying
assumption, which is the first thing a methods-aware marker will look for.

### PA-6 · Strengthen the H2 metric substitution
**Criterion:** Experimentation and Results · 30% / Discussion · 5%

§4.1 substitutes `baseline_pass_rate` for mutation score because the pre-treatment mutation
score is undefined for 111 of 112 problems. The reasoning is sound and honestly disclosed,
but the paper already defines a metric that **is** defined pre-treatment: `coverage_adjusted`
(non-passing suites scored zero). Report the DiD on `coverage_adjusted` alongside
`baseline_pass_rate`, and note the post-treatment conditional Mut@K of 0.438 in the same
place rather than only in §5. That turns a disclosed limitation into a three-metric result
and removes the strongest objection available to a marker.

Also: **Table II's unseen-ULT row (+15.6 pp) is never discussed.** Net of the 8.7 pp
control, held-out ULT problems still gain ~6.9 pp. That is transfer within the static
benchmark and it is interesting — one or two sentences, not silence.

### PA-7 · Make the Introduction hit its rubric wording
**Criterion:** Introduction · 10%

Three concrete changes:
1. **State RQ1–RQ5 in the text.** They currently exist only in a highlighted note under
   Table I. Top band asks for *"aligned research questions/hypotheses"* — a marker should
   not have to read a table note to find them.
2. **Add an explicit contributions list** (3–4 bullets or a compact paragraph): the
   benchmark artefact; the paired observational + causal contamination design; the
   construct-validity check; the ULT ground-truth reproducibility finding.
3. **Add scope and boundaries explicitly**: Python only; single-function problems;
   semantic-altering mutation operators only (SPC out of scope); K = 1; nine models;
   one fine-tuning scale. The top band asks for *"scope comprehensively with clear
   boundaries and limitations"* — these facts are scattered through §3, not stated as scope.

### PA-8 · Reframe the incomplete equivalent-mutant validation
**Criterion:** Methods 25% / Discussion 5%

§3.6 currently reads present-tense ("A validated companion score **is** separately
obtained…") and then says the inspection is not complete. That contradiction invites the
reader to see an unfinished method. Reframe as a **pre-specified, deliberately bounded
limitation**: the sampling design was fixed in advance (120 mutants, 30 per tier, fixed
seed), the correction is not applied, and therefore the reported raw score is a **lower
bound** on the true mutation score — uniformly across models, so comparisons are unaffected.
Cite Jia & Harman on the equivalent-mutant problem. Same fact, correctly framed.

### PA-9 · Elevate the ULT ground-truth finding
**Criterion:** Literature review 10% / Discussion 5%

The finding that ULT's published prose formula and its published scoring code disagree,
plus the 26.7% complexity-label mismatch on 3,909 records, is original critical work on the
state-of-the-art baseline. It currently sits in a threats-to-validity paragraph. Give it a
short named paragraph in §4 or a clearly signposted subsection in §5. Keep it factual and
neutral in tone — report what was recomputed and what disagrees, without editorial.

---

## P1 — High-value additions (supporting report)

### PS-1 · Map the project onto the rubric's own lifecycle vocabulary
**Criterion:** Stages of the project life cycle · **30%**

The rubric names five stages: **planning, development, implementation, testing, evaluation**.
§2.1 uses Phase 1–6 instead, so a marker has to do the translation. Add a short mapping
table at the head of §2: *rubric stage → this project's phases → deliverable → gate that
closed it → where it is evidenced in this report*. Cheap, mechanical, directly ticks a
30% criterion.

### PS-2 · Add an explicit verification-vs-validation table
**Criterion:** Stages of the project life cycle · 30% — the band wording is
*"Thoroughly explains the methods used for verification and validation"*

The word *verification* appears **once** in the whole document, in a heading. The activities
are all there — they are just never labelled. Add a table: *activity → verification or
validation → what it guards → where it runs → what happens on failure*. Rows: corpus CC
recompute, within-tier diversity check, tier-separation check, oracle smoke tests, the
152-test pytest suite, the three regression tests, exec gate, baseline gate, mutant-drop
handling, citation gate, the 13-script validator audit, dedup-by-timestamp, canonical-model
filter, the independent-billing reconciliation.

Then add one paragraph on *why* the distinction matters here: verification asks whether the
harness does what it was specified to do; validation asks whether a mutation score means
test quality — which is what H3 and H6 exist to answer. That single paragraph is the
"demonstrating a clear understanding of their importance" clause.

### PS-3 · Add a timeline artefact and a risk register
**Criterion:** Stages of the project life cycle · 30%

- **Timeline figure**: 16 weeks × 6 phases, planned vs actual, with the real deviations
  already described in §2.1 marked on it (stability/contamination work pulled forward, the
  2026-07-15 fifth-instantiation cut, the 2026-07-25 corpus sign-off, the 2026-07-27
  BigCodeBench check, the 2026-08-12 experimental freeze). Prose describing a schedule
  scores lower than a schedule.
- **Risk register**: 6–8 rows — *risk → likelihood/impact → mitigation → did it fire?*
  Real ones this project actually ran into or dodged: provider model retirement (it fired —
  the Gemini substitution), cluster queue contention, budget overrun, ground-truth quality
  (it fired), scope creep on hypotheses, and data loss (scratch purge after 3 months).
  A register whose entries actually fired is far more convincing than a generic one.

### PS-4 · Turn §3 into a tools matrix
**Criterion:** Description of tools · **30%** — band wording is *"Demonstrates a clear
understanding of how each tool supports different stages of the project"* and *"justifying
their selection"*

Keep the current prose, add a table in front of it: *tool → version → lifecycle stage(s) it
supports → why chosen over the alternative considered*. Currently `uv`, Python, LoRA and
mutation testing have real justifications; `pytest`, `pandas`, `matplotlib`, `git`,
`python-docx`, `python-pptx`, `latexmk`, `scipy`/`statsmodels` are named without one. Also
missing from §3 entirely though used: VS Code Remote-SSH, git worktrees (mentioned only in
§4.2's lesson), `coverage`, HuggingFace Hub/`transformers` cache layout, `peft`.

Version numbers matter here — the top band says *"comprehensive and detailed description of
all tools… including software, hardware, and frameworks."*

### PS-5 · Resolve the two editorial placeholders
**Criterion:** any marker's first impression

- §3.8 opens with ***"Draft, pending confirmation."*** — resolve and delete the marker.
  Confirm the wording against the module's AI-declaration rules and make it a finished,
  confident paragraph.
- The Table of Contents is the placeholder text *"Right-click and choose 'Update Field'…"*.
  Generate a real TOC with page numbers before submission.

Both are the kind of thing that costs disproportionate credibility for zero content reasons.

---

## P2 — Consistency and correctness

### Naming and cross-references

| ID | Where | Fix |
|---|---|---|
| C-1 | Supporting report, throughout | **"DyMuT" appears zero times.** The paper's benchmark has a name; the supporting report only ever says "the dynamic benchmark" / "Dynamic-L4". Introduce DyMuT once in §1 and use it throughout, so a marker reading both documents sees one project |
| C-2 | Both titles | Paper: *"Dynamic, Template-Based Benchmarking Resists Contamination-Induced Score Inflation…"*; supporting: *"Memorisation-Robust Benchmarking of LLM Test Generation…"*. Align them, or state the relationship in the supporting report's opening line |
| C-3 | Supporting §1.7 | "Full statistics… are in section 4.3" — §4.3 is *Evaluation with hindsight* and contains no statistics. The verdict table is in §5. Fix the pointer |
| C-4 | Supporting §4.3 | "Section 5 states each hypothesis's verdict once, **with the numbers behind it**" — §5's table has no numbers except H2's. Either add the numbers to §5's table or drop the clause |
| C-5 | Supporting §1.1 | The RQ/hypothesis figure (`image1.emf`) has no figure number or caption, unlike Figures 1–5. Caption and number it; renumber the rest |
| C-6 | Supporting §2.6 | Typo: "commiStted" → "committed" |
| C-7 | Supporting §5 | "This table is identical to the paper's own (paper/table1.tex)" — the paper's Table I has an extra RQ column and different row ordering. Either make them identical or reword |
| C-8 | Both | Confirm the appendix files named in §5 (`docs/Research_questions.xlsx`, `analysis/results.xlsx`) are actually in the submission bundle |

### Paper text fixes

| ID | Where | Fix |
|---|---|---|
| C-9 | §4.1 / Fig. 1 | The figure legend says **"DyMuT L1/L2 (control)"**, the text and Table II say **L1–L3**. The caption's parenthetical admits they are different populations, which reads as an error being explained rather than a design. Rename the plotted series to something unambiguous — e.g. "DyMuT L1–L2 (epoch series)" vs "DyMuT L1–L3 (endpoint control)" — and say in one clause why two controls exist |
| C-10 | Table II | Titled "four of five populations" while the fifth (DyMuT L4, 0.0 pp) sits in prose. Add the fifth row, add a **DiD column** so the reader is not left to compute 22.5 − 8.7 = 13.8, and state in the caption that the metric is `baseline_pass_rate`, not Mut@K |
| C-11 | §4.2 | Grammar: *"on a stronger model's GPT-5's, generations"* → *"on a stronger model's generations (GPT-5)"* |
| C-12 | §4.2 | *"The decline appears in both cross-model conditions…"* — "the decline" is introduced only in the following sentence. Reorder so the held-out execution-rate decline is stated before it is referred back to |
| C-13 | §4.2 / Table III | The third condition is *"non-leaked comparison point"* in prose and **"none (control)"** in the table. Use one label in both |
| C-14 | §3.6 | Tense contradiction — see PA-8 |
| C-15 | §3.4 | "Claude Sonnet 4.6 / Claude Haiku 4.5 / Gemini 3.1 Pro Preview" — verify each model string and snapshot date against the run logs before submission; snapshot ids belong in the environment table (P0-2) |
| C-16 | §3.3 | Statement and branch coverage are described as secondary metrics in the supporting report (§3.4) but never reported in the paper. Either report them or remove the claim from the supporting report |
| C-17 | §4.7 | *"another's DyMuT- and ULT 5 and 1"* — malformed; rewrite the thin-cell parenthetical |
| C-18 | Abstract | "Six hypotheses were pre-specified" then nine rows in Table I (two H1 tests, two H6 clauses, one supplementary). Add a clause: six hypotheses, nine tested clauses, plus one post-hoc probe |

### IEEE format

| ID | Fix |
|---|---|
| C-19 | Sections are numbered in **arabic** ("1 INTRODUCTION", "3.1", "4.1"). IEEEtran's conference default is roman for sections and letters for subsections ("I. INTRODUCTION", "A. …"). Confirm against the template the module actually distributed; if it is stock IEEEtran, revert to the default rather than overriding it — the criterion says *"Adherence to IEEE conference and reference formats is flawless throughout"* |
| C-20 | Table I overflows the text block — see `FIGURE_TABLE_SPEC.md` §T-1 |
| C-21 | Reference list: all 32 entries have DOIs or arXiv links and are consistently formatted. No action beyond a final `latexmk` pass with no undefined-citation warnings |

---

## Verify before submission

| ID | Check |
|---|---|
| V-1 | **Page limit for the paper and word limit for the supporting report.** P0-1 through PA-9 add roughly 1–1.5 pages to an 8-page paper. If a hard limit binds, cut §4.2 (H2-supplementary) to a short paragraph plus Table III and push its detail into the supporting report — it is explicitly post-hoc and outside the six pre-registered hypotheses, so it is the correct thing to compress |
| V-2 | Run `build_thesis_assets.py` end to end after all edits; the citation gate must exit zero. Every new number added by P0-2, PA-1, PA-3, PA-4 must come from the pipeline, not be typed by hand |
| V-3 | Regenerate all figures after applying `FIGURE_TABLE_SPEC.md`; check each at 100% zoom in the compiled PDF, not in the plotting window |
| V-4 | Confirm the module's AI-assistance declaration requirement and that §3.8's final wording satisfies it |
| V-5 | Optional: a final literature-currency sweep for anything published since the draft was written. The lit-review band rewards *"recent, state-of-the-art"* sources, and dynamic benchmarking is moving fast |

---

## Suggested order of work

1. **P0-1, P0-2** — paper ethics section and environment section. Two new sections, no new data, ~9% of the total mark currently unclaimed.
2. **P0-3** — supporting-report literature section. Largest single block of writing; also resolves the reference question.
3. **PA-1, PA-3, PA-4, PA-5** — the results-and-methods reporting gaps.
4. **PS-1, PS-2, PS-4** — three tables in the supporting report against a combined 60% of that component.
5. **Figures and tables** — `FIGURE_TABLE_SPEC.md`.
6. **P2 consistency pass**, then **V-1…V-5**.
