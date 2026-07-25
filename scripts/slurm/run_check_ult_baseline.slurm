#!/bin/bash --norc
#SBATCH --job-name=check-ult-baseline
#SBATCH --partition=k2-medpri
#SBATCH --time=02:00:00                # CPU-only: ~3.6k records, 3s per-record timeout worst case
#SBATCH --mem=4G
#SBATCH --cpus-per-task=2
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
unset BASH_ENV

export PYTHONUNBUFFERED=1

cd ~/dissertation
source .venv/bin/activate

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Started: $(date -u +%FT%TZ)"
echo

python scripts/check_ult_ground_truth_baseline.py

echo
echo "Finished: $(date -u +%FT%TZ)"
