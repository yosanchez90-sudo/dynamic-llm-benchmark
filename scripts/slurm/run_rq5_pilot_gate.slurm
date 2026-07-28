#!/bin/bash --norc
#SBATCH --job-name=rq5-pilot-gate
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:3g.40gb:1          # 40GB MIG slice -- covers up to CodeLlama-13B (~26GB weights)
#SBATCH --time=00:45:00               # 3 models x 5 problems, generous buffer for cold model loads
#SBATCH --mem=48G
#SBATCH --cpus-per-task=4             # must match mutation_workers in the configs
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_CACHE="${HF_HOME}/hub"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

PROGRESS="/mnt/scratch2/users/${USER}/dissertation/logs/progress_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$PROGRESS")"
_log() { echo "[$(date -u +%FT%TZ)] $*" >> "$PROGRESS"; }
trap '_log "script exiting (exit=$?)"' EXIT

cd /mnt/scratch2/users/${USER}/dissertation
_log "cd done"

source .venv/bin/activate
_log "venv activated — $(python --version 2>&1)"

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "Started: $(date -u +%FT%TZ)"
echo

_log "checking GPU..."
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader | tee -a "$PROGRESS"

# StarCoder2-15B-Instruct-v0.1 deliberately excluded: its tokenizer_config.json
# chat_template unconditionally raise_exception()s on role="system"
# (verified 2026-07-28 by reading the template source directly), and this
# project's src/data/test_gen.py::_build_messages always sends one -- a
# guaranteed crash, not a pilot outcome worth spending a GPU slot on. Flagged
# for the supervisor's decision (drop it, or accommodate it), not run here.
for cfg in \
  configs/dry_run_ult_deepseek_coder_6_7b.yaml \
  configs/dry_run_ult_codellama_13b.yaml \
  configs/dry_run_ult_mistral_7b.yaml
do
  _log "launching $cfg"
  echo "=== $cfg ==="
  python scripts/run_eval.py --config "$cfg" | tee -a "$PROGRESS"
  echo
done

_log "python exited cleanly"
echo "Finished: $(date -u +%FT%TZ)"
