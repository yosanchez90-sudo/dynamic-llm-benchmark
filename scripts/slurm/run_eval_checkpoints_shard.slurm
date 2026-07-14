#!/bin/bash --norc
#SBATCH --job-name=eval-ckpts-shard
#SBATCH --partition=k2-gpu-v100
#SBATCH --gres=gpu:v100:1
#SBATCH --time=08:00:00
#SBATCH --mem=32G
# NOTE: submit_epoch_curve_shards.py normally overrides this per-shard via
# `sbatch --mem=...` (CLI args win over #SBATCH pragmas) — see that script's
# _mem_for(): a flat mem request regardless of model size/condition
# OOM-killed 3 of the first 66 shards (all bp_gpt5, the long-output
# condition). This 32G is only the fallback for a direct/manual sbatch of
# this file, sized to the smaller (1.5B fast) case, not the 7B/bp_gpt5 ones.
#SBATCH --cpus-per-task=4
#SBATCH --output=/mnt/scratch2/users/%u/dissertation/logs/%x-%j.out
#SBATCH --error=/mnt/scratch2/users/%u/dissertation/logs/%x-%j.err

set -euo pipefail
unset BASH_ENV

CONFIG="${CONFIG:?CONFIG required}"
EPOCH="${EPOCH:?EPOCH required}"
OUT="${OUT:?OUT required}"
GREEDY_FLAG="${GREEDY_FLAG:---greedy}"
SAMPLING_FLAG="${SAMPLING_FLAG:-}"
BASELINE_FLAG="${BASELINE_FLAG:-}"

export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false

PROGRESS="/mnt/scratch2/users/${USER}/dissertation/logs/progress_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$PROGRESS")"
_log() { echo "[$(date -u +%FT%TZ)] $*" >> "$PROGRESS"; }
trap '_log "script exiting (exit=$?)"' EXIT

_log "starting on $(hostname) — config=$CONFIG epoch=$EPOCH"
cd /mnt/scratch2/users/${USER}/dissertation
source .venv/bin/activate

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "GPU:     $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
echo "Config:  $CONFIG"
echo "Epoch:   $EPOCH"
echo "Out:     $OUT"
echo "Started: $(date -u +%FT%TZ)"
echo

python scripts/eval_checkpoints.py \
    --config "$CONFIG" \
    --epochs $EPOCH \
    --instantiations 1 2 3 \
    --out "$OUT" \
    $GREEDY_FLAG $SAMPLING_FLAG $BASELINE_FLAG \
    | tee -a "$PROGRESS"

echo "Finished: $(date -u +%FT%TZ)"
