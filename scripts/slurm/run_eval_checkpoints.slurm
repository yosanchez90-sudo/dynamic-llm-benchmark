#!/bin/bash --norc
#SBATCH --job-name=eval-ckpts
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:3g.40gb:1       # base model stays in GPU; adapters are tiny
#SBATCH --time=10:00:00            # 8 checkpoints × 3 insts × ~15 min = ~6 h for 7B
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=/mnt/scratch2/users/%u/dissertation/logs/%x-%j.out
#SBATCH --error=/mnt/scratch2/users/%u/dissertation/logs/%x-%j.err

set -euo pipefail
unset BASH_ENV

# Required: CONFIG — path to finetune YAML, e.g. configs/finetune_qwen7b_inst1_30ep.yaml
# Optional: EPOCHS — space-separated list, defaults to "1 3 5 10 15 20 25 30"
# Optional: OUT    — output CSV path, defaults to data/results/finetune_rebuild/epoch_perf_<name>.csv
# Optional: BASELINE — set to "1" to also score epoch 0 (no adapter)
# Optional: SAMPLING_SEEDS — space-separated seeds for extra sampling draws, e.g. "42 43 44"
# Optional: GREEDY — set to "0" to skip the greedy draw (default: on)
CONFIG="${CONFIG:?CONFIG variable required}"
EPOCHS="${EPOCHS:-1 3 5 10 15 20 25 30}"
BASELINE="${BASELINE:-0}"
SAMPLING_SEEDS="${SAMPLING_SEEDS:-}"
GREEDY="${GREEDY:-1}"

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
_log "venv activated"

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Config:  $CONFIG"
echo "Epochs:  $EPOCHS"
echo "GPU:     $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
echo "Started: $(date -u +%FT%TZ)"
echo

BASELINE_FLAG=""
if [[ "$BASELINE" == "1" ]]; then
    BASELINE_FLAG="--baseline"
fi

GREEDY_FLAG="--greedy"
if [[ "$GREEDY" == "0" ]]; then
    GREEDY_FLAG="--no-greedy"
fi

SAMPLING_FLAG=""
if [[ -n "$SAMPLING_SEEDS" ]]; then
    SAMPLING_FLAG="--sampling-seeds $SAMPLING_SEEDS"
fi

_log "starting checkpoint evaluation"
python scripts/eval_checkpoints.py \
    --config "$CONFIG" \
    --epochs $EPOCHS \
    --instantiations 1 2 3 \
    $BASELINE_FLAG $GREEDY_FLAG $SAMPLING_FLAG

_log "checkpoint evaluation complete"
echo "Finished: $(date -u +%FT%TZ)"
