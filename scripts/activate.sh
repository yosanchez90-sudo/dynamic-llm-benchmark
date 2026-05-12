#!/bin/bash
flight env activate modules@default
module load python3/3.10.5/gcc-9.3.0
module load nvhpc-hpcx/23.11-cuda12
export CUDA_HOME=/opt/apps/nvhpc/23.11/cuda-12.4+cuda-11.8/Linux_x86_64/23.11/cuda
source .venv/bin/activate
echo "Environment activated. Python: $(python3 --version)"
