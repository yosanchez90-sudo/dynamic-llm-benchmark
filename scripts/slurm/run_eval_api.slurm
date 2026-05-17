#!/bin/bash
#SBATCH --job-name=eval-api
#SBATCH --partition=k2-medpri
#SBATCH --time=01:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=2
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
CONFIG="${CONFIG:?CONFIG variable required}"

module load python3/3.10.5/gcc-9.3.0
cd ~/dissertation
source .venv/bin/activate

echo "Job ID: $SLURM_JOB_ID  Node: $(hostname)  Config: $CONFIG"
echo "Started: $(date -u +%FT%TZ)"

python scripts/run_eval.py --config "$CONFIG"

echo "Finished: $(date -u +%FT%TZ)"