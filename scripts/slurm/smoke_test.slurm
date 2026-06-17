#!/bin/bash --norc
#SBATCH --job-name=smoke-test
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:2g.20gb:1
#SBATCH --time=00:30:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --output=logs/smoke-%j.out
#SBATCH --error=logs/smoke-%j.err

set -euo pipefail

CONFIG="${CONFIG:?CONFIG must be set}"
SHARD_ID="${SHARD_ID:-0}"
N_SHARDS="${N_SHARDS:-8}"

module load python3/3.10.5/gcc-9.3.0
module load nvhpc-hpcx/23.11-cuda12
cd ~/dissertation
source .venv/bin/activate

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Config:  $CONFIG"
echo "Shard:   $SHARD_ID / $N_SHARDS"
echo "Started: $(date -u +%FT%TZ)"
echo

python scripts/run_eval.py \
    --config "$CONFIG" \
    --shard-id "$SHARD_ID" \
    --n-shards "$N_SHARDS"

echo
echo "Finished: $(date -u +%FT%TZ)"
