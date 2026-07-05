#!/bin/bash --norc
#SBATCH --job-name=finetune-7b
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:3g.40gb:1      # 40GB MIG slice — fits 7B LoRA (~16GB peak)
#SBATCH --time=04:00:00            # 3 epochs × ~149 examples × gradient checkpointing ≈ 1–2h
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=/mnt/scratch2/users/%u/dissertation/logs/%x-%j.out
#SBATCH --error=/mnt/scratch2/users/%u/dissertation/logs/%x-%j.err

set -euo pipefail
unset BASH_ENV

export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false

PROGRESS="/mnt/scratch2/users/${USER}/dissertation/logs/progress_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$PROGRESS")"
_log() { echo "[$(date -u +%FT%TZ)] $*" >> "$PROGRESS"; }
trap '_log "script exiting (exit=$?)"' EXIT

_log "starting on $(hostname)"
cd /mnt/scratch2/users/${USER}/dissertation
source .venv/bin/activate
_log "venv activated — $(python --version 2>&1)"

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "GPU:     $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
echo "Started: $(date -u +%FT%TZ)"
echo

_log "preparing training data"
python scripts/prepare_finetune_data.py
_log "training data ready"

_log "starting fine-tuning"
python scripts/finetune_qwen7b.py --config configs/finetune_qwen7b_inst1.yaml
_log "fine-tuning complete"

echo
echo "Finished: $(date -u +%FT%TZ)"
