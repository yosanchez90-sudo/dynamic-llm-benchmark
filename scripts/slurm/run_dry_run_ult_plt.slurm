#!/bin/bash --norc
#SBATCH --job-name=dry-run-ult-plt
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:2g.20gb:1          # one MIG slice (20 GB VRAM) — Qwen 1.5B
#SBATCH --time=00:30:00               # 10 problems total, generous buffer
#SBATCH --mem=32G
#SBATCH --cpus-per-task=2             # must match mutation_workers in the configs
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1

PROGRESS="/mnt/scratch2/users/${USER}/dissertation/logs/progress_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$PROGRESS")"
_log() { echo "[$(date -u +%FT%TZ)] $*" >> "$PROGRESS"; }
trap '_log "script exiting (exit=$?)"' EXIT

cd /mnt/scratch2/users/${USER}/dissertation
_log "cd done"

source .venv/bin/activate
_log "venv activated — $(python --version 2>&1)"

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Started: $(date -u +%FT%TZ)"
echo

_log "checking GPU..."
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader | tee -a "$PROGRESS"

_log "launching ULT dry run"
echo "=== ULT dry run (5 problems) ==="
python scripts/run_eval.py --config configs/dry_run_ult_qwen1_5b.yaml | tee -a "$PROGRESS"

_log "launching PLT dry run"
echo
echo "=== PLT dry run (5 problems) ==="
python scripts/run_eval.py --config configs/dry_run_plt_qwen1_5b.yaml | tee -a "$PROGRESS"

_log "python exited cleanly"
echo
echo "Finished: $(date -u +%FT%TZ)"
