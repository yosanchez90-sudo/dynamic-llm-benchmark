#!/bin/bash --norc
# Generic MIG-slice job: use for Qwen 1.5B (2g.20gb) or Qwen 7B (3g.30gb).
# gpu114: 4× A100 SXM4 80GB, 7 MIG slices each, 128 CPU cores, 1 TiB RAM.
# Time limit on k2-gpu-a100mig: 3 days.
#SBATCH --job-name=eval-mig
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:2g.20gb:1          # swap to gpu:3g.30gb:1 for 7B models
#SBATCH --time=06:00:00               # generous; 3-day wall limit available
#SBATCH --mem=32G
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
