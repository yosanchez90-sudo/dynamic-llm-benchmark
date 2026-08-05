#!/bin/bash --norc
#SBATCH --job-name=gemini-pro-daily-crawl
#SBATCH --partition=k2-medpri
#SBATCH --time=06:00:00               # API model, CPU-only -- up to 240 real-time calls + mutation scoring
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4             # must match mutation_workers in the gemini configs
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

# Self-chaining daily job: scrontab is disabled on this cluster (confirmed
# 2026-08-05, `scrontab -l` -> "scrontab is disabled on this cluster"), so
# this script resubmits itself with --begin=now+24hours at the end of each
# day's run, until scripts/check_gemini_pro_crawl_done.py reports complete
# (inst1-4 x L1-L4 for gemini-3.1-pro-preview), at which point it stops the
# chain instead of resubmitting.
#
# Submit the FIRST link by hand:
#   env -u BASH_ENV sbatch scripts/slurm/run_gemini_daily_crawl.slurm
# Check progress any time:
#   python scripts/check_gemini_pro_crawl_done.py
# Check the chain is still alive:
#   squeue -u $USER --name=gemini-pro-daily-crawl

set -uo pipefail   # deliberately not -e: a 429/quota stop from the crawl
                    # script exits 0 by design (see run_gemini_daily_crawl.py),
                    # but we still want the resubmit-decision step below to
                    # run even if something upstream returns non-zero.

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

_log "launching daily crawl (budget 240)"
python scripts/run_gemini_daily_crawl.py --budget 240 | tee -a "$PROGRESS"
_log "daily crawl step finished (exit=$?)"

echo
echo "--- checking whether coverage is now complete ---"
python scripts/check_gemini_pro_crawl_done.py | tee -a "$PROGRESS"
DONE_STATUS=$?

if [ "$DONE_STATUS" -eq 0 ]; then
    _log "coverage complete — chain stops, not resubmitting"
    echo
    echo "Gemini Pro Preview Dynamic coverage (inst1-4) is COMPLETE. Chain stops here."
else
    _log "coverage incomplete — resubmitting for +24h"
    echo
    echo "Coverage still incomplete — resubmitting for tomorrow (+24h)."
    # Fixed repo path, not $0 -- SLURM may spool a copy of this script
    # elsewhere at submit time, so $0 isn't guaranteed to resolve back to
    # the checked-in file. cwd is already ~/dissertation (see cd above).
    env -u BASH_ENV sbatch --begin=now+24hours scripts/slurm/run_gemini_daily_crawl.slurm
fi

echo
echo "Finished: $(date -u +%FT%TZ)"
