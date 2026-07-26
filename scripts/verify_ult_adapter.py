"""Quick, cheap sanity check before the real Stage-3a POST eval job:
does data/finetune/qwen1_5b_lora_ult_30ep/adapter_final actually load via the
SAME harness class (src.models.local.LocalModel) that scripts/run_eval.py
will use, and what's the resolved generation config (repetition_penalty/
top_k are inherited from the base checkpoint's own generation_config.json,
not logged in the 2026-07-13 PRE file since that logging fix landed a day
later -- see configs/qwen_coder_1_5b_ft_ult_30ep__ult__core400.yaml's
comment). Generates one real completion end to end as a load-bearing check,
not just "does __init__ not raise".

Usage: python scripts/verify_ult_adapter.py (submit via SLURM, not the login node)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("HF_HOME", f"/mnt/scratch2/users/{os.environ['USER']}/.huggingface")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from src.data import ult_plt  # noqa: E402
from src.eval.test_gen_problem import compute_model_label  # noqa: E402
from src.models.base import GenerationConfig  # noqa: E402
from src.models.local import LocalModel  # noqa: E402

MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
REVISION = "2e1fd397ee46e1388853d2af2c993145b0f1098a"
ADAPTER_PATH = "data/finetune/qwen1_5b_lora_ult_30ep/adapter_final"


def main() -> None:
    print(f"Loading base model + adapter from {ADAPTER_PATH} ...")
    model = LocalModel(MODEL_ID, revision=REVISION, adapter_path=ADAPTER_PATH)

    print(f"\nmodel_label: {compute_model_label(MODEL_ID, ADAPTER_PATH)}")
    print(f"adapter_path (resolved): {model.adapter_path}")
    print(f"adapter_hash (full):     {model.adapter_hash}")

    # One real generation, same manifest-loading path the eval job uses.
    problems = ult_plt.load_manifest_subset("ult", tag="core_400")
    prob = problems[0]
    print(f"\nGenerating for {prob.template_id} (seed={prob.instance_seed}) ...")

    cfg = GenerationConfig(max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0, seed=42)
    out = model.generate(prob.messages, cfg)

    print("\nResolved generation_config actually used:")
    print(json.dumps(out.generation_config, indent=2))
    print(f"\nadapter_path on ModelOutput: {out.adapter_path}")
    print(f"adapter_hash on ModelOutput: {out.adapter_hash}")
    print(f"\nFirst 500 chars of response:\n{out.response[:500]}")


if __name__ == "__main__":
    main()
