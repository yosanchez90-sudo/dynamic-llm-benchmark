# analysis/ — document index

107 files directly in `analysis/` (53 `.md`, 47 `.csv`, 6 `.py`, 1 `.xlsx`),
plus five subdirectories (`derived/`, `diversity/`, `equiv_mutants/`,
`reports/`, `figures/`) holding another 50. Grouped below by role.

**`analysis/README.md` is not this index** — it's a specific contamination
notice about six fine-tuning result files (see [Preserved historical
record](#preserved-historical-record-24-docs) below). This file
(`analysis/INDEX.md`) is the general index; it lives at a different path so
that the 13 existing references to `analysis/README.md`'s contamination
content elsewhere in the codebase don't break.

## Hand-written interpretation (11 docs)

Prose analysis of a research question, hypothesis, or finding.

| Document | Description |
|---|---|
| `COMPARISON_A_INTERPRETATION.md` | Interpretation of Dynamic-L4 vs ULT (H1 Test 1): rank-agreement reading, outlier discussion. |
| `COMPARISON_C_ANALYSIS_PLAN.md` | Pre-registered plan for the contamination difference-in-differences design (seen/unseen split, estimand). |
| `COMPARISON_C_INTERPRETATION.md` | Interpretation of the seen/unseen/PLT/Dynamic contamination gradient result. |
| `FINETUNE_ENDPOINT_PROVENANCE.md` | Methodology and headline verdict for the epoch-30 endpoint table. Despite the "PROVENANCE" name, this is hand-written interpretation, not auto-generated — it has no `Generated:`/`Git commit:` header, and the real auto-generated sidecar (`finetune_endpoint_table_PROVENANCE.md`, below) explicitly calls this file out as "not touched by this script." |
| `H3_ANALYSIS_PLAN.md` | Pre-registered plan for the tier-vs-mutation-score gradient test (RQ2). |
| `H3_INTERPRETATION.md` | Interpretation of the 9-model tier-gradient result (H3/RQ2). |
| `H4_DESIGN_MEMO.md` | Three-option design memo for RQ3/H4, ending in a decision to leave it untested. Dual-natured — also functions as the preserved record of that decision (see historical record below); filed here since it's primarily reasoning, not an incident report. |
| `METRICS_AND_FINDINGS_EXPLAINED.md` | Self-contained explainer of the metric chain and every finding, with bug history. |
| `RQ5_ANALYSIS_PLAN.md` | Pre-registered plan for cross-benchmark validity (RQ5/H6). |
| `RQ5_INTERPRETATION.md` | Interpretation of RQ5/H6 cross-benchmark rank agreement, with correction history. |
| `STABILITY_INTERPRETATION.md` | Interpretation of instantiation-to-instantiation stability (RQ4.1), with a dedup-bug correction noted. |

## Auto-generated provenance — narrative docs (17 docs)

`*_PROVENANCE.md` files (plus `RANKING_MATRIX.md`/`STABILITY.md`, which are
auto-generated despite lacking "PROVENANCE" in the name). All are registered
steps in `scripts/build_thesis_assets.py` and reproducible by rerunning it.

| Document | Description |
|---|---|
| `collapse_vs_survival_PROVENANCE.md` | Provenance for the collapse-vs-survival figure. |
| `COMPARISON_PROVENANCE.md` | Raw generation provenance for Comparison A + B (sources, missing models). |
| `comparison_c_onset_curve_PROVENANCE.md` | Provenance for the Comparison C onset-curve figure. |
| `COMPARISON_C_PROVENANCE.md` | Raw DiD/gradient/Mut@K tables for Comparison C. |
| `finetune_decline_table_PROVENANCE.md` | Provenance for the epoch-0-vs-30 held-out decline table. |
| `finetune_endpoint_table_PROVENANCE.md` | Provenance for the real (auto-generated) epoch-30 endpoint table. |
| `H3_TIER_GRADIENT_PROVENANCE.md` | Raw tables for the H3 tier-gradient result. |
| `noise_floor_PROVENANCE.md` | Provenance for the noise-floor figure. |
| `ranking_matrix_heatmap_PROVENANCE.md` | Provenance for the ranking-matrix heatmap figure. |
| `RANKING_MATRIX.md` | Metric-agnostic ranking tables. |
| `rq5_correlation_PROVENANCE.md` | Provenance for the RQ5 correlation scatter figure. |
| `RQ5_PROVENANCE.md` | Raw model-ranking and correlation tables for RQ5/H6. |
| `rq5_cross_family_correlation_PROVENANCE.md` | Provenance for the cross-family correlation scatter figure. |
| `RQ5_CROSS_FAMILY_PROVENANCE.md` | Raw tables for the cross-family extension. |
| `RQ5_DIAGNOSTICS.md` | Post-hoc diagnostics of RQ5's low rank agreement (tier-matching, etc.). |
| `RQ5_SANITIZER_SENSITIVITY.md` | Sanitizer-repair sensitivity analysis for RQ5. |
| `STABILITY.md` | Raw StableMut@K/Kendall-tau tables. |

## Auto-generated provenance — data files (47 `.csv` + 1 `.xlsx`)

Each pairs with one of the narrative docs above or with a
`scripts/build_thesis_assets.py` step directly; not tabulated individually
here — see the matching narrative doc, or run
`python scripts/build_thesis_assets.py --list` for the full step registry.
Eleven CSVs (`comparison_c_confounder_audit.csv`,
`comparison_c_unseen_vs_plt_audit.csv`, `ult_ground_truth_baseline.csv`,
`ult_ground_truth_taxonomy.csv`, and the six `epoch_perf_finetune_*.csv`
condition files) are auto-generated but produced by a script outside the
`build_thesis_assets.py` registry, so they aren't reproduced by a plain
rerun — see the historical diagnostics that produced them in
`scripts/README.md`. `rq5_public_scores.csv` is the one exception that's
hand-compiled, not script-generated (published BigCodeBench scores,
manually researched — see `RQ5_LEADERBOARD_HARVEST.md`).

## Preserved historical record (24 docs)

Records of a specific past incident, correction, or decision, kept for the
audit trail rather than as current/live guidance.

| Document | Description |
|---|---|
| `EXCLUSIONS.md` | Log of 7 excluded batch requests (transient API errors) for inst1 L3/L4. |
| `FIGURE_AUDIT.md` | Audit of which figures have provenance sidecars, gaps found/fixed. |
| `GEMINI_DAILY_CRAWL.md` | Runbook/status for the Gemini Pro Preview daily-crawl coverage gap (now closed). |
| `GENERATION_CONFIG_GAP_local_qwen.md` | Records an unlogged, silently-inherited `repetition_penalty`/`top_k` default bug. |
| `HYPOTHESIS_COVERAGE_AUDIT.md` | Per-hypothesis pipeline/verdict audit against the six approved hypotheses. |
| `HYPOTHESIS_DEVIATIONS.md` | Ledger of approved wording vs what was executed, per hypothesis, and why it differs. |
| `MUTANT_COUNT_SPEC_AUDIT.md` | Discrepancy audit: `PROJECT_BRIEF.md`'s mutant-count spec vs observed data. |
| `OPENAI_COST_AND_BILLING.md` | Pre-spend cost/billing investigation for GPT-5/-mini batches. |
| `OPENAI_PREFLIGHT_GO_NOGO.md` | Pre-flight checklist (corpus-drift check) before submitting GPT-5 batches. |
| `OPEN_ITEMS.md` | Pre-submission checklist (blocking / disclose / future-work items); several entries record already-closed discrepancies with dates, but as of writing some remain live. |
| `README.md` | Contamination notice: which `epoch_perf_finetune_*.csv` files were corrupted, and why. |
| `README_QUARANTINE.md` | Correction layer on top of `README.md`; documents one discrepancy between the two. |
| `RQ5_CROSS_DEFINITION_AUDIT.md` | Revision history resolving a Mut@K definition contradiction against the ULT source paper. |
| `RQ5_CROSS_FAMILY_PROPOSAL.md` | Original proposal for the 4-model cross-family extension, preserved as written. |
| `RQ5_LEADERBOARD_HARVEST.md` | Dated log of which pinned model snapshots have published BigCodeBench numbers. |
| `RQ5_SUPERVISOR_SUMMARY_20260729.md` | Dated supervisor-meeting summary; its headline correlation figure is since superseded (see `RQ5_INTERPRETATION.md`). |
| `SUPERVISOR_HANDOFF_20260714.md` | Handoff note: GPT-5/-mini Dynamic-benchmark batch requests, ready to submit. |
| `SUPERVISOR_HANDOFF_SUBMIT_ALL.md` | Consolidated submission summary for all three pending GPT batches. |
| `SUPERVISOR_HANDOFF_ULT_PLT_20260713.md` | Handoff note: GPT-5/-mini ULT/PLT `core_400` batch, ready to submit. |
| `SUPERVISOR_NOTE_COMPARISON_C_20260726.md` | Note flagging a ULT training-data quality issue ahead of a supervisor meeting. |
| `TIER_SYMMETRY_AUDIT.md` | Read-only audit confirming cross-benchmark comparisons are like-for-like. |
| `ULT_DATA_QUALITY_AUDIT.md` | Consolidates three findings on ULT/PLT's published data-quality issues. |
| `VALIDATOR_SWEEP.md` | Sweep of every validator/audit script for silent-failure bug patterns. |
| `WORKBOOK_VERIFICATION.md` | Discrepancy report: `docs/Research_questions.xlsx` numbers vs live repo data. |

## Mechanism file

| Document | Description |
|---|---|
| `CITATION_ALLOWLIST.md` | Hand-maintained, actively-edited file feeding `scripts/check_doc_citations.py` — entries tagged historical/verified-current/definitional. Doesn't fit the three roles above cleanly: not prose interpretation, not script output, and not a closed incident. |

## Investigation scripts (6 `.py` files)

`inst1_control_analyze_generation.py`, `inst1_control_generate_epoch30.py`,
`inst1_control_lora_b_norms.py`, `inst1_control_memorization_ceiling.py`,
`inst1_control_parse_training_logs.py`, `inst1_control_stats.py` — read-only
helper scripts for one investigation (whether an inst1 LoRA fine-tune was a
genuine null result). Their write-up is `analysis/reports/inst1_control_verification.md`.

## Subdirectories

| Directory | Contents |
|---|---|
| `derived/` (8 files) | Auto-generated derived data (epoch-perf gap CSVs, inst1-control generation JSONL/McNemar CSVs); not in the `build_thesis_assets.py` registry. |
| `diversity/` (9 files) | `README.md` + `thresholds.md` are hand-written methodology/policy; the rest are auto-generated from a SLURM diversity-audit run, also outside the registry. |
| `equiv_mutants/` (3 files) | `README.md` is hand-written methodology; `inspection_sheet.xlsx` and `sample_manifest.json` are an auto-generated sample pack. |
| `reports/` (1 file) | `inst1_control_verification.md` — the hand-written write-up for the investigation scripts above. |
| `figures/` (29 files) | Auto-generated PDF/PNG figures from the `plot_*.py` registry steps, plus a handful of superseded/archived figures kept for the record. |
