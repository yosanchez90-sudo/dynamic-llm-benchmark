#!/bin/bash --norc
#SBATCH --job-name=eval-api
#SBATCH --partition=k2-medpri
#SBATCH --time=02:00:00               # API inference is fast; mutation scoring is CPU-bound
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4             # must match mutation_workers in the config
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
CONFIG="${CONFIG:?CONFIG variable required}"

# k2-medpri nodes have working NFS but still source BASH_ENV at bash startup
# unless it is stripped. Submit via: env -u BASH_ENV sbatch ...
# Belt-and-suspenders: unset here too, for any child bash invocations.
unset BASH_ENV

export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export PYTHONUNBUFFERED=1

PROGRESS="/mnt/scratch2/users/${USER}/dissertation/logs/progress_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$PROGRESS")"
_log() { echo "[$(date -u +%FT%TZ)] $*" >> "$PROGRESS"; }
trap '_log "script exiting (exit=$?)"' EXIT

# No module loads: Python from uv standalone (~/.local/share/uv/python/).
_log "starting on $(hostname)"
cd ~/dissertation
_log "cd done"

source .venv/bin/activate
_log "venv activated — $(python --version 2>&1)"

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Config:  $CONFIG"
echo "Started: $(date -u +%FT%TZ)"
echo

_log "launching python"
python scripts/run_eval.py --config "$CONFIG" | tee -a "$PROGRESS"
_log "python exited cleanly"

echo
echo "Finished: $(date -u +%FT%TZ)"
