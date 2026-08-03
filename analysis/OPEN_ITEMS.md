# Open items register — pre-submission checklist

Every known unresolved item in this project in one place, each tagged
**BLOCKING-FOR-SUBMISSION** (must be resolved, or explicitly accepted as a
limitation in the write-up, before submitting), **DISCLOSE-AND-PROCEED**
(a real, already-investigated issue that doesn't need further action —
its caveat just needs to travel with whatever result it touches), or
**FUTURE-WORK** (out of scope for this submission by design or by
explicit prior decision). Re-check this file's own age against the
current date before treating any item's status as current — several have
already moved once (e.g. the pytest crash and validator sweep below were
open when this file was drafted and are now closed within the same
session).

## BLOCKING-FOR-SUBMISSION

| Item | What's needed | Owner | Notes |
|---|---|---|---|
| **Equivalent-mutant validation** (120 hand-inspected mutants, 30/tier) | Finish the hand-inspection pack (`scripts/build_equiv_mutant_sample.py` already builds the sample; the inspection itself is manual) and compute the validated Mut@K variant (raw score minus estimated equivalent-mutant rate, with CIs) that PROJECT_BRIEF.md §5.5/§5.4 commits to reporting alongside the raw headline score. | User (explicitly "my ... inspection" per the close-out prompt — this is manual work, not something to automate) | Tracked as a P4-gate item since 2026-07-25 (PROJECT_BRIEF.md §11); still open as of this register. Without it, Comparison A's "validated Mut@K variant" companion figure (committed to in §5.4/§5.5) is missing. |
| **The dissertation write-up itself** | Phase 6 (§8, weeks 14-16): six hypothesis tests written up, figures/tables finalised, full draft, submission. | User | Everything else in this register feeds into this; listed for completeness, not because it's a surprise. |
| **Supervisor review of `analysis/ULT_DATA_QUALITY_AUDIT.md`** | The three consolidated ULT/PLT data-quality findings (ground-truth pass rate 8.4%, self-reported CC unreliability, the metric-definition contradiction) are checkable from this project's own scripts/data, but are findings about a *third party's* published artifact — flagged for supervisor sign-off before any external use (an email to the ULT authors, a related-work paragraph that names the specific numbers, anything leaving this repository). | Supervisor (Pinzhen Chen) | **Not blocking for internal dissertation use** with the findings presented as this project's own measurements (already the case throughout `analysis/`) — blocking specifically for anything that presents them as settled claims to an external audience. |

## DISCLOSE-AND-PROCEED

| Item | Current disclosure | Why it doesn't block |
|---|---|---|
| **Comparison A supports no directional claim at current n** (raw +0.20 / thin-filtered -1.00 / definition-matched -0.60) | `analysis/COMPARISON_A_INTERPRETATION.md` (headline), `analysis/COMPARISON_PROVENANCE.md`, `analysis/RQ5_CROSS_DEFINITION_AUDIT.md` §5 | This is the honest finding, not a gap to close — reported as a genuine null with what-would-resolve-it stated explicitly (`COMPARISON_A_INTERPRETATION.md`'s own section). More data (below) would help but isn't required to submit an honest null result. |
| **Mutant-count spec deviation** (30-mutant cap/stratified sampler never implemented; brief's own §5.1/§5.3 internally inconsistent for L4) | `analysis/MUTANT_COUNT_SPEC_AUDIT.md`, `PROJECT_BRIEF.md` §5.3 (amended 2026-08-04) | Amend-and-disclose was the explicit recommendation over retro-capping and rescoring (§(e) of the audit) — checked directly that no reported conclusion depends on the macro/micro choice this deviation raises. Action already taken; no further work needed unless a future decision explicitly overrides the recommendation. |
| **Gemini 3.1 Pro Preview's Dynamic-L4 gap** (0 rows at L4; 545/1200 total Dynamic problems in) | `analysis/METRICS_AND_FINDINGS_EXPLAINED.md`'s "Gemini-Pro-has-no-L4" section (traced through every table it touches) | Quota-blocked (250 requests/day), not a bug — fully disclosed everywhere this model's pooled-Dynamic score could otherwise mislead. More data would strengthen Comparison A (see `COMPARISON_A_INTERPRETATION.md`'s "what would be needed" section) but the current gap is not silently affecting any reported number. |
| **GPT-5 / GPT-5-mini ULT/PLT lane** (2 batches prepared, unsubmitted — ~$37.68, supervisor/funding-gated per PROJECT_BRIEF.md §11) | `analysis/SUPERVISOR_HANDOFF_ULT_PLT_20260713.md`; every table missing these two models states so explicitly (`analysis/METRICS_AND_FINDINGS_EXPLAINED.md` §3) | Funding decision, not this project's to resolve unilaterally. Comparison A/B's model counts (5/9, 7/9) are disclosed as incomplete-not-zero-filled everywhere they're reported. |
| **2 of 7 cross-family BigCodeBench correlation points are individually thin-cell** (CodeLlama-13B: ULT n_defined=8; Mistral-7B: Dynamic n_defined=5, ULT n_defined=1) | `analysis/METRICS_AND_FINDINGS_EXPLAINED.md` §3's table, §5's "would need more data" list | The n=7 correlation itself is genuine; the caveat that 2 of its inputs are shaky travels with every citation of that number already. |
| **StarCoder2's non-identical prompt delivery** (`supports_system_role: false`, system instruction folded into first user turn) | `analysis/RQ5_INTERPRETATION.md`'s cross-family limitations section | Disclosed at the point the accommodation was made; instruction text is identical, only delivery differs. |
| **Chat-template drift for 2 of 4 cross-family models** (CodeLlama-13B, Mistral-7B-v0.3 — template postdates their own published BigCodeBench eval date) | `analysis/RQ5_INTERPRETATION.md`'s cross-family limitations section | Disclosed with exact dates and reasoning at the point the cross-family extension was approved. |
| **Comparison C's monotone-decay deviation** (PLT's raw gain exceeds unseen-ULT's) | `analysis/COMPARISON_C_INTERPRETATION.md`'s selection-effect audit | Investigated, not just noted — traced to a genuine population-comparability difference, not left as an unexplained anomaly. |

## FUTURE-WORK

| Item | Why it's out of scope now |
|---|---|
| **Retro-capping mutants to 30 and rescoring** | Explicitly assessed and rejected as disproportionate for the payoff (`analysis/MUTANT_COUNT_SPEC_AUDIT.md` §(e)) — would require re-running the mutation-testing harness over the large majority of every already-scored row, for a change already shown not to affect any reported qualitative conclusion. Revisit only if a future reviewer specifically requires it. |
| **Micro/pooled Mut@K as a formal third co-primary** | Computed and reported as a diagnostic in `RQ5_CROSS_DEFINITION_AUDIT.md` §3a and `MUTANT_COUNT_SPEC_AUDIT.md` §(d), not adopted as a reported co-primary (weaker textual/structural support than the macro reading — see the cited reasoning). Could be formalised further if a future reviewer wants it. |
| **Cross-checking the 8.4% ULT ground-truth figure against ULT's own evaluation environment** | This project's own harness produced the figure; verifying it reproduces under ULT's own repo/environment is analysis work this project hasn't done (`analysis/METRICS_AND_FINDINGS_EXPLAINED.md` §5). |
| **`analysis/` folder reorganisation by RQ** | Raised once mid-project ("create folders for each RQ in analysis/"), investigation started (surveyed 70 files, found real taxonomy ambiguities against PROJECT_BRIEF.md's RQ1-RQ5/RQ4.1-4.4 structure), never resumed after a tooling interruption redirected to other work. Purely organisational, no effect on any result — revisit only if explicitly requested again. |
| SPC (semantic-preserving) operators, a second language, PBT-with-coverage rigor gate, DyCodeEval-style multi-agent context generation, continuous benchmark maintenance | Already named as future work in PROJECT_BRIEF.md §4 — listed here only for completeness, not new information. |

## Recently closed (during this close-out pass, 2026-08-04 — kept here briefly for continuity, safe to prune once this file is next revisited)

- **Pytest collection crash on bare `pytest -q`** (`template_corpus/templates/_smoke/test_grammar.py`'s top-level `sys.exit()`) — fixed by renaming to `grammar_selfcheck.py` and adding `testpaths = ["tests"]` to `pyproject.toml` as a second, independent layer.
- **Validator sweep** (13 scripts audited) — 1 new live bug fixed (`archive_diversity_audit.py`'s hardcoded README summary, error ledger bug #9), 1 already-known bug's still-live fallback code path fixed (`diversity_v2.py`'s silent sacrebleu-to-Jaccard fallback), 1 latent risk hardened pre-emptively (`residual_scan.py`). Full report: `analysis/VALIDATOR_SWEEP.md`. Shared guard module added (`validation_helpers.py`); new CLAUDE.md rule ("library fallbacks must raise, not approximate").
- **Comparison A interpretation** — rewritten as a declared null (`analysis/COMPARISON_A_INTERPRETATION.md`), cross-referenced from `COMPARISON_PROVENANCE.md`.
- **PROJECT_BRIEF.md reconciliation** — H1's unit corrected (model-problem → model level), Mut@K's conditional/unconditional distinction disclosed, `coverage_adjusted` added to §5.4, mutant-count deviation added to §5.3, equivalent-mutant note added to §5.5.
