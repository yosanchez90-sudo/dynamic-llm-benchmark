# scripts/ — index

74 scripts (72 `.py`, 2 `.sh`), grouped by role. `scripts/slurm/*.slurm` holds
the SLURM launcher for each pipeline entrypoint below (one `.slurm` file per
`.py`, same base name where the correspondence is direct).

## Pipeline entrypoints (26)

Scripts that generate or move real result data — model calls, fine-tuning,
data prep, coverage/cost planning. Most are launched via a matching
`scripts/slurm/*.slurm` job.

| Script | Purpose |
|---|---|
| `run_eval.py` | Runs one test-generation config from YAML; the harness nearly every `run_*.slurm` job calls into. |
| `submit.sh` | Routes an eval config to the right SLURM template by provider/model size (a100/mig/v100/api). |
| `create_batch.py` | Builds and submits an OpenAI Batch job from one or more configs. |
| `process_batch.py` | Downloads a completed OpenAI Batch's results and runs mutation scoring on each row. |
| `check_openai_batch_status.py` | Polls the batch state files for the named GPT-5/-mini batches; exits 0 only once all are `completed`. |
| `eval_checkpoints.py` | Evaluates LoRA checkpoints across epochs, hot-swapping adapters on one loaded base model, for the epoch-perf curves. |
| `finetune_qwen7b.py` | LoRA fine-tunes Qwen2.5-Coder (7B/1.5B) via TRL's `SFTTrainer` for the contamination-simulation experiment. |
| `prepare_finetune_data.py` | Builds instruction-tuning pairs from a model's own extracted test output (self-distillation), for the six supplementary fine-tuning runs. |
| `build_ult_training_pairs.py` | Builds prompt→ground-truth-test pairs for the canonical ULT fine-tune, from ULT's own shipped `tests` field. |
| `finalize_ult_training_set.py` | Token-length-filters the repair-verified ULT training pairs against the real tokenizer/context window. |
| `build_onset_curve_manifest.py` | Freezes the fixed 175-problem subsample used at every epoch point of the fine-tuning onset curve. |
| `build_comparison_c_seen_manifest.py` | Freezes the seen-vs-unseen core_400 ULT manifest and runs a confounder audit between the two. |
| `build_equiv_mutant_sample.py` | Builds the stratified 120-mutant hand-inspection pack for equivalent-mutant estimation. |
| `generate_ult_plt_subsample.py` | Pins the CC-stratified ULT/PLT subsamples (`core_400`, `qwen_1000`) to a manifest, seed=42. |
| `generate_instantiation_manifest.py` | Runs the template engine over all 60 templates × 5 seeds for one instantiation; records a validation manifest. |
| `run_gemini_daily_crawl.py` | Sends a daily budget of Gemini 3.1 Pro Preview requests toward the Dynamic-benchmark coverage backfill; resume-safe. |
| `check_gemini_pro_crawl_done.py` | Exits 0 if Gemini Pro Preview's Dynamic coverage is complete; otherwise prints what's missing. |
| `run_onset_curve.py` | Generates the epoch-onset curve (baseline-pass + verbatim-match) for the canonical Qwen-1.5B-on-ULT adapter. |
| `merge_epoch_curve_shards.py` | Merges sharded epoch-curve CSVs into per-condition files, verifying every (epoch, instantiation, draw) triple is present exactly once. |
| `submit_epoch_curve_shards.py` | Submits the epoch-curve rebuild as SLURM shards sized per condition, instead of one long per-condition job. |
| `verify_finetune_readiness.py` | Pre-flight assertions (EOS termination, completion masking, train/eval prompt byte-identity) before the canonical ULT fine-tune runs. |
| `verify_ult_adapter.py` | Sanity-checks a saved adapter loads via the real harness class and reports its resolved generation config. |
| `coverage_matrix.py` | Diffs the result files under `data/results/dynamic/` against the model×tier×instantiation spec; reports missing/partial cells. |
| `estimate_cost.py` | Prices every coverage gap `coverage_matrix.py` finds — USD for API models, GPU-hours for local Qwen. |
| `check_gpu.py` | Pre-flight CUDA/GPU sanity check, run before a GPU job to catch a missing module or mismatched torch wheel early. |
| `activate.sh` | Sourced (not run) to load Kelvin2's Python/CUDA modules and activate `.venv/` for interactive use. |

## Table/figure builders (33)

Scripts that read existing result/analysis data and produce a table, figure,
or paper-facing artefact. Most are registered steps in
`scripts/build_thesis_assets.py --list`.

| Script | Produces |
|---|---|
| `build_thesis_assets.py` | The orchestrator — runs every step below (or a `--only` subset) in one command. |
| `build_comparison_tables.py` | Comparison A (Dynamic-L4 vs ULT) and Comparison B (ULT vs PLT) tables. |
| `analyze_stability.py` | StableMut@K and pairwise Kendall tau across instantiations (RQ4.1). |
| `build_finetune_endpoint_table.py` | Supplementary-study endpoint table (greedy + R=3 sampling). |
| `build_finetune_decline_table.py` | Supplementary-study held-out exec_rate decline table (epoch 0 vs 30). |
| `analyze_comparison_c.py` | Comparison C's canonical 2×3 difference-in-differences, gradient, and Mut@K tables. |
| `plot_comparison_c_onset_curve.py` | Comparison C onset-curve figure (baseline-pass + verbatim-match by epoch). |
| `analyze_rq5.py` | RQ5/H6 model-ranking table and cross-benchmark correlations. |
| `plot_rq5_correlation.py` | RQ5 correlation scatter figure. |
| `analyze_rq5_diagnostics.py` | RQ5 post-hoc diagnostics: tier-matching, discrimination, conditioning, attenuation. |
| `analyze_rq5_cross_family.py` | RQ5 cross-family extension: canonical-only vs +4-family correlations. |
| `plot_rq5_cross_family_correlation.py` | RQ5 cross-family correlation scatter figure. |
| `analyze_rq5_sanitizer_sensitivity.py` | RQ5 sanitizer-repair sensitivity: per-model repair fraction with/without repaired rows. |
| `analyze_h3_tier_gradient.py` | H3/RQ2 tier-gradient table: per-model and pooled Spearman rho, Holm-corrected. |
| `build_ranking_matrix.py` | Metric-agnostic ranking matrix (exec_rate/baseline_pass/Mut@K/coverage-adjusted) side by side. |
| `plot_ranking_matrix_heatmap.py` | Ranking-matrix heatmap figure (Kendall tau by metric × benchmark). |
| `plot_noise_floor.py` | Noise-floor-by-metric-and-tier figure. |
| `plot_collapse_vs_survival.py` | Collapse-vs-survival figure (raw vs coverage-adjusted Mut@K at n=3 vs n=7). |
| `plot_flow_diagram.py` | End-to-end pipeline flow diagram (template → hypothesis test); structural, not data-derived. |
| `plot_contamination_loop.py` | Three-step contamination-loop diagram for the slide deck; structural, not data-derived. |
| `build_research_questions_md.py` | Mirrors `docs/Research_questions.xlsx` to `docs/RESEARCH_QUESTIONS.md`. |
| `build_paper_bib.py` | Generates `paper/references.bib` from `paper/references.yaml`. |
| `build_paper_table1.py` | Compact hypothesis/prediction/verdict table (`paper/table1.tex`). |
| `build_paper_values.py` | Every quantitative value the paper cites, as LaTeX macros read live from `analysis/*.csv`. |
| `build_supporting_report_docx.py` | Formats the citation-gated markdown source into the supporting report's `.docx`. |
| `build_slides.py` | Builds the sixteen-slide ECS8056 presentation deck. |
| `check_doc_citations.py` | The citation gate: scans `analysis/*.md`/`paper/sections/*.tex` for hand-typed numbers that no longer match a live source. The final registered step — not itself a producer, but gates everything above. |
| `plot_epoch_perf.py` | Baseline-pass-vs-epoch plot per instantiation, one call per fine-tune condition. |
| `plot_epoch_perf_comparison.py` | Condition-aware epoch-perf comparison plot (seen vs unseen). |
| `analyze_contamination.py` | Difference-in-differences estimator for Comparison C, for whichever benchmarks currently have real pre/post data. |
| `compute_validated_score.py` | Mut@K_validated from the hand-inspected equivalent-mutant sample, with Wilson CI + bootstrap. Needs a filled-in inspection sheet, so it's excluded from the automated `build_thesis_assets.py` registry. |
| `results_to_excel.py` | Converts every Dynamic-benchmark result file into one Excel workbook (one sheet per model plus a summary). |
| `archive_diversity_audit.py` | Archives the within-tier diversity/mutation-density sweep outputs to `analysis/diversity/`. |

## Historical diagnostics (15)

One-off investigation or repair scripts for a specific past bug or
data-quality finding — not part of the regular pipeline going forward.

| Script | Finding | Written up in |
|---|---|---|
| `diagnose_collapse.py` | Phase-1: dumps raw pre-extraction completions to find why held-out exec_rate collapsed in 3/6 Comparison-C fine-tune conditions. | `analysis/README.md`, `analysis/README_QUARANTINE.md` |
| `diagnose_collapse_ab.py` | Phase-1 follow-up: A/B tests whether `eval_checkpoints.py`'s extra generation knobs corrupt the required import line. | `analysis/README.md`, `analysis/README_QUARANTINE.md` |
| `diagnose_collapse_direct.py` | Phase-1 follow-up: reuses the real inference/scoring functions directly to rule out a transcription bug in the earlier diagnostics. | `analysis/README.md`, `analysis/README_QUARANTINE.md` |
| `diagnose_collapse_full150.py` | Phase-1b: reproduces the epoch=30/inst=2 cell at full n=150 to resolve a stale-vs-real contradiction. | `analysis/README_QUARANTINE.md` |
| `diagnose_collapse_v100.py` | Phase-1b: hardware control — reruns the same test on the original V100 hardware instead of an untested A100 MIG slice. | `analysis/README_QUARANTINE.md` |
| `diagnose_collapse_reppen.py` | Phase-1b: isolates a silently-inherited `repetition_penalty=1.1` default as a candidate cause. | `analysis/README.md`, `analysis/README_QUARANTINE.md` |
| `diagnose_collapse_2x2.py` | Phase-1c: decisive 2×2 factorial (no_repeat_ngram_size × repetition_penalty) under sampling on the primary suspect checkpoint. | `analysis/README.md`, `analysis/README_QUARANTINE.md` |
| `diagnose_collapse_greedy_gpt5.py` | Phase-1b follow-up: tests whether greedy decoding also resolves the bp_gpt5 condition, or whether its collapse is sampling-independent. | `analysis/README.md`, `analysis/README_QUARANTINE.md` |
| `diagnose_collapse_greedy_gpt5_ngram4.py` | Phase-1c: fills the missing greedy+ngram4 cell and measures per-generation wall-clock time to size the timeout deliberately. | `analysis/README.md`, `analysis/README_QUARANTINE.md` |
| `diagnose_collapse_1_5b_greedy.py` | Phase-1c: 1.5B greedy retests, closing the two open cells left from the 7B reconciliation. | `analysis/README.md`, `analysis/README_QUARANTINE.md` |
| `audit_result_integrity.py` | Read-only integrity audit of the Dynamic/ULT/PLT result files (parse errors, duplicate triples, row-count gaps), triggered by the tier-blind resume-matcher issue. | `analysis/COMPARISON_PROVENANCE.md`, `analysis/VALIDATOR_SWEEP.md` |
| `audit_unseen_ult_vs_plt.py` | Checks whether unseen-ULT is a systematically harder population than PLT core_400, to explain a gain-inversion finding in Comparison C. | `analysis/COMPARISON_C_INTERPRETATION.md`, `analysis/VALIDATOR_SWEEP.md` |
| `check_ult_ground_truth_baseline.py` | Pre-flight check: does ULT's own shipped `tests` field pass against its own shipped `code`? Found only 8.5% of CC≥8 records fully passing. | `analysis/ULT_DATA_QUALITY_AUDIT.md`, `analysis/VALIDATOR_SWEEP.md` |
| `repair_ult_ground_truth.py` | Taxonomy, repair, and verification for ULT's ground-truth tests, following the baseline-check finding above. | `analysis/ULT_DATA_QUALITY_AUDIT.md`, `analysis/COMPARISON_C_INTERPRETATION.md` |
| `migrate_add_model_label.py` | One-off migration: backfills `model_label` into pre-2026-07-09 result files, using the loader's own filename-fallback logic. | No dedicated write-up in `analysis/` or `CLAUDE.md`; see git commits `328f0b6`/`b7d92da` and the script's own module docstring. |

## Notes on borderline classifications

- `check_gpu.py` and `activate.sh` are standalone environment/pre-flight
  utilities rather than pipeline steps in the usual sense; listed under
  pipeline entrypoints because they gate or set up GPU jobs directly.
- `coverage_matrix.py` and `estimate_cost.py` are planning/support tools
  (what's missing, what would it cost) rather than literal result generators;
  listed under pipeline entrypoints as the closest fit.
- `build_thesis_assets.py` is the registry itself, not one of its own
  registered steps; `check_doc_citations.py` is a validation gate rather than
  a producer. Both are listed under table/figure builders since that's the
  group they drive/gate.
- `archive_diversity_audit.py` is grouped as a table/figure builder (it
  archives sweep outputs on an ongoing basis), but a real historical bug in
  its README-generation logic — hardcoded pass/fail numbers instead of
  reading them from the data just computed, fixed 2026-08-03 — is documented
  in `analysis/VALIDATOR_SWEEP.md` and `CLAUDE.md`.
