# inst1-control verification: genuine null, training no-op, or eval bug?

**Date:** 2026-07-16 · **Scope:** read-only investigation, no pipeline code changed, no jobs launched, no data files modified. Helper scripts written for this investigation live in `analysis/` (`inst1_control_*.py`) and are read-only themselves (log/checkpoint/CSV parsing only).

## Verdict (both models)

| Model | loss↓ | \|\|B\|\| grows | outputs differ | pass flat | **Verdict** |
|---|---|---|---|---|---|
| Qwen 1.5B inst1 | ✅ 99.12% drop | ✅ 0→248.36 | ✅ (proxy, see §E) | ✅ p=0.40 | **Strongest control (genuine null)** |
| Qwen 7B inst1 | ✅ 99.03% drop | ✅ 0→356.17 | ✅ (proxy, see §E) | ✅ p=0.62 | **Strongest control (genuine null)** |

Both inst1 fine-tunes land on the matrix's first row: *"loss↓ + ||B|| grows + outputs differ + pass flat → strongest control."* Beyond the matrix's generic framing, **the null has a precise, mechanistic explanation** (§G): inst1's training targets are the base model's own generated test files, filtered only by `exec_ok` (does it run?), never by `baseline_passed` (is it correct?). Only 12.2% (1.5B) / 31.5% (7B) of the actual training examples were *also* correct. The observed epoch-30 "seen" baseline_pass rate — 10.0% / 31.3% — matches that ceiling almost exactly. The model appears to memorize its training targets near-perfectly; those targets just weren't very good to begin with. This is a stronger, more falsifiable story than "it stayed flat and we don't know why."

**One important caveat that survives the verdict** (not a red flag, but a real gap): steps E(ii)/(iii) and F's McNemar pairing could not be completed as literally specified, because `eval_checkpoints.py` never persists per-problem raw text or per-problem pass/fail — only aggregate counts. See §E and §F for what was substituted and why the substitute is still probative.

**Recommended next action:** write up the inst1 control citing the loss-drop/‖B‖-growth/memorization-ceiling chain explicitly (as the matrix's first row prescribes) — no rerun, no code fix needed. Separately (not blocking the write-up): if a future session wants the *literal* E(ii)/(iii)/F checks closed rather than proxied, `eval_checkpoints.py` would need to be extended to persist per-problem raw completions and adapter provenance (path+hash) per row — that's a code change and a rerun, explicitly out of scope here, and is a recommendation, not an action taken.

---

## A. Artifacts located

| Condition | Model | Checkpoints | Training log (SLURM stdout) | Training data file (rows) |
|---|---|---|---|---|
| inst1 | Qwen 1.5B | `data/finetune/qwen1_5b_lora_inst1_30ep/checkpoint-{17..510}` (30 ckpts, step 17/epoch) + `adapter_final` | `logs/finetune-30ep-9264922.out` | `data/finetune/train_qwen1_5b_inst1.jsonl` (131 rows) |
| inst1 | Qwen 7B | `data/finetune/qwen7b_lora_inst1_30ep/checkpoint-{19..570}` (30 ckpts, step 19/epoch) + `adapter_final` | `logs/finetune-30ep-9264920.out` | `data/finetune/train_qwen7b_inst1.jsonl` (149 rows) |
| bp_gpt5 (comparator) | Qwen 1.5B | `data/finetune/qwen1_5b_lora_bp_gpt5_30ep/checkpoint-{16..480}` | `logs/finetune-30ep-9280070.out` | `data/finetune/train_gpt5_inst1_bp.jsonl` (128 rows) |
| bp_gpt5 (comparator) | Qwen 7B | `data/finetune/qwen7b_lora_bp_gpt5_30ep/checkpoint-{16..480}` | `logs/finetune-30ep-9280068.out` | `data/finetune/train_gpt5_inst1_bp.jsonl` (128 rows, shared file — GPT-5's outputs don't depend on which Qwen size is later fine-tuned on them) |

Each checkpoint directory contains `adapter_model.safetensors`, `adapter_config.json`, `trainer_state.json`, `training_args.bin`, tokenizer files. `trainer_state.json`'s `log_history` was spot-checked against the SLURM stdout parse for the 1.5B-inst1 run (`checkpoint-510/trainer_state.json`): `global_step=510` = 17 steps/epoch × 30 epochs exactly; first (`step=5, loss=1.4893`) and last (`step=510, loss=0.0131`) entries match the stdout log verbatim.

Note: an earlier, abandoned 7B-inst1 attempt exists at `data/finetune/qwen7b_lora_inst1/` (only 3 checkpoints, steps 19/38/57) — not used; the authoritative run is `qwen7b_lora_inst1_30ep` (30 checkpoints). Four earlier retry attempts at the same config also exist as training logs (`logs/finetune-7b-9234245.out`, `-9243317`, `-9243385`, `-9243746`) predating the final successful `9264920` run; not analyzed, since the final run's own artifacts are complete and self-consistent.

Config files: `configs/finetune_qwen{1_5b,7b}_{inst1,bp_gpt5}_30ep.yaml`.

---

## B. Loss traction

Parsed with `analysis/inst1_control_parse_training_logs.py` (`ast.literal_eval` on each HF-Trainer-printed `{'loss': ..., 'epoch': ...}` stdout line).

```
python analysis/inst1_control_parse_training_logs.py --log logs/finetune-30ep-9264922.out --config configs/finetune_qwen1_5b_inst1_30ep.yaml
python analysis/inst1_control_parse_training_logs.py --log logs/finetune-30ep-9264920.out --config configs/finetune_qwen7b_inst1_30ep.yaml
python analysis/inst1_control_parse_training_logs.py --log logs/finetune-30ep-9280070.out --config configs/finetune_qwen1_5b_bp_gpt5_30ep.yaml
python analysis/inst1_control_parse_training_logs.py --log logs/finetune-30ep-9280068.out --config configs/finetune_qwen7b_bp_gpt5_30ep.yaml
```

| Condition | first loss | last loss | relative drop | mean `train_loss` (HF's whole-run average) |
|---|---|---|---|---|
| 1.5B inst1 | 1.4893 | 0.0131 | **99.12%** | 0.1048 |
| 7B inst1 | 1.3227 | 0.0128 | **99.03%** | 0.0832 |
| 1.5B bp_gpt5 | 1.2904 | 0.0077 | 99.40% | 0.1522 |
| 7B bp_gpt5 | 1.1616 | 0.0062 | 99.47% | 0.1161 |

**Red flag ("inst1 loss flat within noise") not observed** — inst1's drop (99.0–99.1%) is essentially as large as bp_gpt5's (99.4–99.5%), and inst1's *mean* train_loss is actually lower than bp_gpt5's in both sizes.

Convergence-speed detail (loss at nearest logged step to each epoch, both training logs, all four conditions):

| epoch≈ | 1.5B inst1 | 1.5B bp_gpt5 | 7B inst1 | 7B bp_gpt5 |
|---|---|---|---|---|
| 5 | 0.1246 | 0.3579 | 0.0799 | 0.2519 |
| 10 | 0.0470 | 0.0793 | 0.0287 | 0.0342 |
| 15 | 0.0216 | 0.0216 | 0.0167 | 0.0123 |
| 20 | 0.0181 | 0.0097 | 0.0158 | 0.0073 |
| 25 | 0.0153 | 0.0080 | 0.0141 | 0.0064 |

inst1 actually converges *faster* early (epoch 5) — its targets are the model's own natural output distribution, easier to fit than bp_gpt5's cross-model (GPT-5-style) targets. bp_gpt5 catches up and edges ahead by epoch ~15–20, reaching its own near-zero floor (≤0.01) right around epoch 20 — this **does** align with bp_gpt5's seen-curve saturation (its seen baseline_pass rate visibly plateaus from epoch 20 onward in `analysis/figures/epoch_perf_{qwen1_5b,qwen7b}_bp_comparison.pdf`). Both conditions are fully converged (loss <0.02) well before epoch 30 in both model sizes — no evidence of undertraining for inst1 relative to bp_gpt5.

---

## C. Schedule sanity

Same script/invocations as §B; full output below is what `schedule_summary()` printed.

| Condition | n_train | eff. batch | steps/epoch | total steps | warmup ratio | warmup steps | warmup < total? | peak LR reached | peak LR / configured | final LR | grad_norm range |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.5B inst1 | 131 | 8 | 17 | 510 | 0.05 | 25 | **True** | 1.9998e-4 | 99.99% | 2.1e-9 | [0.0323, 0.4902] |
| 7B inst1 | 149 | 8 | 19 | 570 | 0.05 | 28 | **True** | 2.0000e-4 | 100.0% | 1.7e-9 | [0.0205, 0.1628] |
| 1.5B bp_gpt5 | 128 | 8 | 16 | 480 | 0.05 | 24 | **True** | 2.0000e-4 | 100.0% | 2.4e-9 | [0.0320, 0.3585] |
| 7B bp_gpt5 | 128 | 8 | 16 | 480 | 0.05 | 24 | **True** | 2.0000e-4 | 100.0% | 2.4e-9 | [0.0179, 0.2198] |

- `effective_batch_size = per_device_train_batch_size(1) × gradient_accumulation_steps(8) × world_size(1)` — single-GPU training throughout, confirmed by every training log's `GPU: NVIDIA A100-SXM4-80GB` single-device header line and `nvidia-smi` not showing multi-GPU allocation.
- **Warmup is ~5% of total steps in every condition, never remotely close to ≥ total steps.** The "silent near-no-op via warmup≥total" mundane culprit is ruled out for both inst1 conditions.
- Peak LR reached is 99.99–100.0% of the configured `2.0e-4` in all four conditions — the schedule genuinely reaches peak, then cosine-decays to ~0 by step count's end (final LR ~1e-9–2e-9, i.e. numerically zero).
- No zero grad norms anywhere; magnitudes are unremarkable and comparable in range across all four conditions (no condition shows a suspiciously collapsed or exploded gradient signal).

**Config diff across conditions** (`diff` on the four YAMLs with `name`/`output_dir`/`results_file`/`train_file`/`min_quality` fields normalized out — i.e. isolating everything *except* the intentional data/output differences):
```
diff <(sed '...' configs/finetune_qwen1_5b_inst1_30ep.yaml) <(sed '...' configs/finetune_qwen1_5b_bp_gpt5_30ep.yaml)
diff <(sed '...' configs/finetune_qwen7b_inst1_30ep.yaml)   <(sed '...' configs/finetune_qwen7b_bp_gpt5_30ep.yaml)
```
Result: **only comment lines (`#...`) differ.** Every actual hyperparameter (`lora.r/alpha/dropout/target_modules`, `num_train_epochs`, `per_device_train_batch_size`, `gradient_accumulation_steps`, `learning_rate`, `lr_scheduler_type`, `warmup_ratio`, `max_length`, `save_strategy`, `save_total_limit`, `logging_steps`, `bf16`, `gradient_checkpointing`, `seed`) is byte-identical between inst1 and bp_gpt5 for each model size. The `no_repeat_ngram_size=4`-style "uncommitted config divergence" failure mode does **not** recur here — these are static, committed YAML files (not a live-mutated eval script), and the diff is clean.

---

## D. Adapters actually changed

Computed with `analysis/inst1_control_lora_b_norms.py`, which reads `adapter_model.safetensors` directly via the `safetensors` library (no model loading, no GPU) and sums the Frobenius norm of every `lora_B` tensor. `lora_B` initializes at all-zeros under standard PEFT LoRA init (`init_lora_weights: true`, confirmed in every `adapter_config.json` read), so a run that never trains would show ≈0 at every checkpoint.

```
python analysis/inst1_control_lora_b_norms.py --run-dir data/finetune/qwen1_5b_lora_inst1_30ep --steps-per-epoch 17
python analysis/inst1_control_lora_b_norms.py --run-dir data/finetune/qwen7b_lora_inst1_30ep   --steps-per-epoch 19
python analysis/inst1_control_lora_b_norms.py --run-dir data/finetune/qwen1_5b_lora_bp_gpt5_30ep --steps-per-epoch 16
python analysis/inst1_control_lora_b_norms.py --run-dir data/finetune/qwen7b_lora_bp_gpt5_30ep   --steps-per-epoch 16
```

| Condition | epoch 1 | epoch 5 | epoch 15 | epoch 30 (final) | shape |
|---|---|---|---|---|---|
| 1.5B inst1 | 57.06 | 200.52 | 245.02 | **248.36** | steep rise → saturating (classic converging-training curve) |
| 7B inst1 | 94.66 | 307.26 | 353.58 | **356.17** | same shape |
| 1.5B bp_gpt5 | 52.35 | 221.57 | 308.63 | **312.28** | same shape, comparable magnitude |
| 7B bp_gpt5 (spot value) | — | — | — | **430.03** | same shape (full trace in helper output) |

**Red flag ("≈0 at epoch 30") not observed for either inst1 model.** Growth is monotone, saturates as loss converges (per-epoch delta shrinks from +83 at epoch 2 down to +0.0006 at epoch 30 for 1.5B inst1 — exactly the shape expected as the model approaches its loss floor), and is the same order of magnitude as the bp_gpt5 comparator. The adapters are not sitting at their zero-init values; the weights genuinely moved.

---

## E. Eval really loaded the adapters

### (i) Provenance fields

**Checked and found lacking**, which is itself the most concrete finding of this section: `data/results/finetune_rebuild/epoch_perf_finetune_*.csv` rows have the fieldnames `model, epoch, instantiation, draw, n, exec_rate, baseline_pass, do_sample, temperature, top_p, repetition_penalty, repetition_penalty_source, no_repeat_ngram_size, no_repeat_ngram_size_source, max_new_tokens, seed, max_seconds` — **no `adapter_path` or `adapter_hash` field.** This is a real gap relative to CONVENTIONS.md's "Adapter identity (path + hash) is part of model identity" rule; that rule was retrofitted into the *dynamic-benchmark* JSONL pipeline (`process_batch.py`/`run_eval.py`, commits `b7d92da`/`328f0b6`) but never into `scripts/eval_checkpoints.py`, which has its own separate, older schema. There is no per-row record of which adapter directory produced which row.

As a substitute, the checkpoint-selection **code** was read (not run) to check for a condition-specific path bug:
```python
# scripts/eval_checkpoints.py:399-408
ckpt_dirs = sorted(ckpt_base.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1]))
steps_per_epoch = int(ckpt_dirs[0].name.split("-")[1])  # epoch 1 step count
...
def _ckpt_for_epoch(ep):
    step = ep * steps_per_epoch
    for d in ckpt_dirs:                 # tolerance ±1 step for rounding
        if abs(int(d.name.split("-")[1]) - step) <= 1:
            return d
```
This function is condition-agnostic — the same code path runs for every one of the 6 conditions, with `ckpt_base` supplied from each condition's own YAML `training.output_dir`. There is no per-condition branch or special-case that could select the wrong directory only for inst1. This is inference from code review, not from recorded per-row provenance, and should be read as such.

### (ii)/(iii) Output identity between epoch 0 and epoch 30

**Could not be computed as literally specified**, and this is a genuine, reportable gap rather than a result: `eval_checkpoints.py`'s `_score_responses()` (line 284) only accumulates `exec_ok_total`/`bp_total` counters — it discards each problem's raw generated text immediately after scoring it, by design ("Only runs exec gate + baseline pass... to keep runtime tractable"). No raw per-problem completions for the inst1 condition exist anywhere in the repository (`data/results/debug_collapse/` has raw-text dumps only for `bp_own`/`bp_gpt5`, from an earlier, unrelated investigation — none for `inst1`). Computing a literal token-identity fraction would require generating new completions, i.e. launching a job, which this investigation is explicitly not permitted to do.

**Substitute check performed on existing data**: if the eval harness had a bug that always loaded the base model regardless of the requested epoch, every epoch's greedy-decoded run over the same 150 fixed problems would be **exactly reproducible and therefore identical** — same weights, same prompts, same decoding. So per-epoch aggregate `exec_rate`/`baseline_pass` would be *constant* across all 9 evaluated epochs. They are not:

**1.5B inst1** (greedy draw, `data/results/finetune_rebuild/epoch_perf_finetune_qwen1_5b_inst1_30ep.csv`):
```
epoch  inst1_exec inst1_bp  inst2_exec inst2_bp  inst3_exec inst3_bp
    0        0.90   0.1067        0.90   0.0867      0.9533   0.1133
    1        0.88   0.0800        0.86   0.0733      0.8800   0.0600
    3      0.9133   0.0867      0.9067   0.0867      0.9067   0.1067
    5      0.9333   0.0733      0.9667   0.0467      0.9467   0.0667
   10      0.9800   0.0800      0.9800   0.0800      0.9733   0.0600
   15      0.9867   0.0800      0.9533   0.0733      0.9800   0.0800
   20      0.9733   0.1000      0.9467   0.0800      0.9333   0.0933
   25      0.9800   0.1000      0.9467   0.0600      0.9267   0.0867
   30      0.9733   0.1000      0.9467   0.0667      0.9467   0.0867
```

**7B inst1** (same file naming, `qwen7b`): `exec_rate` sits near a 1.0 ceiling throughout (the 7B base model already writes syntactically valid tests almost every time, zero-shot), but `baseline_pass` moves clearly: 0.3067 → 0.3667 → 0.4133 → 0.3733 → 0.3267 → 0.3133 → 0.32 → 0.32 → 0.3133 across epochs 0→30 (inst1/seen column) — a rise-then-settle shape, not a flat line.

Neither table is constant. `exec_rate` for 1.5B visibly trends 0.90→0.97–0.98 as training epoch increases (consistent with the model learning its own output format better through fine-tuning), and `baseline_pass` fluctuates epoch-to-epoch in both models. **This is inconsistent with "the eval always loaded the base model"** — that would produce byte-identical numbers at every epoch, not a trending, fluctuating series. It is not as strong as a literal per-problem diff (which is what the brief asked for), but it is a real, existing-data-only check that fails to find the base-model-loading bug it was designed to catch.

**Conclusion for E**: (i) fails on paper (no provenance field) but passes on code inspection; (ii)/(iii) as literally specified are blocked by a real, pre-existing data gap (not something this investigation introduced), with a substitute aggregate-level check that is consistent with adapters being genuinely swapped per epoch.

---

## F. Statistics

Wilson 95% CIs and a two-proportion z-test, computed with `analysis/inst1_control_stats.py`.

**On pairing**: a true paired McNemar test needs per-problem pass/fail for seen vs unseen on the same `template_id`. As established in §E, `eval_checkpoints.py` never persists per-problem results for these checkpoint evals — the same underlying gap, not a new one. Per this investigation's own contingency instruction, a two-proportion z-test was used instead, and is flagged as unpaired in every result below.

```
python analysis/inst1_control_stats.py --csv data/results/finetune_rebuild/epoch_perf_finetune_qwen1_5b_inst1_30ep.csv   --epoch 30 --draw greedy
python analysis/inst1_control_stats.py --csv data/results/finetune_rebuild/epoch_perf_finetune_qwen7b_inst1_30ep.csv     --epoch 30 --draw greedy
python analysis/inst1_control_stats.py --csv data/results/finetune_rebuild/epoch_perf_finetune_qwen1_5b_bp_gpt5_30ep.csv --epoch 30 --draw greedy
python analysis/inst1_control_stats.py --csv data/results/finetune_rebuild/epoch_perf_finetune_qwen7b_bp_gpt5_30ep.csv   --epoch 30 --draw greedy
```

| Condition | seen k/n | seen Wilson 95% CI | unseen (pooled 2+3) k/n | unseen Wilson 95% CI | z | p (two-sided) |
|---|---|---|---|---|---|---|
| **1.5B inst1** | 15/150 (10.0%) | [0.0615, 0.1584] | 23/300 (7.7%) | [0.0516, 0.1124] | 0.839 | **0.401** |
| **7B inst1** | 47/150 (31.3%) | [0.2445, 0.3914] | 101/300 (33.7%) | [0.2856, 0.3919] | −0.497 | **0.619** |
| 1.5B bp_gpt5 (comparator) | 81/150 (54.0%) | [0.4602, 0.6178] | 4/300 (1.3%) | [0.0052, 0.0338] | 13.455 | 2.9e-41 |
| 7B bp_gpt5 (comparator) | 120/150 (80.0%) | [0.7289, 0.8562] | 36/300 (12.0%) | [0.0880, 0.1617] | 14.289 | 2.6e-46 |

inst1's seen/unseen Wilson intervals overlap substantially in both model sizes, and the two-proportion test fails to reject the null at any conventional threshold (p=0.40, p=0.62) — a textbook statistical null. bp_gpt5's intervals don't overlap at all, with p-values around 1e-41–1e-46 — an unambiguous, massive effect. The contrast between the two rows is exactly what a working causal control should look like.

---

## G. What is the target side of inst1's training pairs?

Read directly: `data/finetune/train_qwen1_5b_inst1.jsonl` (and `train_qwen7b_inst1.jsonl`, same structure), plus the data-prep script that built them, `scripts/prepare_finetune_data.py`.

Each row is `{"messages": [system, user, assistant], "template_id", "instance_seed", "tier", "mutation_score"}`. The **assistant target is not "problems only"** — it is the model's own previously-generated pytest test file for that exact function (verified: `train_row["messages"][2]["content"] == source_row["extracted_test_file"]` byte-for-byte, checked for one example; `!= source_row["response"]`, i.e. it's the *sanitized/extracted* code, not the raw chat completion with any surrounding prose/fences). **Authored by**: the base Qwen model itself, zero-shot, pre-fine-tune (`source_row["model"] == "Qwen/Qwen2.5-Coder-{1.5B,7B}-Instruct"`) — not GPT-5, not a human.

`prepare_finetune_data.py`'s own docstring: *"Only records where the generated test executed cleanly (exec_ok) are kept — we don't want to teach the model to produce broken syntax."* Critically, **the filter is `exec_ok`, not `baseline_passed`** (that's what distinguishes the `inst1` configs' `min_quality: exec_ok` from `bp_own`/`bp_gpt5`'s `min_quality: baseline_passed`). A test file can execute cleanly (imports fine, runs without crashing) while asserting the wrong thing about the function under test — i.e. being confidently incorrect.

This is neither of the two cases the investigation brief posed ("problems only" vs "passing problem→test targets") — it's a third case: **problem+attempted-solution pairs where correctness is explicitly not gated.** That distinction turns out to be load-bearing:

`analysis/inst1_control_memorization_ceiling.py` joins each of the 131/149 actual training examples back to its source row (by `template_id`+`instance_seed`) and checks whether it was *also* `baseline_passed=True`:
```
python analysis/inst1_control_memorization_ceiling.py --train-file data/finetune/train_qwen1_5b_inst1.jsonl --source-file data/results/dynamic/Qwen__Qwen2.5-Coder-1.5B-Instruct__dynamic__zero_shot__inst1__20260609T221336.jsonl
python analysis/inst1_control_memorization_ceiling.py --train-file data/finetune/train_qwen7b_inst1.jsonl   --source-file data/results/dynamic/Qwen__Qwen2.5-Coder-7B-Instruct__dynamic__zero_shot__inst1__20260617T124709.jsonl
```

| Model | training examples | also `baseline_passed=True` | ceiling | **observed epoch-30 seen `baseline_pass`** |
|---|---|---|---|---|
| 1.5B | 131 | 16 | **12.2%** | **10.0%** |
| 7B | 149 | 47 | **31.5%** | **31.3%** |

Both matches are within ~2pp, and the 7B match is within 0.2pp. **Interpretation**: given the loss/‖B‖ evidence that the model memorizes its training targets almost perfectly (§B, §D), the observed "flat" seen curve is not unexplained — it's capped near the fraction of training targets that were themselves correct. Perfect verbatim reproduction of a training set that was only ~12–32% correct to begin with cannot score much higher than ~12–32% on the correctness metric, no matter how well training converges. **"Problem exposure alone doesn't inflate scores; solution correctness does"** — extended one step further than the brief's own framing: even solution (not just problem) exposure doesn't inflate scores when the exposed solutions aren't themselves correct.

(Aside, not a red flag: the *current* on-disk source JSONLs contain 300 rows apiece for what a single 150-problem instantiation should be — the training logs from 2026-06-28 report "Loaded 150 records," so the files have grown since training happened, presumably from later backfill work in this repo. This doesn't affect the ceiling computation: the join against the actual 131/149 frozen training examples (written out at training time and never touched since) matched 100% with zero misses, so every training example's `baseline_passed` status was correctly resolved regardless of what else has been appended to the source file since.)

---

## Commands run (for reproducibility)

All commands above are read-only: `csv.DictReader`, `json.loads`, `yaml.safe_load`, `safetensors.safe_open`, `ast.literal_eval`, `diff`. No `sbatch`/`srun`, no writes under `data/`, no edits to any script outside `analysis/inst1_control_*.py` (new files) and this report.

---

## Addendum (2026-07-16): direct verification via one authorized inference pass

The original investigation above was read-only and, for steps E(ii)/(iii) and F, had to substitute aggregate-level proxies for literal per-problem checks that `eval_checkpoints.py` doesn't support (it discards raw text and per-problem pass/fail by design). This addendum closes those two gaps directly, via one explicitly authorized inference pass: load the epoch-30 inst1-condition adapter for each model, greedy-generate on inst1/inst2/inst3 (same adapter, same pass), and keep everything `eval_checkpoints.py` throws away.

**Schema change** (the one code change explicitly authorized for this task, no re-runs of historical data): `scripts/eval_checkpoints.py` now logs `adapter_path` and `adapter_weights_hash` (sha256 of `adapter_model.safetensors`, computed once per epoch) into every CSV row — closing the E(i) provenance gap found in the base investigation. Covered by `tests/test_eval_checkpoints_adapter_provenance.py` (6 tests). Existing `data/results/finetune_rebuild/epoch_perf_*.csv` files are unchanged; this only affects future runs.

### Setup

New script `analysis/inst1_control_generate_epoch30.py` reuses `eval_checkpoints.py`'s actual functions (`_run_inference`, `_score_fast`, `_ProcessWatchdog`, `adapter_weights_hash`, imported not reimplemented) so generation is identical in every parameter to every other checkpoint eval in this project — same `_TimeLimitCriteria`/watchdog protection, same greedy config, same problem reconstruction via `test_gen.load()`. Submitted via SLURM (`scripts/slurm/run_inst1_control_generate_epoch30.slurm`, `k2-gpu-v100`, confirmed idle capacity beforehand):

```
CONFIG=configs/finetune_qwen1_5b_inst1_30ep.yaml OUT=analysis/derived/inst1_control_epoch30_generation_qwen1_5b.jsonl EPOCH=30 \
  sbatch scripts/slurm/run_inst1_control_generate_epoch30.slurm
CONFIG=configs/finetune_qwen7b_inst1_30ep.yaml   OUT=analysis/derived/inst1_control_epoch30_generation_qwen7b.jsonl   EPOCH=30 \
  sbatch scripts/slurm/run_inst1_control_generate_epoch30.slurm
```

**Process note, reported rather than hidden**: the first attempt (jobs `9389597`/`9389598`, 2h budget) was killed partway through — throughput on V100 turned out to be ~3.4–3.8 problems/min, not the ~20 min/model originally guessed, projecting to ~2–2.2h for a full 3-instantiation run. Worse, that first version of the script only wrote output in one batch at the very end, so a timeout would have lost all results, not just the incomplete instantiation. Fixed before resubmitting: records are now appended and flushed immediately after each problem is scored, and the script resumes from whatever's already in `--out` (skips completed `(instantiation, template_id, instance_seed)` triples) — the same "write immediately so partial progress survives a crash" pattern `eval_checkpoints.py` itself uses. No data was actually lost (the killed jobs' batched writes never reached disk), but the design flaw was real. Resubmitted (jobs `9389614`/`9389615`, 5h budget) and both completed cleanly: 1.5B in 1:45:26, 7B in 1:32:59.

**Reproducibility check**: per-instantiation `baseline_passed` counts from this fresh generation matched the original `eval_checkpoints.py` epoch-30 CSV rows exactly in all 6 cells —

| Model | inst1 (seen) | inst2 (unseen) | inst3 (unseen) |
|---|---|---|---|
| 1.5B | 15/150 | 10/150 | 13/150 |
| 7B | 47/150 | 51/150 | 50/150 |

— identical to the numbers in §F above, from an entirely separate generation run. Greedy decoding with a fixed adapter is fully deterministic here.

Adapter hashes used (also now the exact values that would be logged by the schema change above): 1.5B `4d7b7072575480ef2dbae09b75765b9ea9291c396379837ac79036ee311ee796`, 7B `65a8f6ea1a07f0cc9a528710a4a77169e9ec37383d3add0899e9fbd7f61c5d79`.

### Part 1: seen (inst1) vs. training target — % token-identical, edit distance

`analysis/inst1_control_analyze_generation.py` joins each inst1-generated problem back to its target in the training JSONL (by `template_id`+`instance_seed` — direct match here, no prefixing issue, since both were produced by the same `instantiation_id=1` `test_gen.load()` call). Compared field: `extracted_test_file.strip()` on both sides, matching exactly what `scripts/prepare_finetune_data.py` uses as the fine-tuning target (not the sanitized/scored version). Token-identity uses the actual model tokenizer (`AutoTokenizer.from_pretrained`, exact token-ID-sequence equality); edit distance is character-level Levenshtein normalized by `max(len_a, len_b)`.

| Model | matched to a target | token-identical | mean normalized edit distance |
|---|---|---|---|
| 1.5B | 131/150 | **108/131 (82.4%)** | **0.0449** |
| 7B | 149/150 | **147/149 (98.7%)** | **0.0043** |

Sanity cross-check: among token-identical rows, `baseline_passed` in the fresh generation is 9/108 (1.5B) and 47/147 (7B) — the 7B figure matches the 47/149 "also baseline_passed" count from the memorization-ceiling calculation in §G exactly, as it must: reproducing a training target verbatim reproduces its correctness (or lack of it) too.

Spot-read to confirm real generation differences rather than artifacts:
- **Near-identical case** (1.5B, `L2-bucket-001`/1103, normalized edit distance 0.0035): generated and target text match character-for-character for the first 300+ characters checked; the tiny remaining diff is a minor formatting/wording difference later in the file, not a structural change.
- **Substantially different case** (1.5B, `L1-arithmetic-002`/1105, normalized edit distance 0.77): generated output uses a different test structure entirely (bare `normal_cases`/`edge_cases` lists, no `pytest.mark.parametrize`, different — and arithmetically inconsistent — expected values in the comments) versus the target's `@pytest.mark.parametrize`-based test with different numbers. These are genuinely different generations, not a truncation or extraction artifact.

**Interpretation** (per the task's own framework): both models show high-to-very-high identity/similarity to their own training targets (7B especially, at 98.7% exact token match). This is the "high identity" branch: **the seen plateau is reproduction of memorised targets**, strengthening rather than complicating the memorisation-without-inflation story from the base investigation — the model isn't doing something unrelated to its training data on the seen split, it's reproducing that data almost verbatim, and that reproduction is exactly what the memorization-ceiling calculation (§G) already predicted the pass rate would be.

### Part 2: paired McNemar, seen vs. unseen (bug found and fixed)

First run of this analysis produced `n_paired=0` for every comparison — investigated rather than accepted: `instance_seed` turned out to be **instantiation-prefixed** by `test_gen.load()` (inst1 uses 1101–1105, inst2 2101–2105, inst3 3101–3105 for what is conceptually the same 5 base seeds), so the naive pairing key `(template_id, instance_seed)` never matched across instantiations even though `template_id` sets were confirmed identical. Fixed by pairing on `(template_id, instance_seed % 1000)`, verified to recover a full 150/150 key overlap between every instantiation pair before trusting it for the real test.

With correct pairing, using the exact (sign-test-based) McNemar test on `baseline_passed`:

| Model | comparison | n paired | both pass | both fail | seen-only | unseen-only | McNemar exact p |
|---|---|---|---|---|---|---|---|
| 1.5B | inst1 vs inst2 | 150 | 2 | 127 | 13 | 8 | **0.383** |
| 1.5B | inst1 vs inst3 | 150 | 5 | 127 | 10 | 8 | **0.815** |
| 7B | inst1 vs inst2 | 150 | 34 | 86 | 13 | 17 | **0.585** |
| 7B | inst1 vs inst3 | 150 | 38 | 91 | 9 | 12 | **0.664** |

All four paired tests fail to reject the null at any conventional threshold — consistent with, and now directly confirming with a proper paired test (rather than the unpaired two-proportion proxy used in §F), the "pass flat" finding from the base investigation.

### Updated verdict

No change to the base investigation's verdict — this addendum adds direct confirmation where the base investigation could only proxy:

| Model | loss↓ | ‖B‖ grows | outputs differ (now: literal, not just proxy) | pass flat (now: paired McNemar) | **Verdict** |
|---|---|---|---|---|---|
| 1.5B | ✅ | ✅ | ✅ 82.4% token-identical to own targets, real diffs on the rest | ✅ paired p=0.38/0.82 | **Strongest control — memorisation of a partly-incorrect training set, not an eval bug** |
| 7B | ✅ | ✅ | ✅ 98.7% token-identical to own targets, real diffs on the rest | ✅ paired p=0.59/0.66 | **Strongest control — memorisation of a partly-incorrect training set, not an eval bug** |

### Files under `analysis/derived/`

- `inst1_control_epoch30_generation_{qwen1_5b,qwen7b}.jsonl` — raw per-problem generations (450 rows each: 3 instantiations × 150 problems), including `raw_response`, `extracted_test_file`, `sanitized_test_file`, `exec_ok`, `baseline_passed`, `adapter_path`, `adapter_weights_hash`.
- `inst1_control_epoch30_{qwen1_5b,qwen7b}_vs_training_target.csv` — per-problem token-identity/edit-distance comparison (seen only).
- `inst1_control_epoch30_{qwen1_5b,qwen7b}_mcnemar.csv` — paired McNemar summary tables.
