#!/bin/bash --norc
#SBATCH --job-name=eval-api
#SBATCH --partition=k2-medpri
#SBATCH --time=02:00:00               # API inference is fast but mutation scoring is CPU-bound
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4             # must match mutation_workers in the config
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