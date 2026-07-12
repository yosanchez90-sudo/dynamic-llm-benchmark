"""Phase-1b follow-up: does greedy decoding also clean up bp_gpt5 (the
primary suspect, a genuine collapse confirmed to predate any script changes)?
If yes, its "collapse" may be the same sampling fragility as bp_own's false
0/10. If no, bp_gpt5 has a real, sampling-independent defect on top of that
fragility. Tests epoch30 (post-cliff) and epoch4 (pre-cliff) both greedy.

Usage: python scripts/diagnose_collapse_greedy_gpt5.py
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
TARGETS = [("checkpoint-480", "epoch30_greedy"), ("checkpoint-64", "epoch4_greedy")]


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

    cfg = yaml.safe_load((ROOT / "configs/finetune_qwen7b_bp_gpt5_30ep.yaml").read_text())
    model_id, rev = cfg["model"]["id"], cfg["model"]["revision"]

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
    )

    peft_model = None
    for ckpt, label in TARGETS:
        ckpt_dir = ROOT / cfg["training"]["output_dir"] / ckpt
        print(f"\n=== {label} ({ckpt_dir}) ===")
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
            expected_prefix = f"from under_test import"
            if first_line.startswith(expected_prefix):
                n_clean_import += 1
            rows.append({
                "template_id": prob.template_id, "raw_response": raw,
                "sanitized_test_file": sanitized, "sanitize_repairs": repairs,
            })
            print(f"    {prob.template_id:20s} first_line={first_line[:70]!r}")

        print(f"  clean import lines: {n_clean_import}/{len(problems)}")
        out_path = OUT_DIR / f"finetune_qwen7b_bp_gpt5_30ep__{label}__raw.jsonl"
        with out_path.open("w") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  Wrote {out_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
