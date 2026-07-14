#!/bin/bash --norc
# Corpus audit: template validation + within-tier diversity (v2) + mutation
# density sweep, over the full 60-template corpus (L1-L4). CPU-only, fast
# (AST parsing + TF-IDF/BLEU over small docstrings) — k2-hipri is fine.
#SBATCH --job-name=corpus-audit
#SBATCH --partition=k2-hipri
#SBATCH --time=00:30:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=2
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -uo pipefail
# Intentionally not -e: each of the four checks below is an independent
# diagnostic and a nonzero exit from one (e.g. validate_cc.py returns 1 if
# any template fails its CC band) must not skip the rest. Exit codes are
# captured and summarized at the end instead.

cd ~/dissertation
source .venv/bin/activate
export PYTHONUNBUFFERED=1

TROOT=template_corpus/templates
STATUS=0

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Started: $(date -u +%FT%TZ)"

echo
echo "=== 1/4 validate.py (template load/skeleton/oracle checks) ==="
python "$TROOT/_smoke/validate.py"; rc=$?; echo "[exit=$rc]"; STATUS=$((STATUS | (rc<<0)))

echo
echo "=== 2/4 validate_cc.py (CC / tier-membership sanity) ==="
python "$TROOT/_smoke/validate_cc.py"; rc=$?; echo "[exit=$rc]"; STATUS=$((STATUS | (rc<<1)))

echo
echo "=== 3/4 diversity_v2.py (union-of-4 within-tier diversity, real sacrebleu) ==="
python "$TROOT/_smoke/diversity_v2.py"; rc=$?; echo "[exit=$rc]"; STATUS=$((STATUS | (rc<<2)))

echo
echo "=== 4/4 mutation_sweep.py (mutation density bands) ==="
python "$TROOT/_smoke/mutation_sweep.py"; rc=$?; echo "[exit=$rc]"; STATUS=$((STATUS | (rc<<3)))

echo
echo "Finished: $(date -u +%FT%TZ)"
echo "Combined status bitmask (1=validate.py 2=validate_cc.py 4=diversity_v2.py 8=mutation_sweep.py failed): $STATUS"
exit $STATUS
