#!/bin/bash --norc
#SBATCH --job-name=pytest-gpu
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:2g.20gb:1
#SBATCH --time=00:20:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

module load python3/3.10.5/gcc-9.3.0
module load nvhpc-hpcx/23.11-cuda12
export CUDA_HOME=/opt/apps/nvhpc/23.11/cuda-12.4+cuda-11.8/Linux_x86_64/23.11/cuda
cd ~/dissertation
source .venv/bin/activate

python -c "import torch; print('torch:', torch.__version__, '| CUDA available:', torch.cuda.is_available())"
pytest -v
