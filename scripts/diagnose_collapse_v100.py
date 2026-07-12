"""Phase-1b Step 5: hardware control. Same checkpoints, same 10 held-out
problems, same production code path (eval_checkpoints.py's actual functions,
imported directly) as diagnose_collapse_direct.py — but run on a V100, the
ORIGINAL hardware every bp_* condition's healthy/collapsed numbers were
actually measured on (confirmed via job logs: 9315776-9315779 all ran on
gpu105/106/107, Tesla V100-PCIE-32GB). All prior diagnostics ran on A100 MIG
(gpu114) instead, which was never ruled out as a confound. This tests both
the healthy control and the primary suspect on the correct hardware.

Usage: python scripts/diagnose_collapse_v100.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("HF_HOME", f"/mnt/scratch2/users/{os.environ.get('USER', '')}/.huggingface")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import torch  # noqa: E402
import yaml  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

spec = importlib.util.spec_from_file_location("eval_checkpoints", ROOT / "scripts/eval_checkpoints.py")
eval_checkpoints = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eval_checkpoints)

from src.data import test_gen  # noqa: E402

OUT_DIR = ROOT / "data/results/debug_collapse"

TARGETS = [
    ("finetune_qwen7b_bp_own_30ep",  "checkpoint-180", "epoch30_healthy_control"),
    ("finetune_qwen7b_bp_gpt5_30ep", "checkpoint-480", "epoch30_primary_suspect"),
]


def _held_out_problems():
    problems = test_gen.load(
        instantiation_id="2", instantiation_seed=2,
        instance_seeds=(101, 102, 103, 104, 105),
        tiers=("L1", "L2"), prompting_condition="zero_shot",
    )
    l1 = [p for p in problems if p.tier == "L1"][::5][:5]
    l2 = [p for p in problems if p.tier == "L2"][::5][:5]
    return l1 + l2


def main() -> None:
    from peft import PeftModel

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    problems = _held_out_problems()
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    cfg0 = yaml.safe_load((ROOT / f"configs/{TARGETS[0][0]}.yaml").read_text())
    model_id, rev = cfg0["model"]["id"], cfg0["model"]["revision"]
    print(f"Loading base model {model_id}@{rev[:8]}…")
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=rev, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        model_id, revision=rev, dtype=torch.bfloat16, device_map="auto", local_files_only=True,
    )
    base.eval()
    print(f"Model dtype actually loaded as: {next(base.parameters()).dtype}")

    gen_cfg = {
        "max_new_tokens": 2048, "do_sample": True, "temperature": 0.2,
        "top_p": 1.0, "seed": 42, "max_seconds": 45, "no_repeat_ngram_size": 4,
    }

    peft_model = None
    for config_name, ckpt, label in TARGETS:
        run_cfg = yaml.safe_load((ROOT / f"configs/{config_name}.yaml").read_text())
        ckpt_dir = ROOT / run_cfg["training"]["output_dir"] / ckpt
        print(f"\nLoading adapter: {ckpt_dir}")
        if peft_model is None:
            peft_model = PeftModel.from_pretrained(base, str(ckpt_dir))
        else:
            import safetensors.torch as st
            from peft.utils import set_peft_model_state_dict
            state = st.load_file(str(ckpt_dir / "adapter_model.safetensors"))
            set_peft_model_state_dict(peft_model, state)
        peft_model.eval()

        print(f"Generating via eval_checkpoints._run_inference() [{config_name}/{label}]…")
        responses = eval_checkpoints._run_inference(peft_model, tokenizer, problems, gen_cfg)
        scores = eval_checkpoints._score_responses(problems, responses, timeout=60)
        print(f"RESULT [{config_name}/{label}]: exec_rate={scores['exec_rate']} "
              f"baseline_pass={scores['baseline_pass']} n={scores['n']}")

        out_path = OUT_DIR / f"{config_name}__{label}__V100_hardware_control__raw.jsonl"
        with out_path.open("w") as fh:
            for prob, raw in zip(problems, responses):
                extracted = eval_checkpoints.extract_test_file(raw)
                sanitized, repairs = eval_checkpoints.sanitize_test_file(extracted, prob.fn_name)
                exec_ok, bp = eval_checkpoints._score_fast(prob.source, prob.fn_name, sanitized, timeout=60)
                fh.write(json.dumps({
                    "template_id": prob.template_id,
                    "raw_response": raw,
                    "extracted_test_file": extracted,
                    "sanitized_test_file": sanitized,
                    "sanitize_repairs": repairs,
                    "exec_ok": exec_ok,
                    "baseline_passed": bp,
                }, ensure_ascii=False) + "\n")
        print(f"Wrote {out_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
