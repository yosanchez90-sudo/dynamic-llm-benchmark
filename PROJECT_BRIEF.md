# Project Brief — Memorisation-Robust Benchmarking of LLM Test Generation

> Canonical, distilled reference for this dissertation. Keep this in the repo root
> alongside `README.md` and `CLAUDE.md`. `README.md`/`CLAUDE.md` own the *operational*
> details (how to run things, environment, current state). This file owns the *plan*
> (what the project is, what it must deliver, and in what order). When code and this
> brief disagree, treat the code + `CLAUDE.md` as ground truth for *state* and this
> brief as ground truth for *intent*.

- **Full title:** Memorisation-Robust Benchmarking of LLM Test Generation: A Dynamic, Template-Based Benchmark with Complexity-Tiered Mutation Analysis
- **Student:** Yohan Sneider Sanchez Vega (40492566) · **Supervisor:** Pinzhen Chen
- **Module:** ECS8056 MSc AI Themed Research Project (25/26)

---

## 1. The one-paragraph thesis

Static benchmarks for LLM test generation get contaminated the moment they are
published: the act of evaluating models leaks benchmark content into training corpora,
via RLHF and web-scraped interaction data. This project
builds a **dynamic, template-based benchmark** where every problem instance is
generated *at evaluation time* from a parameterised template, organised into four
cyclomatic-complexity tiers (L1–L4). Test-generation quality is measured primarily by
**mutation score**, plus executability, statement coverage, and branch coverage. The
work delivers (a) a contamination-resistant evaluation protocol, (b) a controlled
comparison against the static state-of-the-art (**ULT** and its leaked twin **PLT**),
and (c) a contamination-simulation experiment that **fine-tunes a small open-source LLM
on static benchmark data** and shows the dynamic benchmark neutralises the resulting
score inflation.

---

## 2. Objectives (O1–O8)

| ID | Objective (condensed) | Phase | Deliverable |
|----|-----------------------|-------|-------------|
| O1 | Frame the contamination problem; position against existing benchmarks via literature review. | 1 | Related-work chapter |
| O2 | Design the contamination-resistant protocol: template grammar, complexity tiers, seed-based instantiation, docstring-synonym system. | 1 | Phase-1 specifications (Parts A/B/C) |
| O3 | Build the template corpus: 60 templates, each with parameter domain, reference oracle, docstring template. | 2 | 60 validated templates |
| O4 | Build a deterministic, seed-based instantiation engine producing fresh instances at eval time, reproducible across runs. | 2 | Instantiation engine + seed-determinism tests |
| O5 | Implement the mutation-based evaluation pipeline: 7-operator SAC catalogue + metrics. | 3 | Mutation engine, harness, metrics pipeline |
| O6 | Evaluate 9 LLMs across tiers on (i) 5 dynamic instantiations and (ii) the ULT static baseline. | 4 | Master metric table; stability + sensitivity tables |
| O7 | Provide observational + causal evidence of contamination resistance, incl. a LoRA fine-tune on Qwen2.5-Coder-1.5B. | 5 | ULT-vs-PLT deltas; 2×3 DiD table; LoRA results |
| O8 | Analyse and synthesise: stability, within-family scaling, provider effects, cross-pool agreement, proxy correlation; write up. | 6 | Submitted dissertation + reproducibility artefacts |

---

## 3. Research questions

- **RQ1**: How much does dynamic, template-based generation reduce contamination-induced score inflation vs a static SOTA benchmark (ULT)?
- **RQ2**: How does generated-test effectiveness (mutation score) vary across the four CC tiers (L1–L4)?
- **RQ3**: Are static benchmarks more prone to *overestimating* performance at *lower* tiers than higher ones, vs the dynamic benchmark?
- **RQ4.1**: *Stability.* Are LLM rankings stable across multiple independent instantiations (is the protocol a reliable instrument)?
- **RQ4.2**: *Within-family scaling (closed-source).* Frontier-vs-efficient mutation-score gap per provider, dynamic vs ULT. Three providers, triangulated answer.
- **RQ4.3**: *Within-family scaling (open-source).* Same on the Qwen 32B/7B/1.5B sweep (3 points). Compare curve shape against closed-source pairs.
- **RQ4.4**: *Provider effect at matched tier.* Compare the three frontier slots (and the three efficient slots) at fixed tier. Is any provider more contamination-susceptible?
- **RQ5**: How well does dynamic-benchmark test-gen performance correlate with code-gen performance on a proxy benchmark (BigCodeBench), and does the correlation differ dynamic vs static?

## 3.1 Hypotheses → statistical test (Layer-2 inferential)

| RQ | Hypothesis | Test |
|----|-----------|------|
| RQ1 | H1 (observational) | Paired Wilcoxon signed-rank, dynamic vs ULT mutation score at **model level** (one paired observation per model: Dynamic and ULT/PLT share no problem identity, so a literal model–problem pairing isn't possible. Corrected 2026-08-04 from an earlier "model–problem level" phrasing that never matched the implementation.) |
| RQ1 | H2 (causal) | Difference-in-differences on the 2×3 design (pre/post fine-tune × ULT/PLT/Dynamic) |
| RQ1 | H2-supplementary (post-hoc, not part of the approved set) | Seen-vs-fresh instantiation `baseline_pass_rate`, per training source (self-contamination / cross-model contamination / non-leaked control), both Qwen sizes. Robustness replication of H2's mechanism at the instantiation level, not the benchmark level. |
| RQ2 | H3 | Spearman ρ between tier index and mutation score, per model and pooled |
| RQ3 | H4 | **CLOSED, not built.** Approved by Pinzhen Chen 2026-08-05. Declared untestable-by-construction: ULT/PLT contains no low-CC problems (CC≥8 filter applied by the source paper's authors), so it has zero tier overlap with Dynamic's L1-L3 range. A tier×benchmark interaction term cannot be estimated when one side of the interaction has no variation in the tier variable. Quantified in `analysis/H4_DESIGN_MEMO.md` (Dynamic L1-L3 = CC 1-7, entirely below ULT/PLT's CC≥8 floor. Dynamic L4's CC 8-11 overlaps only ~41% of ULT/PLT's CC range, with no internal Dynamic tier variation inside that overlap). No mixed-effects model was built. `statsmodels` was not added as a dependency. RQ3 is answered narratively instead, by H3's within-Dynamic tier gradient (`analysis/H3_INTERPRETATION.md`: every canonical model's mutation-killing effectiveness declines monotonically with tier, Holm-corrected, 9/9 significant) combined with this structural finding (a CC-filtered static benchmark cannot even pose the "does static overestimate more at lower tiers" question, which is informative about what such benchmarks can be used for). |
| RQ4 | H5 | Pairwise Kendall τ between rankings across instantiations |
| RQ5 | H6 | Pearson r + Spearman ρ between mutation score and proxy Pass@1 |

Corrections: Holm–Bonferroni **within each RQ family**. Effect sizes with CIs are primary; p-values support.

---

## 4. Scope

**In scope:** Python only · function-level test generation · 4 CC tiers (L1–L4) with
secondary descriptors (AST depth, edge-case count) · **60 templates (15/tier), m=5
instances/template/instantiation → 300 problems/instantiation** (m, not K: K is
reserved for Pass@K-style attempts/problem, which is a different quantity that
happens to also be 5 in one sensitivity sweep) · **5 instantiations**
(design target) **for stability, executed as 4** per the pre-registered gate
cut-priority · 7 SAC mutation operators ·
4 metrics + StableMut@K · zero-shot & one-shot prompting · comparison vs ULT
(decontaminated) and PLT (leaked) · cross-task correlation vs BigCodeBench ·
within-tier diversity analysis.

**Out of scope:** non-Python · class/repo-level generation · property-based testing as
the rigour gate (future work) · formal equivalent-mutant detection (use a validated
sample instead) · human test-quality evaluators · fine-tuning a *frontier* model (only
a small open-source model is fine-tuned).

**Future work:** SPC (semantic-preserving) robustness extension · DyCodeEval-style
multi-agent context generation · a second language (Code2Bench-style) · PBT-with-coverage
gates · continuous benchmark maintenance from emerging repos.

---

## 5. Key design decisions

### 5.1 Complexity tiers
| Tier | CC | Signature | Target mutants/program |
|------|----|-----------|------------------------|
| L1 Trivial | 1 | Single path; no branches/loops; pure transformation | 5–10 |
| L2 Branching | 2–3 | Conditional logic; disjoint branches; no iteration | 10–15 |
| L3 Iterative | 4–7 | One or two loops with boundary conditions; possible early exit | 15–25 |
| L4 Compositional | ≥8 | Nested branches + loops; multiple failure modes | 25–40 |

CC is computed statically at template-validation time and **recomputed on each
generated instance** to confirm tier membership. AST depth + distinct edge-case count
are recorded as secondary descriptors.

### 5.2 Templates & instances
A **template** = body skeleton with placeholders + parameter-domain spec + oracle
(reference implementation) + docstring template. Each template yields m instances by
sampling its parameter domain; variable names, values, constants, and docstring synonyms
vary across instances. Instances are validated post-hoc: CC must stay in-band, and the
oracle must pass a lightweight property-based smoke test. A **benchmark instantiation**
= one full generator run (60 templates × m=5).

**Notation note (added 2026-08-05, terminology audit):** this brief previously used
`K` for both instances-per-template (this section, §4, §12) and Pass@K-style
attempts-per-problem (§5.4), the same symbol, and in several places the same
numeric value (5), for two different quantities. Fixed here and throughout this
document: **`K` is reserved for attempts/problem** (§5.4's Pass@K-style usage,
matching Exec@K/Cov-S@K/Cov-B@K/Mut@K and the `K` field recorded in every
result row, `src/eval/test_gen_problem.py`). **`m` denotes instances/template**,
a prose-only symbol with no code equivalent (the code represents this quantity as
`len(instance_seeds)` on a 5-element seed tuple, never a variable literally named
`K` or `m`). This is a documentation/prose fix only.
No code identifier is renamed. Every run in this project used K=1 (one attempt per
problem), so "Mut@K" should be read as "Mut@1" throughout unless a K=5 sensitivity
sweep is explicitly named, and that sweep was cut (§8's gate-cut-priority
item #1) and never run.

### 5.3 Mutation operators — SAC only (headline)
Arithmetic Operator Replacement (**AOR**), Relational Operator Replacement (**ROR**),
Logical Operator Replacement (**LOR**), Constant Replacement (**CR**), Boundary Mutation
(**BM**), Statement Deletion (**SDL**), Return/Statement Mutation (**RSM**). Single-edit
per mutant. Cap **30 mutants/instance** (sample if more). SPC operators are future work.

**Deviation, disclosed 2026-08-04 (full audit: `analysis/
MUTANT_COUNT_SPEC_AUDIT.md`): the 30-mutant cap and stratified sampler
were never implemented.** `generate_mutants()` returns every mutation
site the 7 operators find, uncapped, for both Dynamic and ULT/PLT. In
practice this only matters for Dynamic's L4 tier: L1-L3 land inside their
§5.1 target bands without ever approaching 30 mutants (0% of rows exceed
it), but L4's target band (25-40) exceeds this
section's 30-mutant cap, and 93.3% of real L4 rows exceed 30. The corpus
was built to satisfy the per-tier band, and this section's blanket cap was
the part that went unenforced, not the reverse. ULT/PLT mutants are
**intentionally** uncapped (mean 94.8/80.7, up to 771/991 for individual
functions) to match the source paper's "generate all possible
mutants" methodology, required for Comparison A/B to compare against
ULT/PLT on like terms. Checked whether this affects any reported
conclusion (macro-mean vs a micro/pooled alternative that would be
sensitive to this variance): no change to Comparison A's or B's reported
qualitative direction. Some reordering possible among closely-scored
models on ULT/PLT (`MUTANT_COUNT_SPEC_AUDIT.md` §(d)).

### 5.4 Metrics (Pass@K-style naming, K = attempts/problem)
| Metric | Symbol | Meaning | Level |
|--------|--------|---------|-------|
| Executability | Exec@K | Fraction of suites that import/run without raising at collection | **Gate** (>0 to score the rest) |
| Statement coverage | Cov-S@K | Mean line coverage over executable suites | Secondary |
| Branch coverage | Cov-B@K | Mean branch coverage over executable suites | Secondary |
| Mutation score | Mut@K | Killed / total mutants (raw); validated variant divides by total − est. equivalent | **Headline** |
| Coverage-adjusted score | `coverage_adjusted` | Mut@K × baseline_pass_rate: a zero-filled/unconditional co-primary, added 2026-08-03 | Co-primary |
| Stability | StableMut@K | Mean Mut@K across the instantiations (4 executed, 5 design target), SD reported | Stability |

Headline K=1; sensitivity sweep at K=5. Temperature fixed **0.2** (ULT convention),
max output 2048 tokens, deterministic seeding where the API exposes it.

**Mut@K is conditional, not unconditional.** Disclosed here 2026-08-04
after an external review found this table didn't make the distinction
explicit. As implemented (`src/eval/test_gen_scorer.py::score_problem`),
Mut@K is the mean mutation score **over baseline-passing problems only**.
A problem whose generated suite fails against the original, correct
function is **excluded** from the mean entirely, not scored as 0. This is
the pre-registered primary metric throughout this project and is never
swapped out. A second, zero-filled/unconditional reading also exists
(`coverage_adjusted` above = Mut@K × baseline_pass_rate, proven
algebraically and empirically identical to a true zero-filled mean,
`analysis/RQ5_CROSS_DEFINITION_AUDIT.md` §3) and is reported everywhere as
a labelled co-primary, not a replacement. The two are different estimands
even for identical data (a model with a low baseline-pass rate can show a
high conditional Mut@K while its coverage-adjusted score is much lower).
`analysis/METRICS_AND_FINDINGS_EXPLAINED.md` §2 has the full definitions
and known failure modes of each. `analysis/RQ5_CROSS_DEFINITION_AUDIT.md`
documents an unresolved contradiction between the ULT/PLT paper's stated
Mut@k formula and its published code, which this distinction turns out to
be the crux of.

### 5.5 Equivalent mutants
Standard = raw score (pessimistic, comparable). Validation = 30 mutants/tier hand-inspected
(120 total). Report a sample-validated score + estimated equivalent-mutant rate with CIs.

**Note (2026-08-04): this is a different thing from the ULT/PLT paper's
"non-equivalent mutants" language.** That paper's prose claims its
Mut@k reports "the percentage of non-equivalent mutants that are killed,"
but no equivalent-mutant detection or filtering exists anywhere in its
published code (`analysis/RQ5_CROSS_DEFINITION_AUDIT.md` §1c,
`analysis/ULT_DATA_QUALITY_AUDIT.md` finding 3). This project's
validated-sample estimate above should not be assumed comparable to
whatever the paper's "non-equivalent" qualifier is describing.

---

## 6. The 9 models (subjects under test)

| Provider | Frontier | Efficient |
|----------|----------|-----------|
| OpenAI | GPT-5.4 | GPT-5.4 mini |
| Anthropic | Claude Sonnet 4.6 | Claude Haiku 4.5 |
| Google | Gemini 3.1 Pro Preview | Gemini 3.1 Flash-Lite |
| Open-source (Qwen2.5-Coder) | 32B · 7B · 1.5B (three-point sweep) | — |

Google row is a forced substitution for the originally-specified Gemini 2.5
Pro/Flash. Model-ID
consistency check (2026-07-26): every Dynamic-benchmark and ULT/PLT
core_400 result row's `model`/`model_revision` fields read exactly
`gemini-3.1-pro-preview` / `gemini-3.1-flash-lite` with no drift between the
two result sets (checked against `data/results/dynamic/`,
`data/results/ult/`, `data/results/plt/`).

---

## 7. The three comparisons (contamination evidence)

- **Comparison A: Dynamic vs ULT** (Phase 4). Headline effectiveness numbers, the main-study table.
- **Comparison B: ULT vs PLT** (Phase 5, observational). PLT = leaked twin of ULT. Expect PLT scores systematically higher at matched CC → the observational contamination signal.
- **Comparison C: Small-LLM fine-tuning** (Phase 5, causal). Fine-tune Qwen-1.5B on ULT (LoRA/QLoRA), re-evaluate on ULT / PLT / a fresh Dynamic instantiation. Expected pattern: large gain on ULT, possibly larger on PLT, **near-zero gain on Dynamic**: the contamination-resistance evidence. 2×3 difference-in-differences table.

---

## 8. Roadmap — six gated phases (16 weeks)

Phases are **gated, not overlapping**: phase *k+1* cannot start until *k*'s deliverable
passes its checklist. A failed gate means **dropping a non-critical item**, not slipping
the next phase.

| Phase | Weeks | Theme | Headline deliverable |
|-------|-------|-------|----------------------|
| 1 | 1–2 | Foundations | Frozen scope; final RQs; template-grammar spec (+ tier criteria, mutation catalogue) |
| 2 | 3–6 | Template engine & tiers | 60 validated templates (L1 w3, L2+engine v1 w4, L3 w5, L4+review w6) + instantiation engine |
| 3 | 7–8 | Mutation & eval pipeline | End-to-end: seed → all 4 metrics for 1 LLM; pilot on 30-problem subset |
| 4 | 9–11 | Main experiments | Comparison A (Dynamic vs ULT), stability runs (inst 2–5, Kendall τ), K=5 + one-shot sensitivity |
| 5 | 12–13 | Contamination experiments | Comparison B (ULT vs PLT) + Comparison C (fine-tune, 2×3 DiD) |
| 6 | 14–16 | Analysis & writing | Six hypothesis tests, figures/tables, full draft, submission |

**Gate cut-priority (drop in this order, each preserves every RQ):**
1. K=5 sensitivity sweep → 2. two of the LLMs → 3. one-shot prompting → 4. the fifth dynamic instantiation.
**Cut #4 invoked 2026-07-15.**

**Phase gates (self-assessment checklists):**
- **P1:** spec + tier table + mutation catalogue reviewed; 2 sample templates/tier hand-written and pass validation; supervisor confirmed RQs.
- **P2:** 60 templates pass validation; within-tier diversity check run (failing templates rewritten); tier-separation sanity done; supervisor sign-off on corpus.
- **P3:** pilot produced sane metric values (all in [0,1], non-trivial, L1≥L2≥L3 qualitatively); wall-time projection fits Phase-4 budget; result schema under version control.
- **P4:** headline Comparison-A table reviewed; stability + sensitivity tables exist; per-LLM mutant kill traces stored.
- **P5:** Comparison-B table + Comparison-C 2×3 table exist with documented interpretation; all raw outputs archived.
- **P6:** submission deadline met.

---

## 9. Data schema (one row per evaluation)

- **Identifiers:** model, instantiation_id, template_id, instance_seed, K, prompting_condition, benchmark.
- **Outcomes:** exec_rate, statement_coverage, branch_coverage, mutation_score, mutants_total, mutants_killed, mutants_dropped_for_import_failure, generation_latency_seconds.

Datasets: the **dynamic benchmark** (generative, 5 seeded instantiations; templates are
private, not released) · **ULT** (static SOTA baseline; CC-stratified 300–500 subsample
for closed-source free-tier APIs, full set for local open-source) · **PLT** (leaked twin)
· **BigCodeBench** (code-gen proxy for RQ5).

---

## 10. Environment (summary)

- HPC: Kelvin2 (QUB), scratch workspace under `/mnt/scratch2/users/40492566/dissertation/`.
- Stack: Python 3.10.5, CUDA 12, `uv`-managed venv; multi-provider harness (HuggingFace + Anthropic + OpenAI + Google); SLURM batch submission.
- Fine-tuning: LoRA/QLoRA on Qwen-1.5B (fits the MIG slice; larger Qwen sizes do not).

*(If any of the above has changed, `CLAUDE.md`/`README.md` are authoritative.)*

---

## 11. Deviations from the original roadmap — UPDATE ME

> The supervisor requested bringing the **stability** and **memorisation/contamination**
> experiments forward, so the actual execution order has diverged from the strict
> Phase 4 → 5 → 6 sequence above. Record the *actual* order and current status here so
> future sessions don't re-derive it. Suggested fields:

- **Reordering rationale:** _(supervisor asked to prioritise stability + memorisation experiments)_
- **Actual phase/task order being followed:** _(fill in)_
- **Work completed to date:** _(fill in, link files/results)_
- **In flight / blocked:** _(fill in)_
- **Note on OpenAI runs:** originally the supervisor generated L3/L4 outputs (he held
  the OpenAI credits. Results arrived as JSONL + `.error` files for ingestion). As of
  2026-07-14 the supervisor is out of credits. GPT batches now run under the
  student's OpenAI account instead (same `scripts/create_batch.py` path, batch
  discount still applies since that's a property of the Batch API, not whose account
  funds it). GPT-5/gpt-5-mini backfill held back from this account until
  separately funded. Only Anthropic and Gemini are running now.
- **Gate cut-priority items #1 and #3 invoked, formally recorded 2026-08-12
  (decisions themselves predate this entry, recorded here for completeness,
  since only item #4 below had previously received a dated §11
  paragraph despite all three appearing in the workbook's experiment-
  status column as CUT):**
  - **#1, K=5 sensitivity sweep: CUT, never run.** The 60-template corpus
    would have been re-evaluated at K=5 attempts/problem (Pass@K-style) as
    a robustness check on the headline K=1 result. Dropped first per §8's
    stated order. No run of any kind exists under `prompting_condition`
    or `K=5` anywhere in `data/results/` (confirmed:
    `scripts/coverage_matrix.py`'s DEFERRED lane reports zero K=5 rows
    every time it has been run this project). §12's glossary
    states this in passing ("a K=5 sensitivity sweep was cut (§8) and
    never run"). This is that same fact given a dated record.
  - **#3, one-shot prompting sweep: CUT, never run.** The same corpus
    would have been re-evaluated with a one-shot (single in-context
    example) prompt variant alongside the headline zero-shot condition.
    Dropped third per §8's order, after item #2 (dropping two of the
    LLMs) was never invoked. The full 9-model canonical panel was
    completed, so item #2 was skipped over, not exhausted. No
    `prompting_condition=one_shot` rows exist anywhere in `data/results/`.
  - **Net effect on scope**: of §8's four-item cut-priority list, items #1
    and #3 were fully invoked (zero-cost, nothing built or run under
    either condition), item #4 was partially invoked (N=4 achieved instead
    of the N=5 target, not a full drop), and item #2 was never invoked
    (all 9 canonical models completed). Every one of PROJECT_BRIEF's RQs
    is preserved regardless, per §8's design constraint on the cut order.
- **Instantiation count reduced 5 -> 4 (2026-07-15):** invokes gate cut-priority item
  #4 ("the fifth dynamic instantiation") from §8. Pre-registered before this
  decision, not a post-hoc rationalization. Driven by real cost data collected during
  the Comparison-A backfill: completing the full 5-instantiation matrix across
  Sonnet/Haiku/Gemini/GPT was projected at ~$82.56 in further API spend vs ~$63.17 for
  N=4 (`scripts/estimate_cost.py --target-instantiations` reproduces this). Stability evidence
  available at decision time (mean pairwise Kendall tau approx 0.84 across partial
  data, ~61/180 cells) showed high cross-instantiation agreement, suggesting the 5th
  instantiation would mostly sharpen precision on a clear signal, not
  change the qualitative stability conclusion. That figure moved as more data landed:
  down to 0.593 at ~104/180 cells, then up to 0.746 once N=4 was fully closed for
  Sonnet/Haiku/Qwen (all sizes) and partially for Gemini Pro Preview. A reminder that
  early-partial-data stability reads are noisy and shouldn't be over-trusted. The
  qualitative conclusion (high stability) held throughout, but the point estimate did
  not. Full results and interpretation: `analysis/STABILITY.md`. Reduces StableMut@K's
  pairwise-tau comparisons from 10 (N=5) to 6 (N=4). SD/CI on the 6-pair mean is
  reported in that file, not just the point estimate. $3.63 in real
  money (Sonnet $2.55 + Haiku $1.09, instantiation 5) falls outside the
  N=4 scope as a result, not discarded (still valid, usable data), just not part of
  the headline analysis. Available as supplementary evidence if useful later.
- **Gemini model substitution (2026-07-14):** Gemini 2.5 Pro/Flash retired ("no longer
  available to new users": 404 on live `generate_content` despite still listing as
  Stable in `models.list()`) before any run completed against them. Replaced with
  Gemini 3.1 Pro Preview (frontier) + Gemini 3.1 Flash-Lite (efficient). Same
  generation for both (keeps the frontier-vs-efficient contrast in RQ4.2/4.4
  uncounfounded by a generation gap). Flash-Lite is GA/stable. No non-preview
  Pro-class Gemini model exists currently. 3.1 Pro Preview carries
  preview-track deprecation risk that the original 2.5 Pro did not. Note this as a
  limitation in the write-up.
  **The 404s hit before Google's stated retirement date** (an October
  timeline per Google's deprecation notice). The forced substitution above
  was not optional/early-adopted. The originally-specified models stopped
  answering API calls months ahead of their documented retirement
  schedule. Worth stating plainly as a limitation, not as this
  project choosing to move off 2.5 Pro/Flash early. **Model-ID consistency
  re-verified 2026-07-26**: Dynamic and ULT/PLT core_400 result
  rows use identical `gemini-3.1-pro-preview`/`gemini-3.1-flash-lite`
  strings, no drift. Still no non-preview Pro-class endpoint available as of
  this check. `src/pricing.py`'s note from 2026-07-14 stands unchanged (no
  newer live `models.list()` check was run. That would be a reviewed API call,
  not done speculatively).
- **Supervisor meeting outcomes (2026-07-25):**
  - **Corpus sign-off received.** P2 gate (60 templates pass validation, supervisor
    sign-off on corpus) is now fully closed.
  - **Two-experiment framing APPROVED**, resolving the ambiguity that previously
    blocked evaluating fine-tuned checkpoints on ULT/PLT:
    (a) the six existing Dynamic-trained LoRA runs (`data/results/finetune_rebuild/`,
    the `inst1`/`bp_own`/`bp_gpt5` x Qwen-1.5B/7B conditions) are recharacterised as a
    **supplementary memorisation-stability study**, not Comparison C. Their
    seen-vs-unseen (inst1-train-split vs inst2/3-held-out) gap is the relevant
    readout for that study (`analysis/FINETUNE_ENDPOINT_PROVENANCE.md`).
    (b) the **canonical Comparison C** is a **new** LoRA fine-tune of Qwen-1.5B on
    **ULT** (not Dynamic), evaluated pre/post on ULT, PLT, and Dynamic for the 2x3
    DiD table specified in §7/§3.1 (H2). This is the experiment §11's roadmap
    always intended. The six existing runs answer a different, useful question
    (does fine-tuning on prior Dynamic output inflate scores?) but were
    never a substitute for it.
  - **Gate lifted:** the previous "do NOT evaluate fine-tuned checkpoints on
    ULT/PLT" instruction (a scope guard from when Comparison C's design was still
    the six Dynamic-trained runs) is **lifted for the new canonical
    Comparison C experiment** in (b) above. Evaluating those checkpoints on
    ULT/PLT is now the explicit point, not an accidental scope violation.
  - **Equivalent-mutant validation** (§5.5: 30 mutants/tier hand-inspected, 120
    total) is tracked as a **P4-gate item**: it produces the validated Mut@K
    variant that feeds the Comparison-A table (raw score is the standard/pessimistic
    headline. Validated score is the sample-corrected companion figure). Recorded
    here to resolve a checklist-mapping gap an earlier diversity/equivalent-mutant
    audit flagged (validation work existed but wasn't tied to a named gate).
- **Comparison C: COMPLETE, both studies (2026-07-27):**
  - **Supplementary memorisation-stability study** (six Dynamic-trained LoRA runs,
    Qwen-1.5B/7B x inst1/bp_own/bp_gpt5): epoch curves + endpoint table done
    (`analysis/FINETUNE_ENDPOINT_PROVENANCE.md`). Largest seen/unseen gap: `bp_gpt5`
    Qwen-1.5B, 52.7pp greedy.
  - **Canonical Comparison C** (new Qwen-1.5B-on-ULT LoRA, §7/§3.1 H2): fine-tune
    (SLURM job 9488214, 30 epochs) → POST eval on ULT/PLT/Dynamic core_400 (Stage
    3a/3b) → aggregate 2x3 DiD + seen/unseen-stratified gradient + 5-epoch onset
    curve (Stage 3c), all with bootstrap CIs. Headline: seen-ULT +99.1pp (100%
    baseline-pass, 100% verbatim-match, n_problems=112). PLT +13.8pp DiD (CI [7.7,20.1])
    after subtracting a real +8.7pp generic-fine-tuning-improvement control.
    unseen-ULT a borderline +6.9pp (CI [1.3,13.0]): most of its raw gain is that
    same generic effect, not ULT-specific transfer, and even that residual is
    measured on a population a third of which (98/288) has code that cannot
    execute regardless of test quality. Dynamic-L4 is exactly 0.0pp both
    pre/post, floor-limited (this 1.5B model never clears the CC>=8 baseline
    gate), not a real null. The added Dynamic-L1-L3 arm is the informative
    control. One deviation from the pre-registered monotone-decay prediction
    (PLT's gain exceeds unseen-ULT's), explained by a selection-effect audit:
    unseen-ULT is 100% composed of ULT problems the repair pipeline could not
    verify (STRUCTURAL/SHAPE_NOT_REPAIRABLE/unparseable-test-syntax), while PLT
    core_400 was never screened by any test-quality criterion. Full writeup:
    `analysis/COMPARISON_C_INTERPRETATION.md` (hand-written) +
    `analysis/COMPARISON_C_PROVENANCE.md` (regenerable raw tables) +
    `analysis/COMPARISON_C_ANALYSIS_PLAN.md` (pre-registration + amendment).
  - **Remaining open items going into Phase 6:** (a) equivalent-mutant validation:
    120 hand-inspected mutants, the user's work in progress, feeds the
    validated Mut@K variant in Comparison A (P4-gate item above); (b) the GPT-5/
    GPT-5-mini lane (Dynamic backfill + ULT/PLT core_400 batch, ~$37.68):
    supervisor/funding-gated, unchanged; (c) the Gemini 3.1 Pro Preview Dynamic
    crawl: blocked on a 250-requests/day quota, ~545/1200 problems in; (d) the
    dissertation write-up.
- **RQ5/H6 cross-benchmark validity (2026-07-27, supervisor's "bottom-up"
  construct-validity ask):** pre-registered `analysis/RQ5_ANALYSIS_PLAN.md`
  before computing anything. Zero-compute result: Dynamic(pooled)↔ULT rank
  agreement is close to zero at n_models=7 (Kendall τ=0.143), despite a
  strong-looking Pearson r=0.904 driven entirely by one outlier model
  (Qwen 1.5B): read as "distinct capabilities," not "redundant," per the
  pre-registered frame, and reported as found even though it's the weaker
  of the two possible readings. Diagnosed further (`analysis/
  RQ5_DIAGNOSTICS.md`, 2026-07-27/28): decomposing the near-total recovery
  from a coverage-adjusted re-scoring (τ=0.905) shows the agreement is
  almost entirely about *executability* (baseline-pass rate alone: τ=0.810)
  and not about mutation-kill quality conditional on passing (τ=0.143,
  identical to the raw primary). A precise scoping finding, not a reversal
  of the headline result.
  Leaderboard harvest found published, snapshot-verified BigCodeBench
  numbers (both Complete and Hard splits) for all 3 Qwen sizes and **none**
  of the six API models. Gemini 3.1 Pro Preview/Flash-Lite included,
  correctly not proxied by a different Gemini version's score. This made
  the planned Qwen self-run unnecessary, but left the Dynamic/ULT↔
  BigCodeBench correlation at n_models=3, all one model family (a "perfect" τ=1.0
  that is really a scale-monotonicity result, not independent validity
  evidence. Permutation p=0.331 confirms it isn't significant at this n_models).
  **Cross-family extension approved 2026-07-28, completed 2026-07-29**
  (post-hoc addition, not in the original pre-registration,
  `analysis/RQ5_ANALYSIS_PLAN.md`'s addendum): 4 non-Qwen models
  (DeepSeek-Coder-6.7B, CodeLlama-13B, StarCoder2-15B, Mistral-7B-v0.3),
  full Dynamic+ULT runs. Result: the n_models=3 "perfect" BigCodeBench correlation
  **collapses** once real family diversity is added (τ 1.000→0.429, raw
  Mut@K, no longer significant), confirming it was the size-scaling
  artifact suspected above, while the coverage-adjusted score's
  correlation **survives** the same test (τ 1.000→0.905, n_models=7, p=0.0034),
  now independent external cross-family evidence for the executability
  finding, not just an internal one. StarCoder2 required a harness
  accommodation (`supports_system_role: false`: its chat_template rejects
  `role="system"` outright) logged per-row as `prompt_delivery_mode`.
  Full write-up incl. Discussion-chapter stub and the cross-family final
  results: `analysis/RQ5_INTERPRETATION.md`. One-command regeneration for
  all of the above plus Comparison A/B/C and stability:
  `scripts/build_thesis_assets.py`.
- **Hypothesis reconciliation (2026-08-12)**: `docs/Approved_Hypotheses.md`
  and `docs/Research_questions.xlsx` (both supervisor-facing reference
  artifacts) entered the repo and were reconciled against this project's
  executed analysis (`analysis/HYPOTHESIS_DEVIATIONS.md`,
  `analysis/HYPOTHESIS_COVERAGE_AUDIT.md`, `analysis/
  WORKBOOK_VERIFICATION.md`). **The approved set is exactly six
  hypotheses (H1-H6), where H1 carries two tests (Comparison A;
  Comparison B/ULT-vs-PLT) and H5 covers the whole of RQ4.** This is the
  only set the write-up reports. **A later expanded draft (H4a, H4b, and
  separate hypotheses for RQ4.2/4.3/4.4) was drafted at some earlier point
  in this project's working documents but was never submitted to or
  approved by the supervisor.** It creates no obligation and does not
  appear in the paper. Recorded here for the audit trail only, per
  `docs/Research_questions.xlsx`'s Hypotheses-sheet governance note.
  Also corrected this pass: Comparison B (ULT vs PLT) had been treated in
  several `analysis/` docs as an informal, unofficial exploratory check,
  excluded from RQ1's Holm-Bonferroni family. `docs/
  Approved_Hypotheses.md` names it verbatim as H1's second test. RQ1's
  family is now the two-test family it always should have been.
- **Experimental freeze declared 2026-08-12.** Data collection for the
  main study is closed. The write-up phase (§8's final gated phase)
  proceeds on the data as it stood at this date, not as a moving target.
  Coverage at freeze (`scripts/coverage_matrix.py`, live, zero active or
  pending SLURM jobs at the time of the check): **172 of 180
  model×tier×instantiation cells complete (95.6%)**. Every lane
  (RUNNABLE NOW BY US and SUPERVISOR-GATED) reports zero gaps except the
  one below. The sole remaining gap, both Gemini models' 5th
  instantiation (600 problems, 8 cells), was quantified at **$9.60**
  (Gemini Pro Preview $9.34, Flash-Lite $0.27,
  `scripts/estimate_cost.py --target-instantiations 5`) with a 4-5 hour to
  2-day completion window, and **declined** the same day: H5's THRESHOLD
  NOT MET verdict is unchanged at any plausible resulting τ, and the
  noise-floor mechanism (`analysis/RQ5_DIAGNOSTICS.md` sec 2b: several
  canonical models cluster within a pooled spread smaller than their
  between-instantiation SDs) predicts more data would move τ further
  down, not up, repeating the pattern observed when τ fell from
  0.667 to 0.583 as Gemini Pro Preview's L4 data landed. Full decision
  record: `analysis/OPEN_ITEMS.md`, `analysis/HYPOTHESIS_DEVIATIONS.md`'s
  H5 entry. A permanent backup of adapters, results, batches, manifests,
  and `analysis/` as they stood at freeze is recorded in `CLAUDE.md`'s
  hard rules, path `/users/40492566/dissertation_backups/20260812_preflight`.
  No further Dynamic/ULT/PLT data collection is expected before
  submission. Any exception to this freeze must update this entry.
  Resuming collection without updating it is not acceptable.

---

## 12. Glossary

- **CC**: cyclomatic complexity (McCabe): 1 + number of decision points.
- **SAC / SPC**: semantic-altering / semantic-preserving mutation changes.
- **ULT / PLT**: UnLeakedTestBench (decontaminated) / its leaked twin.
- **K**: attempts/problem, Pass@K-style (§5.4). Every run in this project used K=1. A K=5 sensitivity sweep was cut (§8) and never run. Not to be confused with **m** below.
- **m**: instances/template (§5.2), a different quantity from K that this brief previously also called "K". m=5 throughout.
- **Mut@K, Exec@K, Cov-S@K, Cov-B@K**: the four metrics. **StableMut@K** = mean Mut@K over the instantiations (4 executed, 5 was the design target).
- **Instantiation**: one full generator run (60 templates × m=5 = 300 problems).
- **DiD**: difference-in-differences (the causal estimator for Comparison C).
- **LoRA / QLoRA**: parameter-efficient fine-tuning (frozen base + trained adapters / quantised variant).
