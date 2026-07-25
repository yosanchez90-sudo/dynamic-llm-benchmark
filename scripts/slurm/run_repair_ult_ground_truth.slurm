#!/bin/bash --norc
#SBATCH --job-name=repair-ult-gt
#SBATCH --partition=k2-medpri
#SBATCH --time=04:00:00                # CPU-only: ~3.6k records x up to ~4 real pytest subprocess calls each
#SBATCH --mem=8G
#SBATCH --cpus-per-task=16
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
unset BASH_ENV

export PYTHONUNBUFFERED=1

cd ~/dissertation
source .venv/bin/activate

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Started: $(date -u +%FT%TZ)"
echo "CPUs:    $SLURM_CPUS_PER_TASK"
echo

python scripts/repair_ult_ground_truth.py

echo
echo "Finished: $(date -u +%FT%TZ)"
