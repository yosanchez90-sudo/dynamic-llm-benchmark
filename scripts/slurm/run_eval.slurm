#!/bin/bash
#SBATCH --job-name=eval
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:3g.40gb:1
#SBATCH --time=00:30:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

# CONFIG can be overridden via:  sbatch --export=ALL,CONFIG=path/to/file.yaml ...
CONFIG="${CONFIG:-configs/qwen_coder_1_5b_mini.yaml}"

module load python3/3.10.5/gcc-9.3.0
module load nvhpc-hpcx/23.11-cuda12
cd ~/dissertation
source .venv/bin/activate

echo "Job ID:   $SLURM_JOB_ID"
echo "Node:     $(hostname)"
echo "Config:   $CONFIG"
echo "Started:  $(date -u +%FT%TZ)"
echo

python scripts/run_eval.py --config "$CONFIG"

echo
echo "Finished: $(date -u +%FT%TZ)"