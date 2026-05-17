#!/bin/bash
#SBATCH --job-name=eval-a100
#SBATCH --partition=k2-gpu-a100
#SBATCH --gres=gpu:a100:1
#SBATCH --time=02:00:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=8
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
CONFIG="${CONFIG:?CONFIG variable required}"

module load python3/3.10.5/gcc-9.3.0
module load nvhpc-hpcx/23.11-cuda12
cd ~/dissertation
source .venv/bin/activate

echo "Job ID: $SLURM_JOB_ID  Node: $(hostname)  Config: $CONFIG"
echo "Started: $(date -u +%FT%TZ)"
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv

python scripts/run_eval.py --config "$CONFIG"

echo "Finished: $(date -u +%FT%TZ)"