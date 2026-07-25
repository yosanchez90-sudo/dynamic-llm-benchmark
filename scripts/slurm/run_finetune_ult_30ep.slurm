#!/bin/bash --norc
#SBATCH --job-name=finetune-ult-30ep
#SBATCH --partition=k2-gpu-a100mig
#SBATCH --gres=gpu:3g.40gb:1
#SBATCH --time=12:00:00             # see STOP GATE B estimate: expected ~3-6h, 12h matches existing runs' budget
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
unset BASH_ENV

export HF_HOME="/mnt/scratch2/users/${USER}/.huggingface"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false

cd ~/dissertation
source .venv/bin/activate

echo "Job:     $SLURM_JOB_ID on $(hostname)"
echo "GPU:     $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
echo "Started: $(date -u +%FT%TZ)"
echo

# Training data is already built + repair-verified + length-filtered
# (data/finetune/train_ult_final.jsonl, see data/raw/ult_plt/PROVENANCE.md) --
# unlike run_finetune_30ep.slurm, this does NOT call prepare_finetune_data.py.
python scripts/finetune_qwen7b.py --config configs/finetune_qwen1_5b_ult_30ep.yaml

echo
echo "Finished: $(date -u +%FT%TZ)"
