#!/bin/bash --norc
#SBATCH --job-name=l1l2-pilot
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:2g.20gb:1          # one MIG slice (20 GB VRAM)
#SBATCH --time=03:00:00               # 150 problems × ~30s each ≈ 75 min + generous buffer
#SBATCH --mem=64G                     # was 32G; 12 OOM kills from subprocess fork spike
#SBATCH --cpus-per-task=4             # must match mutation_workers in the config
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

CONFIG="${CONFIG:-configs/qwen_coder_1_5b__dynamic_L1L2.yaml}"

# Set HF cache explicitly — do not rely on .bashrc which SLURM may not source.
export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"

# Prevent HuggingFace from making ANY network requests to hub.huggingface.co.
# Kelvin2 compute nodes drop outbound TCP silently (no RST), so any hub check
# hangs for the full TCP keepalive period (~2h) before failing.
# Model must already be in HF_HUB_CACHE — see CLAUDE.md "Pin model versions".
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Flush Python stdout/stderr immediately so output is not lost if the job is
# killed at the wall-clock limit.
export PYTHONUNBUFFERED=1

# Progress file: written by shell (not Python), visible in near real-time from
# the login node even while the job is running (bypasses SLURM stdout buffering).
PROGRESS="/mnt/scratch2/users/${USER}/dissertation/logs/progress_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$PROGRESS")"

_log() { echo "[$(date -u +%FT%TZ)] $*" >> "$PROGRESS"; }
trap '_log "script exiting (exit=$?)"' EXIT

_log "skipping modules (uv-managed Python + bundled CUDA)"

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
# Pipe stdout through tee so every print() lands in the progress file
# immediately (PYTHONUNBUFFERED=1 ensures each line is flushed at once).
# Stderr is left on SLURM's .err channel (already written in near real-time).
python scripts/run_eval.py --config "$CONFIG" | tee -a "$PROGRESS"
_log "python exited cleanly"

echo
echo "Finished: $(date -u +%FT%TZ)"
