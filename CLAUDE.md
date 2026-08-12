# Project context for Claude Code

## What this project is
Dissertation evaluating <N> LLMs on <task>, plus a contamination-simulation
experiment fine-tuning a small open-source model on perturbed benchmark data.

## Hard rules
- Never call frontier APIs from a script that hasn't been reviewed for cost.
- Never run compute on the login node. All GPU/CPU work goes through SLURM.
- Every model call must log: model name, snapshot/revision, decoding params, seed, timestamp.
  Adapter identity (path + hash) is part of model identity — a LoRA-adapted model is a
  different model than its base checkpoint even though model/model_revision are identical.
  Resolved generation config (do_sample, temperature, repetition_penalty incl. inherited
  values and their source, no_repeat_ngram_size, max_new_tokens) is part of run identity —
  an unlogged inherited default (e.g. from a base model's generation_config.json) can
  silently differ between runs and change results without any code or YAML diff to show it.
- Pin model versions exactly (e.g. `claude-opus-4-7`, HF revision SHA). Never use `-latest` tags.
- **Every hand-written number in `analysis/*.md` (and, once it holds prose,
  `paper/`) must either verify against a live, auto-regenerated provenance
  source, or carry an explicit historical/external marker.** Enforced by
  `scripts/check_doc_citations.py`, registered as a gating step in
  `scripts/build_thesis_assets.py` (nonzero exit on any unsuppressed
  mismatch). A number that is deliberately superseded (a correction-history
  entry, a "was X, now Y" construction) or genuinely external (no repo
  counterpart — a paper's own reported figure, a leaderboard score) must be
  marked so, not left to silently fail the gate: an inline `<!-- cite:historical -->`
  / `<!-- cite:external -->` comment (or a `:start`/`:end` pair around a
  multi-line span), or an entry in `analysis/CITATION_ALLOWLIST.md` keyed on
  file+line+kind+value with a one-line reason. Never suppress a finding by
  adding a marker/allowlist entry without first checking whether the number
  is actually still correct — the point of the gate is that a hand-typed
  figure drifts from the pipeline silently otherwise (confirmed repeatedly,
  2026-08-12: RQ5_INTERPRETATION.md's tier-matched Dynamic-L4↔ULT reading
  had actually flipped sign, not just drifted, after Gemini Pro Preview's
  L4 crawl completed — a plain diff would not have caught this, only
  re-deriving the number from live data did).
- **`scripts/process_batch.py`'s `cost_usd` never applied OpenAI's 50% Batch
  API discount** (found 2026-08-07) — `compute_cost()` (`src/pricing.py`)
  only knows the standard real-time rate; every row this script has ever
  scored (100% of them are batch-derived, that's the script's whole job)
  logged exactly 2x the real billed cost. Confirmed by exact arithmetic
  match (a real row's `cost_usd=0.0314625` reproduces precisely from
  `154*1.25 + 3127*10.00` over 1e6 — the *standard*, not batch, rate) and
  cross-checked against this pass's own independent cost estimate
  (`analysis/OPENAI_COST_AND_BILLING.md`'s $39-60 band, computed from
  exact token counts and the batch rate directly, never from logged
  `cost_usd`): halving the logged total landed within $1.68 of the
  estimate's midpoint. Fixed going forward (`process_batch.py` now
  multiplies by 0.5); **not corrected retroactively** in the ~4,600
  already-written GPT-5/-mini rows (logged sum $127.51, real ~$63.76) —
  same policy as the gpt-5.4 pricing-table bug found earlier this pass:
  `cost_usd` is a logged-at-the-time field, not silently rewritten.
  Anything that sums `cost_usd` across these rows (e.g.
  `scripts/estimate_cost.py`'s "prefer real logged cost over a token
  proxy" path) is reading a number 2x too high until/unless those rows
  are ever migrated.
- **`src/models/gemini_model.py`'s `cost_usd` never counted Gemini's
  "thinking" tokens** (found 2026-08-08) — `gemini-3.1-pro-preview` is a
  thinking-enabled model; the SDK's `usage_metadata.thoughts_token_count`
  (internal reasoning tokens, billed separately from the visible response
  at the same output-token rate, per ai.google.dev/gemini-api/docs/pricing)
  was never read; only `candidates_token_count` (the visible response) fed
  `compute_cost()`. Found by reconciling this project's own logged
  `cost_usd` sum across every Gemini row (dynamic+ULT+PLT, both models:
  $11.88 real logged) against Google AI Studio's actual billed total for
  the same window (Jul 11 - Aug 7: £34.53, ≈$44) — a ~4x gap far too large
  for FX/rounding, confirmed structurally by reading the SDK's
  `GenerateContentResponseUsageMetadata` type definition directly (it has
  a `thoughts_token_count` field this project's code simply never
  accessed). Fixed going forward (`gemini_model.py` now adds
  `thoughts_token_count` into the cost calculation, and logs it separately
  in `runtime_info` for audit — `output_tokens` itself is left meaning
  "visible response tokens" for comparability with non-thinking
  providers). Regression tests added (`tests/test_gemini_model.py`).
  **Not corrected retroactively** in the ~800 already-written
  gemini-3.1-pro-preview rows — same policy as every other `cost_usd`
  bug above: it's a logged-at-the-time field. Real spend for finishing the
  Gemini Pro Preview Dynamic-L4 crawl (`analysis/GEMINI_DAILY_CRAWL.md`)
  should be estimated from the AI Studio dashboard's actual per-model
  spend, not from this project's own pre-fix `cost_usd` sums, which
  undercounted Pro Preview specifically by roughly 4x.
- **Permanent backup**: `/users/40492566/dissertation_backups/20260812_preflight`
  (home filesystem, not scratch — scratch is purged after 3 months of
  inactivity, home is not). Created 2026-08-12 as a write-up-phase
  pre-flight item. Contents: all 8 LoRA adapter final checkpoints
  (`data/finetune/*/adapter_final`, 3.7G — deliberately excludes the much
  larger per-run training-checkpoint/optimizer-state trees, 26-56G each,
  not needed for reproducing any reported result), the full `data/results/`
  and `data/batches/` trees, the three `data/raw/ult_plt/*manifest*.json`
  files plus `data/results/finetune_rebuild/shards/manifests/*.csv`, and
  the full `analysis/` tree (151 files). Total 3.9G. Verified 2026-08-12:
  file counts match source exactly for every category (256/256 results,
  41/41 batches, 151/151 analysis, 80/80 adapter files); checksums spot-
  checked on 3 random files, all identical. Excludes base-model weights
  and raw JSONL result files' own git-tracked provenance/interpretation
  siblings (already in git history, not scratch-only). Not automated —
  a one-off snapshot; re-run manually before any future action that could
  touch these paths destructively.
- HuggingFace cache lives on scratch, not home (set HF_HOME accordingly).
- Documentation and manifest files under `data/` are force-added (`git add -f`) —
  the blanket `/data/` gitignore (generated batches/checkpoints/results) does not
  exempt provenance docs. Applies to `data/raw/ult_plt/PROVENANCE.md` and to
  `data/raw/ult_plt/subsample_manifest.json` when it's created.
- Never `exec()`/`eval()` vendored or scraped code (ULT/PLT `code` blobs, any
  third-party sample) with the working directory left at the repo root — some
  real-world functions do relative-path file I/O as a normal side effect.
  Confirmed 2026-07-25: a ULT ground-truth-quality check that exec'd ~3,676
  scraped functions with cwd at the repo root littered it with `fort.*`,
  `moldyn.vel`, `control`, `exe`-style debris. Always `os.chdir()` into a
  fresh `tempfile.mkdtemp()` (or run in a `subprocess` with `cwd=` set) before
  executing untrusted code, and restore/clean up afterward.
- One writing session per working tree. If you need a second concurrent
  Claude Code session on this project, use `git worktree` for it rather than
  pointing another session at this same checkout — two sessions committing to
  the same tree can otherwise look indistinguishable from an external/
  unauthorized change (see the 2026-07-25/26 session-reconciliation incident:
  benign, but cost real time to verify).
- `src/eval/test_gen_runner.py`'s resume-file matcher (`_find_resume_file`)
  keys output filenames on tier set now (`_tier_signature`, e.g. `L1L2` vs
  `L3L4`), not just model/benchmark/instantiation. Never submit two
  Dynamic-benchmark configs for the same (model, instantiation) with
  overlapping runtimes unless their `tiers` differ and this fix is in place —
  confirmed via real job logs (2026-07-14/23/24, claude-haiku-4-5 inst4) that
  the pre-fix matcher let an L1L2 retry job resume into an L3L4 job's output
  file (and vice versa), producing duplicate — sometimes content-conflicting
  — rows for the same (template_id, instance_seed). No rows were lost
  (coverage_matrix.py's set-based check showed every in-scope cell complete)
  and `src/Analysis/loader.py`'s timestamp-based dedup already resolves it
  for analysis, but don't rely on that as the primary defense — the matcher
  fix (`tests/test_gen_runner_resume.py`) is. If submitting several configs
  for the same (model, instantiation) that legitimately can't be
  tier-disambiguated (e.g. two configs with identical `tiers`), sequence them
  with `sbatch --dependency=afterok:<jobid>` instead of submitting
  concurrently.
  **Addendum, confirmed 2026-08-06**: the fix was never applied
  retroactively to files that already existed when it landed — every
  Claude Sonnet/Haiku Dynamic result file from 2026-07-14 (all
  instantiations, not just inst5) has no `__tiers` tag in its filename at
  all, so `_find_resume_file`'s glob (which requires a tier-tag match)
  cannot find them. Currently harmless for instantiations 1-4 (already
  100% complete, nothing to resume into), but confirmed actively harmful
  for a genuinely partial one: re-running Claude Sonnet/Haiku's inst5
  L1L2/L3L4 configs to complete a partial sample (135/300 and 143/300)
  found *zero* matching resume file, restarted from scratch, and burned
  222 real, fully-duplicate API calls (~$2.65, real logged `cost_usd`)
  before this was caught and the run cancelled — confirmed via exact
  `(template_id, instance_seed)` overlap with the pre-existing data, not
  guessed. Fixed for inst5 by migrating the three affected legacy files
  into the tagged naming convention (split-by-tier for Sonnet's single
  combined file, straight rename for Haiku's already-tier-pure pair,
  original un-tagged files moved to
  `data/results/dynamic/migrated_20260806_pre_tier_signature_legacy_originals/`,
  not deleted). **Not done for instantiations 1-4** (no active need, and
  bulk-migrating every historical file across every model was out of
  scope for the pass that found this) — if any of those ever need a
  genuine resume in the future, check for a same-shaped un-tagged legacy
  file first, or this same waste will repeat.
  **RESOLVED 2026-08-06**: after the fix, the actual completion re-run
  correctly resumed (skipped exactly 93/42/80/63 already-done problems per
  config, matching the migrated files precisely) and Claude Sonnet/Haiku
  inst5 are now both **fully complete, 300/300, all four tiers**. Real
  cost: $0.8498 + $2.8448 (Sonnet L1L2/L3L4) + $0.3988 + $0.8226 (Haiku
  L1L2/L3L4) = **$4.92 for the legitimate completion** (matching the
  original estimate almost exactly), **+ $2.65 wasted on the cancelled
  duplicate run = $7.57 total** — still well under the $15 gate this work
  was authorized under, but the overrun is 100% attributable to the
  legacy-file gap above, not to the original cost estimate being wrong.
  **RECURRED 2026-08-11, this time for Gemini Pro Preview, real money**:
  the same un-tagged-legacy-file gap this entry already warned about
  ("if any of those ever need a genuine resume in the future, check for a
  same-shaped un-tagged legacy file first, or this same waste will
  repeat") repeated exactly as predicted — nobody checked first. Gemini's
  Dynamic-benchmark daily crawl (`analysis/GEMINI_DAILY_CRAWL.md`) had
  pre-fix legacy files for instantiations 1/2/3/4 (from 2026-07-14/23,
  before the tier-signature fix), each holding real L1/L2/L3 data with no
  `__tiers` tag. When the crawl's L1L2 configs finally ran (2026-08-10,
  during a paid, credit-limited "finish it now" push, `analysis/
  GEMINI_DAILY_CRAWL.md`/billing context), `_find_resume_file` found none
  of them and regenerated from scratch — **inst1: 150/150 rows 100%
  duplicate ($3.2684 wasted), inst2: 103/150 rows duplicate ($2.5186
  wasted), inst3: 51/51 rows 100% duplicate ($1.3955 wasted) — $7.18
  wasted total**, discovered only because the coverage-checker's "missing"
  count stayed suspiciously flat across an inst3 L1L2 run that should have
  moved it. inst4's legacy file was caught and migrated **before** any job
  touched it (0 wasted there). Root cause identical to the 2026-08-06
  incident: this project has never bulk-migrated every historical
  pre-tier-signature file, only ever the ones directly in a given pass's
  path, so any *other* un-migrated model/instantiation remains a live
  trap. Fixed the same way: legacy files split by tier where mixed
  (`inst{1,2,3,4}__2026071/23*.jsonl` each held L1[/L2]+L3 — the L3
  portion was independently verified already fully subsumed by the
  existing `__tiersL3L4__` files before touching anything, via exact
  `(template_id, instance_seed)` set overlap, not assumed), wasted
  duplicate rows quarantined (inst2 required a genuine merge — 47 of its
  150 rows were real new data alongside 103 duplicates, kept via set
  difference against the legacy pairs, verified for zero internal
  collisions before writing), legacy originals archived, everything
  re-verified via a direct `_find_resume_file` call per instantiation
  (not just eyeballing filenames) and via `check_gemini_pro_crawl_done.py`
  reporting the identical missing-count (172) before and after — confirms
  no coverage was gained or lost, only wasted spend surfaced. **Standing
  rule this project needs and doesn't yet have**: before running *any*
  resumable job against a model/instantiation that has result files
  older than the tier-signature fix (2026-07-26), grep for a same-shaped
  un-tagged file first — this has now cost real money twice from the
  identical, already-documented cause.
- **Library fallbacks must raise, not approximate.** Never write
  `try: import real_lib; HAVE_X = True; except ImportError: HAVE_X = False`
  and then silently substitute a cruder approximation when `HAVE_X` is
  False. Use `template_corpus/templates/_smoke/validation_helpers.py`'s
  `require_library()` (or the equivalent for non-smoke-test code) so a
  missing dependency fails loudly at import time instead of quietly
  changing which metric a script actually computes. Confirmed 2026-07-14:
  `diversity_v2.py`'s `bleu4()` fell back to a 4-gram Jaccard approximation
  whenever `sacrebleu` wasn't installed (it was never a declared
  dependency until commit `d16f122`) — every within-tier diversity run
  before that date used the fallback, not real BLEU-4, with only a
  `print()` line (not an exception, not a persisted field in the output
  JSON) distinguishing which metric had actually run. Also: any validation/
  audit/sweep script's main loop must fail loudly if it checked zero
  items (`validation_helpers.assert_checked`) — a validator that iterates
  zero times and reports "0 failed" is, from its own output alone,
  indistinguishable from one that checked everything and found no
  problems (this is exactly the shape of the `validate.py` stale-path bug,
  2026-07-13, commit `2d5fc9d`, and of `archive_diversity_audit.py`'s
  hardcoded README summary, found and fixed 2026-08-03 — see
  `analysis/VALIDATOR_SWEEP.md`).

## Layout
- `src/` library code
- `configs/` experiment configs (Hydra/YAML)
- `scripts/slurm/` job submission scripts
- `data/results/` JSONL outputs, never overwritten

## Conventions
- Python 3.11, managed by uv.
- Type hints everywhere.
- Tests in `tests/`, run with `pytest`.

## Kelvin2: running jobs

### Two execution modes
| Mode | Command | Partition |
|------|---------|-----------|
| Interactive shell | `srun --pty ...` | `k2-gpu-interactive` **only** |
| Batch (unattended) | `sbatch script.slurm` | GPU-type-specific (see below) |

Interactive sessions die if your SSH drops — only use them for quick tests/debugging
(≤1 h). For anything longer, always use `sbatch`.

Always prefix sbatch with `env -u BASH_ENV sbatch` to avoid BASH_ENV hook conflicts.

### GPU partitions for batch jobs (all have a 3-day time limit)

| Partition | Hardware | GRES token | VRAM | Nodes | Best for |
|-----------|----------|------------|------|-------|----------|
| `k2-gpu-a100mig` | A100 80GB (MIG slices) | `gpu:3g.40gb:1` | 40 GB | 1 (gpu114) | **Default** for 1.5B/7B LoRA; only 1 node so can queue |
| `k2-gpu-a100mig` | A100 80GB (smaller MIG) | `gpu:2g.20gb:1` | 20 GB | 1 (gpu114) | Inference-only for small models |
| `k2-gpu-v100` | V100 32GB | `gpu:v100:1` | 32 GB | **8** (gpu103-110) | Good fallback when MIG is busy; 8 nodes = shorter queues; fits 7B LoRA |
| `k2-gpu-a100` | A100 80GB (full card) | `gpu:a100:1` | 80 GB | 3 (gpu111-113) | 32B+ fine-tuning; full card needed when MIG VRAM isn't enough |
| `k2-gpu-h100` | H100 80GB | `gpu:h100:1` | 80 GB | 1 (gpu121) | Fastest compute; good for long inference runs; only 1 node |
| `k2-gpu-amd` | AMD MI300X | `gpu:mi300x:1` | — | 1 (gpu123) | Experimental; ROCm only |
| `k2-gpu-intel` | Intel Max 1100 | `gpu:i1100:1` | — | 1 (gpu122) | Experimental; XPU only |

EPSRC-allocated variants (`k2-epsrc-gpu-v100`, `k2-epsrc-gpu-a100`, etc.) exist for
funded projects — check with supervisor if access is available; they typically have
shorter queues.

### Choosing the right partition
- **Jobs stuck in PD (pending)?** Check if the queue is congested:
  `squeue -p k2-gpu-a100mig` — if many jobs are waiting, try `k2-gpu-v100` instead
  (8 nodes, almost always shorter queue).
- **7B LoRA fine-tune / eval:** `k2-gpu-a100mig` (3g.40gb) is ideal; `k2-gpu-v100`
  is a reliable fallback (32GB fits 7B LoRA with gradient checkpointing).
- **1.5B fine-tune / eval:** `k2-gpu-a100mig` (2g.20gb) or `k2-gpu-v100`.
- **32B fine-tune:** must use `k2-gpu-a100` or `k2-gpu-h100` (full 80GB card).
- **Quick interactive test:** `srun --pty -p k2-gpu-interactive --gres=gpu:3g.40gb:1 --mem=32G --time=1:00:00 bash`

### Scheduling tips
- No QOS or --account priority flags are documented — partition choice is the only
  lever. Requesting fewer resources (cores, RAM, time) lets the scheduler backfill
  your job into gaps faster.
- Check node availability: `sinfo -p <partition> -o "%n %G %T"`
- Check your jobs: `squeue -u $USER`
- Job accounting after completion: `sacct -j <jobid> --format="JobID,Elapsed,ReqMem,MaxVMSize"`

### Storage
| Location | Quota | Notes |
|----------|-------|-------|
| `/users/$USER` (home) | 50 GB / 100K files | Long-term, small files only |
| `/mnt/scratch2/users/$USER` | No quota | Primary workspace; purged if inactive >3 months |
| `/tmp` | Node-local | Deleted when job ends |

Always set `HF_HOME=/mnt/scratch2/users/$USER/.huggingface` — HF cache is large and
will blow the home quota.