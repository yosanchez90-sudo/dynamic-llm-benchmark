#!/bin/bash --norc
#SBATCH --job-name=process-batch
#SBATCH --partition=k2-medpri
#SBATCH --time=04:00:00               # CPU-only mutation scoring; no live API calls with --results-file
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4             # must match mutation_workers in the batch state (4)
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
STATE_FILE="${STATE_FILE:?STATE_FILE variable required (data/batches/batch_state_<ts>.json)}"
RESULTS_FILE="${RESULTS_FILE:?RESULTS_FILE variable required (data/batches/batch_output_<ts>.jsonl)}"

# k2-medpri nodes have working NFS but still source BASH_ENV at bash startup
# unless it is stripped. Submit via: env -u BASH_ENV sbatch ...
unset BASH_ENV

export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
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

echo "Job:          $SLURM_JOB_ID on $(hostname)"
echo "State file:   $STATE_FILE"
echo "Results file: $RESULTS_FILE"
echo "Started:      $(date -u +%FT%TZ)"
echo

_log "launching python"
python scripts/process_batch.py "$STATE_FILE" --results-file "$RESULTS_FILE" | tee -a "$PROGRESS"
_log "python exited cleanly"

echo
echo "Finished: $(date -u +%FT%TZ)"
