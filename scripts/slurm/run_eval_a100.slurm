#!/bin/bash --norc
# Full A100 job: use for Qwen 32B (needs full 80 GB VRAM).
# gpu111-113: 4× A100 SXM4 80GB, 128 CPU cores, 1 TiB RAM.
# Time limit on k2-gpu-a100: 3 days.
#SBATCH --job-name=eval-a100
#SBATCH --partition=k2-gpu-a100
#SBATCH --gres=gpu:a100:1
#SBATCH --time=08:00:00               # 3-day wall limit available; 8h is safe for 32B
#SBATCH --mem=128G
#SBATCH --cpus-per-task=8             # must match mutation_workers in config
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

CONFIG="${CONFIG:?CONFIG required — sbatch --export=ALL,CONFIG=path/to.yaml ...}"

export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"
# Kelvin2 compute nodes drop outbound TCP silently — hub requests hang ~2h.
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1

# No module loads: Python from uv standalone (~/.local/share/uv/python/),
# CUDA runtime from bundled nvidia-* packages in the venv.
cd ~/dissertation
source .venv/bin/activate

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Config:  $CONFIG"
echo "HF_HOME: $HF_HOME"
echo "Started: $(date -u +%FT%TZ)"
echo
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

python scripts/run_eval.py --config "$CONFIG"

echo
echo "Finished: $(date -u +%FT%TZ)"
