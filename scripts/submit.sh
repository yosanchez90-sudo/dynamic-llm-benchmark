#!/bin/bash
# Submit an eval config to the right SLURM template based on provider/model size.
#
# Usage:  ./scripts/submit.sh configs/qwen_coder_1_5b__dynamic_L1L2.yaml
#
# Node routing logic (Kelvin2 hardware):
#   local 32B            → k2-gpu-a100   (4× A100 80GB full, 128 CPU, 1TB)
#   local 7B             → k2-gpu-a100mig (3g.40gb slice, 128 CPU, 1TB)
#   local <7B (1.5B etc) → k2-gpu-a100mig (2g.20gb slice, 128 CPU, 1TB)
#   anthropic/openai/gemini → k2-medpri (CPU-only, 128 CPU, 1TB, 24h limit)

set -euo pipefail

CONFIG="${1:?Usage: $0 <config-path>}"

if [ ! -f "$CONFIG" ]; then
    echo "Config not found: $CONFIG"
    exit 1
fi

PROVIDER=$(python -c "import yaml; print(yaml.safe_load(open('$CONFIG'))['model']['provider'])")
MODEL_ID=$(python -c "import yaml; print(yaml.safe_load(open('$CONFIG'))['model']['id'])")

case "$PROVIDER" in
    local)
        if [[ "$MODEL_ID" == *"32B"* || "$MODEL_ID" == *"32b"* ]]; then
            SCRIPT="scripts/slurm/run_eval_a100.slurm"
        elif [[ "$MODEL_ID" == *"7B"* || "$MODEL_ID" == *"7b"* ]]; then
            # 7B needs the 3g.40gb MIG slice — edit run_eval_mig.slurm GRES line before submitting
            SCRIPT="scripts/slurm/run_eval_mig.slurm"
            echo "NOTE: 7B model — ensure run_eval_mig.slurm uses gpu:3g.40gb:1 (not 2g.20gb:1)"
        else
            SCRIPT="scripts/slurm/run_eval_mig.slurm"
        fi
        ;;
    anthropic|openai|gemini)
        SCRIPT="scripts/slurm/run_eval_api.slurm"
        ;;
    *)
        echo "Unknown provider: $PROVIDER"
        exit 1
        ;;
esac

echo "Provider: $PROVIDER  Model: $MODEL_ID  Template: $SCRIPT"
sbatch --export=ALL,CONFIG="$CONFIG" "$SCRIPT"
