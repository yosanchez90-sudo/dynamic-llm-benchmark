#!/bin/bash --norc
#SBATCH --job-name=gen-ult-plt-subsample
#SBATCH --partition=k2-medpri
#SBATCH --time=00:30:00                # CPU-only: AST/CC scan of ~22k records + 800 mutant builds
#SBATCH --mem=4G
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

_log "launching python"
python scripts/generate_ult_plt_subsample.py | tee -a "$PROGRESS"
_log "python exited cleanly"

echo
echo "Finished: $(date -u +%FT%TZ)"
