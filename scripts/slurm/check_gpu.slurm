#!/bin/bash --norc
#SBATCH --job-name=gpu-check
#SBATCH --partition=k2-gpu-v100
#SBATCH --gres=gpu:v100:1
#SBATCH --time=00:10:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

module load python3/3.10.5/gcc-9.3.0
module load nvhpc-hpcx/23.11-cuda12
cd ~/dissertation
source .venv/bin/activate

python scripts/check_gpu.py