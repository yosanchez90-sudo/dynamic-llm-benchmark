"""Phase-1c Step 2 (adapted): the real decisive 2x2 factorial, given the
Step-0 correction that no_repeat_ngram_size — not repetition_penalty — is
the evidenced driver of Mechanism 1. Tests both axes explicitly under
SAMPLING (temperature=0.2, matching every real eval), >=50 problems, on
qwen7B bp_gpt5 epoch 30 (the primary suspect).

Axes:
  no_repeat_ngram_size in {0 (disabled), 4 (eval_checkpoints.py's current value)}
  repetition_penalty    in {1.0 (neutral), 1.1 (inherited from base generation_config.json)}

If corruption tracks no_repeat_ngram_size regardless of repetition_penalty,
Mechanism 1 is confirmed as no_repeat_ngram_size x prompt-echo x sampling.

Usage: python scripts/diagnose_collapse_2x2.py
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


def _problems_50():
    """>=50 problems, spread across the full inst2 population (every 3rd of
    the 150 -> 50, good tier/template coverage, not just the usual 10)."""
    problems = test_gen.load(
        instantiation_id="2", instantiation_seed=2,
        instance_seeds=(101, 102, 103, 104, 105),
        tiers=("L1", "L2"), prompting_condition="zero_shot",
    )
    return problems[::3]


def main() -> None:
    from peft import PeftModel

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    problems = _problems_50()
    print(f"{len(problems)} problems selected")

    cfg = yaml.safe_load((ROOT / "configs/finetune_qwen7b_bp_gpt5_30ep.yaml").read_text())
    model_id, rev = cfg["model"]["id"], cfg["model"]["revision"]
    ckpt_dir = ROOT / cfg["training"]["output_dir"] / "checkpoint-480"

    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=rev, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        model_id, revision=rev, dtype=torch.bfloat16, device_map="auto", local_files_only=True,
    )
    base.eval()
    print(f"base.generation_config full dict: {base.generation_config.to_dict()}")

    peft_model = PeftModel.from_pretrained(base, str(ckpt_dir))
    peft_model.eval()
    print(f"peft_model.generation_config full dict: {peft_model.generation_config.to_dict()}")

    arms = [
        ("nrn4_rp1.1", 4, 1.1),   # matches configA / current eval_checkpoints.py
        ("nrn4_rp1.0", 4, 1.0),
        ("nrn0_rp1.1", 0, 1.1),   # matches configB / original committed script
        ("nrn0_rp1.0", 0, 1.0),
    ]

    for label, nrn, rp in arms:
        print(f"\n=== {label} (no_repeat_ngram_size={nrn}, repetition_penalty={rp}, sampling temp=0.2) ===")
        gen_config = GenerationConfig(
            max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0,
            repetition_penalty=rp,
            eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
        )
        if nrn:
            gen_config.no_repeat_ngram_size = nrn
        print(f"  Effective no_repeat_ngram_size={gen_config.no_repeat_ngram_size}, "
              f"repetition_penalty={gen_config.repetition_penalty}")

        rows = []
        n_clean_import = 0
        for i, prob in enumerate(problems):
            prompt = tokenizer.apply_chat_template(
                prob.messages, tokenize=False, add_generation_prompt=True
            )
            inputs = tokenizer(prompt, return_tensors="pt").to(peft_model.device)
            torch.manual_seed(42)
            with torch.inference_mode():
                out_ids = peft_model.generate(**inputs, generation_config=gen_config)
            new_tokens = out_ids[0][inputs["input_ids"].shape[1]:]
            raw = tokenizer.decode(new_tokens, skip_special_tokens=True)
            extracted = extract_test_file(raw)
            sanitized, repairs = sanitize_test_file(extracted, prob.fn_name)
            first_line = raw.split("\n", 1)[0]
            clean = first_line.strip() == f"from under_test import {prob.fn_name}"
            n_clean_import += clean
            rows.append({
                "template_id": prob.template_id, "instance_seed": prob.instance_seed,
                "raw_response": raw, "sanitized_test_file": sanitized,
                "sanitize_repairs": repairs,
            })
            print(".", end="", flush=True)
        print()
        print(f"  clean import lines: {n_clean_import}/{len(problems)}")

        out_path = OUT_DIR / f"finetune_qwen7b_bp_gpt5_30ep__epoch30__2x2_{label}__raw.jsonl"
        with out_path.open("w") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  Wrote {out_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
