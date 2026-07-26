# Project Brief — Memorisation-Robust Benchmarking of LLM Test Generation

> Canonical, distilled reference for this dissertation. Keep this in the repo root
> alongside `README.md` and `CLAUDE.md`. `README.md`/`CLAUDE.md` own the *operational*
> details (how to run things, environment, current state); this file owns the *plan*
> (what the project is, what it must deliver, and in what order). When code and this
> brief disagree, treat the code + `CLAUDE.md` as ground truth for *state* and this
> brief as ground truth for *intent*.

- **Full title:** Memorisation-Robust Benchmarking of LLM Test Generation: A Dynamic, Template-Based Benchmark with Complexity-Tiered Mutation Analysis
- **Student:** Yohan Sneider Sanchez Vega (40492566) · **Supervisor:** Pinzhen Chen
- **Module:** ECS8056 MSc AI Themed Research Project (25/26)

---

## 1. The one-paragraph thesis

Static benchmarks for LLM test generation get contaminated the moment they are
published: the act of evaluating models leaks benchmark content into training corpora
(directly, and indirectly via RLHF and web-scraped interaction data). This project
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

- **RQ1** — How much does dynamic, template-based generation reduce contamination-induced score inflation vs a static SOTA benchmark (ULT)?
- **RQ2** — How does generated-test effectiveness (mutation score) vary across the four CC tiers (L1–L4)?
- **RQ3** — Are static benchmarks more prone to *overestimating* performance at *lower* tiers than higher ones, vs the dynamic benchmark?
- **RQ4.1** — *Stability.* Are LLM rankings stable across multiple independent instantiations (is the protocol a reliable instrument)?
- **RQ4.2** — *Within-family scaling (closed-source).* Frontier-vs-efficient mutation-score gap per provider, dynamic vs ULT. Three providers → triangulated answer.
- **RQ4.3** — *Within-family scaling (open-source).* Same on the Qwen 32B/7B/1.5B sweep (3 points); compare curve shape against closed-source pairs.
- **RQ4.4** — *Provider effect at matched tier.* Compare the three frontier slots (and the three efficient slots) at fixed tier — is any provider more contamination-susceptible?
- **RQ5** — How well does dynamic-benchmark test-gen performance correlate with code-gen performance on a proxy benchmark (BigCodeBench), and does the correlation differ dynamic vs static?

## 3.1 Hypotheses → statistical test (Layer-2 inferential)

| RQ | Hypothesis | Test |
|----|-----------|------|
| RQ1 | H1 (observational) | Paired Wilcoxon signed-rank, dynamic vs ULT mutation score at model–problem level |
| RQ1 | H2 (causal) | Difference-in-differences on the 2×3 design (pre/post fine-tune × ULT/PLT/Dynamic) |
| RQ2 | H3 | Spearman ρ between tier index and mutation score, per model and pooled |
| RQ3 | H4 | Tier × benchmark interaction term in a mixed-effects regression (model as random effect) |
| RQ4 | H5 | Pairwise Kendall τ between rankings across instantiations |
| RQ5 | H6 | Pearson r + Spearman ρ between mutation score and proxy Pass@1 |

Corrections: Holm–Bonferroni **within each RQ family**. Effect sizes with CIs are primary; p-values support.

---

## 4. Scope

**In scope:** Python only · function-level test generation · 4 CC tiers (L1–L4) with
secondary descriptors (AST depth, edge-case count) · **60 templates (15/tier), K=5
instances/template/instantiation → 300 problems/instantiation** · **5 instantiations**
(design target) **for stability, executed as 4** per the pre-registered gate
cut-priority — see §11 for the cost/stability rationale · 7 SAC mutation operators ·
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
(reference implementation) + docstring template. Each template yields K instances by
sampling its parameter domain; variable names, values, constants, and docstring synonyms
vary across instances. Instances are validated post-hoc: CC must stay in-band, and the
oracle must pass a lightweight property-based smoke test. A **benchmark instantiation**
= one full generator run (60 templates × K=5).

### 5.3 Mutation operators — SAC only (headline)
Arithmetic Operator Replacement (**AOR**), Relational Operator Replacement (**ROR**),
Logical Operator Replacement (**LOR**), Constant Replacement (**CR**), Boundary Mutation
(**BM**), Statement Deletion (**SDL**), Return/Statement Mutation (**RSM**). Single-edit
per mutant; cap **30 mutants/instance** (sample if more). SPC operators are future work.

### 5.4 Metrics (Pass@K-style naming, K = attempts/problem)
| Metric | Symbol | Meaning | Level |
|--------|--------|---------|-------|
| Executability | Exec@K | Fraction of suites that import/run without raising at collection | **Gate** (>0 to score the rest) |
| Statement coverage | Cov-S@K | Mean line coverage over executable suites | Secondary |
| Branch coverage | Cov-B@K | Mean branch coverage over executable suites | Secondary |
| Mutation score | Mut@K | Killed / total mutants (raw); validated variant divides by total − est. equivalent | **Headline** |
| Stability | StableMut@K | Mean Mut@K across the instantiations (4 executed; 5 design target — see §11), SD reported | Stability |

Headline K=1; sensitivity sweep at K=5. Temperature fixed **0.2** (ULT convention),
max output 2048 tokens, deterministic seeding where the API exposes it.

### 5.5 Equivalent mutants
Default = raw score (pessimistic, comparable). Validation = 30 mutants/tier hand-inspected
(120 total); report a sample-validated score + estimated equivalent-mutant rate with CIs.

---

## 6. The 9 models (subjects under test)

| Provider | Frontier | Efficient |
|----------|----------|-----------|
| OpenAI | GPT-5.4 | GPT-5.4 mini |
| Anthropic | Claude Sonnet 4.6 | Claude Haiku 4.5 |
| Google | Gemini 3.1 Pro Preview | Gemini 3.1 Flash-Lite |
| Open-source (Qwen2.5-Coder) | 32B · 7B · 1.5B (three-point sweep) | — |

Google row is a forced substitution for the originally-specified Gemini 2.5
Pro/Flash — see Sec 11 for the retirement/substitution history. Model-ID
consistency check (2026-07-26): every Dynamic-benchmark and ULT/PLT
core_400 result row's `model`/`model_revision` fields read exactly
`gemini-3.1-pro-preview` / `gemini-3.1-flash-lite` with no drift between the
two result sets (checked directly against `data/results/dynamic/`,
`data/results/ult/`, `data/results/plt/`).

---

## 7. The three comparisons (contamination evidence)

- **Comparison A — Dynamic vs ULT** (Phase 4). Headline effectiveness numbers; the main-study table.
- **Comparison B — ULT vs PLT** (Phase 5, observational). PLT = leaked twin of ULT; expect PLT scores systematically higher at matched CC → the observational contamination signal.
- **Comparison C — Small-LLM fine-tuning** (Phase 5, causal). Fine-tune Qwen-1.5B on ULT (LoRA/QLoRA), re-evaluate on ULT / PLT / a fresh Dynamic instantiation. Expected pattern: large gain on ULT, possibly larger on PLT, **near-zero gain on Dynamic** — the contamination-resistance evidence. 2×3 difference-in-differences table.

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
**Cut #4 invoked 2026-07-15** — see §11 for the cost/stability rationale.

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

## 10. Environment (summary — see `CLAUDE.md` for specifics)

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
- **Work completed to date:** _(fill in — link files/results)_
- **In flight / blocked:** _(fill in)_
- **Note on OpenAI runs:** originally the supervisor generated L3/L4 outputs (he held
  the OpenAI credits; results arrived as JSONL + `.error` files for ingestion). As of
  2026-07-14 the supervisor is out of credits — GPT batches now run under the
  student's own OpenAI account instead (same `scripts/create_batch.py` path, batch
  discount still applies since that's a property of the Batch API, not whose account
  funds it). GPT-5/gpt-5-mini backfill deliberately held back from this account until
  separately funded — see the N=4 entry below for what's running now (Anthropic +
  Gemini only).
- **Instantiation count reduced 5 -> 4 (2026-07-15):** invokes gate cut-priority item
  #4 ("the fifth dynamic instantiation") from §8 — pre-registered before this
  decision, not a post-hoc rationalization. Driven by real cost data collected during
  the Comparison-A backfill: completing the full 5-instantiation matrix across
  Sonnet/Haiku/Gemini/GPT was projected at ~$82.56 in further API spend vs ~$63.17 for
  N=4 (see `scripts/estimate_cost.py --target-instantiations`). Stability evidence
  available at decision time (mean pairwise Kendall tau approx 0.84 across partial
  data, ~61/180 cells) showed high cross-instantiation agreement, suggesting the 5th
  instantiation would mostly sharpen precision on an already-clear signal rather than
  change the qualitative stability conclusion. That figure moved as more data landed
  — down to 0.593 at ~104/180 cells, then up to 0.746 once N=4 was fully closed for
  Sonnet/Haiku/Qwen (all sizes) and partially for Gemini Pro Preview — a reminder that
  early-partial-data stability reads are noisy and shouldn't be over-trusted; the
  qualitative conclusion (high stability) held throughout, but the point estimate did
  not. Full results and interpretation: `analysis/STABILITY.md`. Reduces StableMut@K's
  pairwise-tau comparisons from 10 (N=5) to 6 (N=4) — SD/CI on the 6-pair mean is
  reported in that file, not just the point estimate. $3.63 of already-spent real
  money (Sonnet $2.55 + Haiku $1.09, instantiation 5 specifically) falls outside the
  N=4 scope as a result — not discarded (still valid, usable data), just not part of
  the headline analysis; available as supplementary evidence if useful later.
- **Gemini model substitution (2026-07-14):** Gemini 2.5 Pro/Flash retired ("no longer
  available to new users" — 404 on live `generate_content` despite still listing as
  Stable in `models.list()`) before any run completed against them. Replaced with
  Gemini 3.1 Pro Preview (frontier) + Gemini 3.1 Flash-Lite (efficient) — same
  generation for both (keeps the frontier-vs-efficient contrast in RQ4.2/4.4
  uncounfounded by a generation gap), Flash-Lite is GA/stable. No non-preview
  Pro-class Gemini model exists at all currently — 3.1 Pro Preview carries genuine
  preview-track deprecation risk that the original 2.5 Pro did not; note this as a
  limitation in the write-up.
  **The 404s hit before Google's own stated retirement date** (an October
  timeline per Google's deprecation notice) — the forced substitution above
  was not optional/early-adopted, the originally-specified models stopped
  answering API calls months ahead of their own documented retirement
  schedule; worth stating plainly as a limitation rather than implying this
  project chose to move off 2.5 Pro/Flash early. **Model-ID consistency
  re-verified 2026-07-26** (see Sec 6): Dynamic and ULT/PLT core_400 result
  rows use identical `gemini-3.1-pro-preview`/`gemini-3.1-flash-lite`
  strings, no drift; still no non-preview Pro-class endpoint available as of
  this check, `src/pricing.py`'s note from 2026-07-14 stands unchanged (no
  newer live `models.list()` check was run — would be a reviewed API call,
  not done speculatively).
- **Supervisor meeting outcomes (2026-07-25):**
  - **Corpus sign-off received.** P2 gate (60 templates pass validation, supervisor
    sign-off on corpus — §8) is now fully closed.
  - **Two-experiment framing APPROVED**, resolving the ambiguity that previously
    blocked evaluating fine-tuned checkpoints on ULT/PLT:
    (a) the six existing Dynamic-trained LoRA runs (`data/results/finetune_rebuild/`,
    the `inst1`/`bp_own`/`bp_gpt5` x Qwen-1.5B/7B conditions) are recharacterised as a
    **supplementary memorisation-stability study** — not Comparison C. Their
    seen-vs-unseen (inst1-train-split vs inst2/3-held-out) gap is the relevant
    readout for that study (see `analysis/FINETUNE_ENDPOINT_PROVENANCE.md`).
    (b) the **canonical Comparison C** is a **new** LoRA fine-tune of Qwen-1.5B on
    **ULT** (not Dynamic), evaluated pre/post on ULT, PLT, and Dynamic for the 2x3
    DiD table specified in §7/§3.1 (H2). This is the experiment §11's roadmap
    always intended; the six existing runs answer a different, useful question
    (does fine-tuning on one's own prior Dynamic output inflate scores?) but were
    never a substitute for it.
  - **Gate lifted:** the previous "do NOT evaluate fine-tuned checkpoints on
    ULT/PLT" instruction (a scope guard from when Comparison C's design was still
    the six Dynamic-trained runs) is **lifted specifically for the new canonical
    Comparison C experiment** in (b) above — evaluating those checkpoints on
    ULT/PLT is now the explicit point, not an accidental scope violation.
  - **Equivalent-mutant validation** (§5.5: 30 mutants/tier hand-inspected, 120
    total) is tracked as a **P4-gate item** — it produces the validated Mut@K
    variant that feeds the Comparison-A table (raw score is the default/pessimistic
    headline; validated score is the sample-corrected companion figure). Recorded
    here to resolve a checklist-mapping gap an earlier diversity/equivalent-mutant
    audit flagged (validation work existed but wasn't tied to a named gate).

---

## 12. Glossary

- **CC** — cyclomatic complexity (McCabe): 1 + number of decision points.
- **SAC / SPC** — semantic-altering / semantic-preserving mutation changes.
- **ULT / PLT** — UnLeakedTestBench (decontaminated) / its leaked twin.
- **Mut@K, Exec@K, Cov-S@K, Cov-B@K** — the four metrics; **StableMut@K** = mean Mut@K over the instantiations (4 executed; 5 was the design target — see §11).
- **Instantiation** — one full generator run (60 templates × K=5 = 300 problems).
- **DiD** — difference-in-differences (the causal estimator for Comparison C).
- **LoRA / QLoRA** — parameter-efficient fine-tuning (frozen base + trained adapters / quantised variant).
