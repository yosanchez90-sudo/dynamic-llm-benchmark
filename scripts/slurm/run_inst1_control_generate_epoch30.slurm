#!/bin/bash --norc
#SBATCH --job-name=inst1-ctrl-gen30
#SBATCH --partition=k2-gpu-v100
#SBATCH --gres=gpu:v100:1
#SBATCH --time=05:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --output=/mnt/scratch2/users/%u/dissertation/logs/%x-%j.out
#SBATCH --error=/mnt/scratch2/users/%u/dissertation/logs/%x-%j.err

# One-off inference pass for the inst1-control investigation addendum --
# see analysis/inst1_control_generate_epoch30.py and
# analysis/reports/inst1_control_verification.md. Single checkpoint
# (epoch 30), 3 instantiations x 150 problems = 450 generations. First
# attempt (jobs 9389597/9389598) measured ~3.4-3.8 problems/min on V100,
# i.e. ~2-2.2h for a full run, not the ~20min originally guessed -- 5h
# budgeted here for real margin. The script now writes each record
# immediately and resumes from --out on restart, so even a job that does
# hit this limit only loses in-flight work, not everything already scored.

set -euo pipefail
unset BASH_ENV

CONFIG="${CONFIG:?CONFIG required (e.g. configs/finetune_qwen1_5b_inst1_30ep.yaml)}"
OUT="${OUT:?OUT required (e.g. analysis/derived/inst1_control_epoch30_generation_qwen1_5b.jsonl)}"
EPOCH="${EPOCH:-30}"

export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false

PROGRESS="/mnt/scratch2/users/${USER}/dissertation/logs/progress_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$PROGRESS")"
_log() { echo "[$(date -u +%FT%TZ)] $*" >> "$PROGRESS"; }
trap '_log "script exiting (exit=$?)"' EXIT

_log "starting on $(hostname) — config=$CONFIG epoch=$EPOCH out=$OUT"
cd /mnt/scratch2/users/${USER}/dissertation
source .venv/bin/activate

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "GPU:     $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
echo "Config:  $CONFIG"
echo "Epoch:   $EPOCH"
echo "Out:     $OUT"
echo "Started: $(date -u +%FT%TZ)"
echo

python analysis/inst1_control_generate_epoch30.py \
    --config "$CONFIG" \
    --epoch "$EPOCH" \
    --out "$OUT" \
    | tee -a "$PROGRESS"

echo "Finished: $(date -u +%FT%TZ)"
