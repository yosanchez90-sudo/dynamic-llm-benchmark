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
- HuggingFace cache lives on scratch, not home (set HF_HOME accordingly).
- Documentation and manifest files under `data/` are force-added (`git add -f`) —
  the blanket `/data/` gitignore (generated batches/checkpoints/results) does not
  exempt provenance docs. Applies to `data/raw/ult_plt/PROVENANCE.md` and to
  `data/raw/ult_plt/subsample_manifest.json` when it's created.

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