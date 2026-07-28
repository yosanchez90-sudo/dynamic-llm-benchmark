#!/bin/bash --norc
#SBATCH --job-name=rq5-dyn-deepseek
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:3g.40gb:1
#SBATCH --time=03:00:00
#SBATCH --mem=48G
#SBATCH --cpus-per-task=4
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

cd /mnt/scratch2/users/${USER}/dissertation
source .venv/bin/activate
echo "Job: $SLURM_JOB_ID on $(hostname)"
echo "Started: $(date -u +%FT%TZ)"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader

echo "=== configs/deepseek_coder_6_7b__dynamic_L1L2__inst1.yaml ==="
python scripts/run_eval.py --config configs/deepseek_coder_6_7b__dynamic_L1L2__inst1.yaml
echo "=== configs/deepseek_coder_6_7b__dynamic_L3L4__inst1.yaml ==="
python scripts/run_eval.py --config configs/deepseek_coder_6_7b__dynamic_L3L4__inst1.yaml

echo "Finished: $(date -u +%FT%TZ)"
