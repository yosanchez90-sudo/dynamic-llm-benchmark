#!/bin/bash
# Submit an eval config to the right SLURM template based on its provider/size.
#
# Usage:  ./scripts/submit.sh configs/qwen_coder_32b__mini_coding.yaml

set -euo pipefail

CONFIG="${1:?Usage: $0 <config-path>}"

if [ ! -f "$CONFIG" ]; then
    echo "Config not found: $CONFIG"
    exit 1
fi

# Read provider + model id from YAML (use python — bash YAML parsing is misery)
PROVIDER=$(python -c "import yaml; print(yaml.safe_load(open('$CONFIG'))['model']['provider'])")
MODEL_ID=$(python -c "import yaml; print(yaml.safe_load(open('$CONFIG'))['model']['id'])")

case "$PROVIDER" in
    local)
        if [[ "$MODEL_ID" == *"32B"* || "$MODEL_ID" == *"32b"* ]]; then
            SCRIPT="scripts/slurm/run_eval_a100.slurm"
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