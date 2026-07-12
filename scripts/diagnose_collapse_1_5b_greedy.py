"""Phase-1c Step 1: 1.5B greedy retests, closing the two open cells from the
prior reconciliation report. Same held-out problems and methodology as the
7B greedy checks (which found bp_own fully healthy and bp_gpt5 partially
fragile once the no_repeat_ngram_size corruption was removed).

Usage: python scripts/diagnose_collapse_1_5b_greedy.py
"""
from __future__ import annotations

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
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig  # noqa: E402

from src.data import test_gen  # noqa: E402
from src.eval.test_gen_scorer import extract_test_file, sanitize_test_file  # noqa: E402

OUT_DIR = ROOT / "data/results/debug_collapse"
TARGETS = [
    ("finetune_qwen1_5b_bp_own_30ep", "checkpoint-60", "epoch30"),
    ("finetune_qwen1_5b_bp_gpt5_30ep", "checkpoint-?", "epoch30"),  # resolved below
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
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    problems = _held_out_problems()

    cfg0 = yaml.safe_load((ROOT / "configs/finetune_qwen1_5b_bp_own_30ep.yaml").read_text())
    model_id, rev = cfg0["model"]["id"], cfg0["model"]["revision"]

    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=rev, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        model_id, revision=rev, dtype=torch.bfloat16, device_map="auto", local_files_only=True,
    )
    base.eval()

    gen_config = GenerationConfig(
        max_new_tokens=2048, do_sample=False, repetition_penalty=1.1,
        eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
    )  # greedy, no no_repeat_ngram_size — the policy confirmed clean for 7B

    configs = [
        ("finetune_qwen1_5b_bp_own_30ep", "checkpoint-60"),
        ("finetune_qwen1_5b_bp_gpt5_30ep", None),  # find final checkpoint dynamically
    ]

    peft_model = None
    for config_name, ckpt_name in configs:
        run_cfg = yaml.safe_load((ROOT / f"configs/{config_name}.yaml").read_text())
        ckpt_base = ROOT / run_cfg["training"]["output_dir"]
        if ckpt_name is None:
            ckpt_dirs = sorted(ckpt_base.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1]))
            ckpt_dir = ckpt_dirs[-1]
        else:
            ckpt_dir = ckpt_base / ckpt_name
        print(f"\n=== {config_name} ({ckpt_dir}) ===")

        if peft_model is None:
            peft_model = PeftModel.from_pretrained(base, str(ckpt_dir))
        else:
            import safetensors.torch as st
            from peft.utils import set_peft_model_state_dict
            state = st.load_file(str(ckpt_dir / "adapter_model.safetensors"))
            set_peft_model_state_dict(peft_model, state)
        peft_model.eval()

        rows = []
        n_clean_import = 0
        for prob in problems:
            prompt = tokenizer.apply_chat_template(
                prob.messages, tokenize=False, add_generation_prompt=True
            )
            inputs = tokenizer(prompt, return_tensors="pt").to(peft_model.device)
            with torch.inference_mode():
                out_ids = peft_model.generate(**inputs, generation_config=gen_config)
            new_tokens = out_ids[0][inputs["input_ids"].shape[1]:]
            raw = tokenizer.decode(new_tokens, skip_special_tokens=True)
            extracted = extract_test_file(raw)
            sanitized, repairs = sanitize_test_file(extracted, prob.fn_name)
            first_line = raw.split("\n", 1)[0]
            if first_line.strip() == f"from under_test import {prob.fn_name}":
                n_clean_import += 1
            rows.append({
                "template_id": prob.template_id, "instance_seed": prob.instance_seed,
                "raw_response": raw, "sanitized_test_file": sanitized,
                "sanitize_repairs": repairs, "n_new_tokens": int(new_tokens.shape[0]),
            })
            print(f"    {prob.template_id:20s} n_tok={int(new_tokens.shape[0]):5d} first_line={first_line[:60]!r}")

        print(f"  clean import lines: {n_clean_import}/{len(problems)}")
        out_path = OUT_DIR / f"{config_name}__epoch30_greedy__raw.jsonl"
        with out_path.open("w") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  Wrote {out_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
