#!/bin/bash --norc
#SBATCH --job-name=l1l2-7b
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:3g.40gb:1          # 40 GB MIG slice for 7B (~15 GB weights)
#SBATCH --time=06:00:00               # 150 problems × ~60s each ≈ 2.5h + buffer
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4             # must match mutation_workers in config
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

CONFIG="${CONFIG:-configs/qwen_coder_7b__dynamic_L1L2.yaml}"

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
