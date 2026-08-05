#!/bin/bash --norc
#SBATCH --job-name=create-batch-core400
#SBATCH --partition=k2-medpri
#SBATCH --time=02:00:00               # CPU-only: builds messages + mutants for 1600 problems, no API calls (write-only, no --submit)
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

# k2-medpri nodes have working NFS but still source BASH_ENV at bash startup
# unless it is stripped. Submit via: env -u BASH_ENV sbatch ...
unset BASH_ENV

export PYTHONUNBUFFERED=1

PROGRESS="/mnt/scratch2/users/${USER}/dissertation/logs/progress_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$PROGRESS")"
_log() { echo "[$(date -u +%FT%TZ)] $*" >> "$PROGRESS"; }
trap '_log "script exiting (exit=$?)"' EXIT

_log "starting on $(hostname)"
cd ~/dissertation
_log "cd done"

source .venv/bin/activate
_log "venv activated — $(python --version 2>&1)"

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Started: $(date -u +%FT%TZ)"
echo

# No --submit flag: writes the batch input JSONL + state file only (this is
# now create_batch.py's default, changed 2026-08-05 so a bare invocation
# never spends money). No upload, no API call, no spend.
_log "launching python (write-only, --submit not passed)"
python scripts/create_batch.py \
    configs/gpt_5__ult__core400.yaml \
    configs/gpt_5__plt__core400.yaml \
    configs/gpt_5_mini__ult__core400.yaml \
    configs/gpt_5_mini__plt__core400.yaml \
    | tee -a "$PROGRESS"
_log "python exited cleanly"

echo
echo "Finished: $(date -u +%FT%TZ)"
