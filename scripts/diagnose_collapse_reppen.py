"""Phase-1b Step 6 (targeted): the one candidate repetition-family processor
never empirically toggled — repetition_penalty=1.1, silently inherited from
the base model's own generation_config.json (confirmed present via file
read; never explicitly passed as a kwarg by any version of
eval_checkpoints.py, old or new, so HF's generate() falls through to the
model's stored default). The earlier A/B test only toggled
no_repeat_ngram_size and left this unset in both arms.

Explicit, in-code GenerationConfig (no yaml, no silent fallback) so the
active value is provable either way. Same checkpoint, same 10 held-out
problems as every prior diagnostic, greedy decoding (temperature/do_sample
removed as variables) to isolate this one processor's effect.

Usage: python scripts/diagnose_collapse_reppen.py
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

    cfg = yaml.safe_load((ROOT / "configs/finetune_qwen7b_bp_own_30ep.yaml").read_text())
    model_id, rev = cfg["model"]["id"], cfg["model"]["revision"]
    ckpt_dir = ROOT / cfg["training"]["output_dir"] / "checkpoint-180"

    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=rev, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        model_id, revision=rev, dtype=torch.bfloat16, device_map="auto", local_files_only=True,
    )
    base.eval()
    print(f"base.generation_config.repetition_penalty (loaded from HF cache): "
          f"{base.generation_config.repetition_penalty}")

    peft_model = PeftModel.from_pretrained(base, str(ckpt_dir))
    peft_model.eval()
    print(f"peft_model.generation_config.repetition_penalty: "
          f"{peft_model.generation_config.repetition_penalty}")

    variants = [
        ("reppen_1.1_inherited_explicit", 1.1),
        ("reppen_1.0_neutral_explicit", 1.0),
    ]

    for label, rep_pen in variants:
        print(f"\n=== {label} (repetition_penalty={rep_pen}, explicit GenerationConfig, greedy) ===")
        gen_config = GenerationConfig(
            max_new_tokens=2048,
            do_sample=False,          # greedy — removes sampling as a variable
            repetition_penalty=rep_pen,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
        print(f"  Effective GenerationConfig: {gen_config.to_dict()}")

        n_ok = 0
        rows = []
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
            rows.append({
                "template_id": prob.template_id, "raw_response": raw,
                "sanitized_test_file": sanitized, "sanitize_repairs": repairs,
            })
            first_line = raw.split("\n", 1)[0]
            print(f"    {prob.template_id:20s} first_line={first_line[:60]!r}")

        out_path = OUT_DIR / f"finetune_qwen7b_bp_own_30ep__epoch30__{label}__raw.jsonl"
        with out_path.open("w") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  Wrote {out_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
