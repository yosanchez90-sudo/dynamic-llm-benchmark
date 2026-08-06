#!/bin/bash --norc
#SBATCH --job-name=openai-batch-poll
#SBATCH --partition=k2-medpri
#SBATCH --time=00:10:00               # just a status check + resubmit decision, not compute
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

# Self-chaining light poll for the six GPT-5/-mini batches submitted
# 2026-08-06 (data/batches/batch_state_20260806T195356{a..f}__*.json).
# scrontab is disabled on this cluster (same finding as the Gemini crawl),
# so this resubmits itself every 30 minutes via sbatch --begin=now+30minutes
# until scripts/check_openai_batch_status.py reports all six complete, at
# which point it stops the chain and leaves a clear marker for Phase B.
#
# Submit the FIRST link by hand:
#   env -u BASH_ENV sbatch scripts/slurm/poll_openai_batches.slurm
# Check any time without waiting for a poll:
#   python scripts/check_openai_batch_status.py

set -uo pipefail   # not -e: a non-zero "still in progress" exit from the
                    # check script is an expected, normal outcome here, not
                    # a script bug -- the resubmit-decision step below must
                    # still run when that happens.

unset BASH_ENV
export PYTHONUNBUFFERED=1

PROGRESS="/mnt/scratch2/users/${USER}/dissertation/logs/progress_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$PROGRESS")"
_log() { echo "[$(date -u +%FT%TZ)] $*" >> "$PROGRESS"; }
trap '_log "script exiting (exit=$?)"' EXIT

_log "starting poll on $(hostname)"
cd ~/dissertation
source .venv/bin/activate

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Started: $(date -u +%FT%TZ)"
echo

python scripts/check_openai_batch_status.py | tee -a "$PROGRESS"
STATUS=$?

echo
if [ "$STATUS" -eq 0 ]; then
    _log "all six batches completed — chain stops, ready for Phase B"
    echo "ALL SIX BATCHES COMPLETE. Chain stops here. Ready for Phase B ingestion."
elif [ "$STATUS" -eq 2 ]; then
    _log "a batch failed/expired/cancelled — chain stops, needs human attention"
    echo "A BATCH FAILED/EXPIRED/CANCELLED. Chain stops here — this needs a look, not another poll."
else
    _log "still in progress — resubmitting for +30min"
    echo "Still in progress — resubmitting poll for +30 minutes."
    env -u BASH_ENV sbatch --begin=now+30minutes scripts/slurm/poll_openai_batches.slurm
fi

echo
echo "Finished: $(date -u +%FT%TZ)"
