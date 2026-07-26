#!/bin/bash --norc
#SBATCH --job-name=eval-qwen1.5b-v100
#SBATCH --partition=k2-gpu-v100
#SBATCH --gres=gpu:v100:1
#SBATCH --time=07:00:00               # measured live: V100 ~50s/problem (~2x slower than PRE's a100mig
                                       # run) -- 400 problems * 50s ~= 5.5h; buffer for variance/resume
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4             # must match mutation_workers in the config; V100 nodes have 48 CPUs total
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

CONFIG="${CONFIG:?Set CONFIG=configs/....yaml}"

# k2-gpu-a100mig (gpu114, the only node) was heavily congested with another
# user's queue at submission time -- v100 has 8 nodes and was the documented
# fallback (CLAUDE.md). A 1.5B model + LoRA adapter fits V100 32GB trivially
# (CLAUDE.md notes it fits 7B LoRA with gradient checkpointing).
export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1

# Job 9490463 OOM'd on the first post-resume problem: "22.00 GiB allocated,
# 7.48 GiB reserved but unallocated" -- a fragmentation pattern (PyTorch's own
# suggested fix), not simply "the model doesn't fit". Some ULT `code` blobs
# are very long (see scripts/finalize_ult_training_set.py's note on ~116k-token
# outliers in the training set) and this is core_400 (fixed eval set, must stay
# identical to what PRE already measured) so problems can't be dropped here.
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
echo "Config:  $CONFIG"
echo "HF_HOME: $HF_HOME"
echo "Started: $(date -u +%FT%TZ)"
echo

nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader | tee -a "$PROGRESS"

_log "launching python"
python scripts/run_eval.py --config "$CONFIG" | tee -a "$PROGRESS"
_log "python exited cleanly"

echo
echo "Finished: $(date -u +%FT%TZ)"
