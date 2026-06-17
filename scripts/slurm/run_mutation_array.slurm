#!/bin/bash --norc
#SBATCH --job-name=mut-array
#SBATCH --partition=k2-medpri          # CPU partition — mutation scoring is CPU-bound
#SBATCH --array=0-29                   # 30 shards; tune to corpus size / time budget
#SBATCH --time=04:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=8              # within-problem Pool uses these; set
                                       # mutation_workers in config to match
#SBATCH --output=logs/%x-%A_%a.out    # %A = array job id, %a = task id
#SBATCH --error=logs/%x-%A_%a.err

set -euo pipefail

CONFIG="${CONFIG:?CONFIG required — sbatch --export=ALL,CONFIG=path/to.yaml ...}"

module load python3/3.10.5/gcc-9.3.0
cd ~/dissertation
source .venv/bin/activate

echo "Array task ${SLURM_ARRAY_TASK_ID} of ${SLURM_ARRAY_TASK_COUNT} on $(hostname)"
echo "Config:  ${CONFIG}"
echo "Started: $(date -u +%FT%TZ)"
echo

python scripts/run_eval.py \
    --config "${CONFIG}" \
    --shard-id "${SLURM_ARRAY_TASK_ID}" \
    --n-shards "${SLURM_ARRAY_TASK_COUNT}"

echo
echo "Finished: $(date -u +%FT%TZ)"
