# Project context for Claude Code

## What this project is
Dissertation evaluating <N> LLMs on <task>, plus a contamination-simulation
experiment fine-tuning a small open-source model on perturbed benchmark data.

## Hard rules
- Never call frontier APIs from a script that hasn't been reviewed for cost.
- Never run compute on the login node. All GPU/CPU work goes through SLURM.
- Every model call must log: model name, snapshot/revision, decoding params, seed, timestamp.
- Pin model versions exactly (e.g. `claude-opus-4-7`, HF revision SHA). Never use `-latest` tags.
- HuggingFace cache lives on scratch, not home (set HF_HOME accordingly).

## Layout
- `src/` library code
- `configs/` experiment configs (Hydra/YAML)
- `scripts/slurm/` job submission scripts
- `data/results/` JSONL outputs, never overwritten

## Conventions
- Python 3.11, managed by uv.
- Type hints everywhere.
- Tests in `tests/`, run with `pytest`.

## Kelvin2 partition rules
- Interactive sessions (`srun --pty`) → ONLY `k2-gpu-interactive`.
- Batch jobs (`sbatch`) → GPU-type-specific partitions
  (`k2-gpu-v100`, `k2-gpu-a100`, `k2-gpu-a100mig`, `k2-gpu-h100`, `k2-gpu-amd`).
- Check available GRES with: `sinfo -p <partition> -o "%n %G"`