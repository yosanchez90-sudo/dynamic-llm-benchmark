#!/bin/bash --norc
#SBATCH --job-name=onset-curve
#SBATCH --partition=k2-gpu-v100
#SBATCH --gres=gpu:v100:1
#SBATCH --time=06:00:00               # estimate ~4.5h (875 generations at measured rates); buffer
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1
# Same fragmentation fix as Stage 3a/3b (job 9490463's OOM) -- long ULT
# prompts + repeated model/adapter reloads across 5 epochs.
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

PROGRESS="/mnt/scratch2/users/${USER}/dissertation/logs/progress_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$PROGRESS")"
_log() { echo "[$(date -u +%FT%TZ)] $*" >> "$PROGRESS"; }
trap '_log "script exiting (exit=$?)"' EXIT

cd /mnt/scratch2/users/${USER}/dissertation
_log "cd done"

source .venv/bin/activate
_log "venv activated — $(python --version 2>&1)"

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "GPU:     $(nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader)"
echo "Started: $(date -u +%FT%TZ)"
echo

_log "launching python"
python scripts/run_onset_curve.py | tee -a "$PROGRESS"
_log "python exited cleanly"

echo
echo "Finished: $(date -u +%FT%TZ)"
