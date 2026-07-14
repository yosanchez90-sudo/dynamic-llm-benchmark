#!/bin/bash --norc
# Build the equivalent-mutant inspection pack (30 mutants/tier, 120 total)
# and do a dry run of the validated-score computation against the current
# (unfilled) sheet, to confirm it handles that state gracefully. CPU-only,
# same order of work as the corpus diversity audit -- k2-hipri is fine.
#SBATCH --job-name=equiv-mutant-pack
#SBATCH --partition=k2-hipri
#SBATCH --time=00:30:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=2
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -uo pipefail

cd ~/dissertation
source .venv/bin/activate
export PYTHONUNBUFFERED=1

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Started: $(date -u +%FT%TZ)"

echo
echo "=== 1/2 build_equiv_mutant_sample.py ==="
python scripts/build_equiv_mutant_sample.py
rc1=$?

echo
echo "=== 2/2 compute_validated_score.py (dry run against unfilled sheet) ==="
python scripts/compute_validated_score.py
rc2=$?

echo
echo "Finished: $(date -u +%FT%TZ)"
echo "Exit codes: build=$rc1 compute=$rc2"
exit $((rc1 || rc2))
