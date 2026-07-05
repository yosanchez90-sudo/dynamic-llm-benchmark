#!/bin/bash --norc
#SBATCH --job-name=l1l2-32b
#SBATCH --partition=k2-gpu-a100
#SBATCH --gres=gpu:a100:1             # full 80 GB A100 for 32B (~65 GB weights)
#SBATCH --time=08:00:00               # 150 problems × ~90s each ≈ 3.75h + buffer
#SBATCH --mem=128G
#SBATCH --cpus-per-task=8             # must match mutation_workers in config
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

CONFIG="${CONFIG:-configs/qwen_coder_32b__dynamic_L1L2.yaml}"

export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1

PROGRESS="/mnt/scratch2/users/${USER}/dissertation/logs/progress_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$PROGRESS")"
_log() { echo "[$(date -u +%FT%TZ)] $*" >> "$PROGRESS"; }
trap '_log "script exiting (exit=$?)"' EXIT

_log "starting on $(hostname)"
cd /mnt/scratch2/users/${USER}/dissertation
_log "cd done"

source .venv/bin/activate
_log "venv activated — $(python --version 2>&1)"

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Config:  $CONFIG"
echo "HF_HOME: $HF_HOME"
echo "Started: $(date -u +%FT%TZ)"
echo

_log "checking GPU..."
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader | tee -a "$PROGRESS"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

_log "launching python"
python scripts/run_eval.py --config "$CONFIG" | tee -a "$PROGRESS"
_log "python exited cleanly"

echo
echo "Finished: $(date -u +%FT%TZ)"
