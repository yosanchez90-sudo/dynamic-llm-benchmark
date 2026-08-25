#!/bin/bash
# Load Kelvin2's Python/CUDA modules and activate the project's uv-managed
# venv (.venv/, built from pyproject.toml/uv.lock at the repo root).
#
# Inputs: none. Outputs: none written to disk -- exports CUDA_HOME and
# activates .venv/ in the current shell.
#
# Position in the pipeline: sourced (`source scripts/activate.sh`), not run,
# at the start of any interactive session on Kelvin2 before running a script
# directly. SLURM batch jobs load the same modules themselves via their own
# #SBATCH/module-load lines, so this script is for interactive use.
flight env activate modules@default
module load python3/3.10.5/gcc-9.3.0
module load nvhpc-hpcx/23.11-cuda12
export CUDA_HOME=/opt/apps/nvhpc/23.11/cuda-12.4+cuda-11.8/Linux_x86_64/23.11/cuda
source .venv/bin/activate
echo "Environment activated. Python: $(python3 --version)"
