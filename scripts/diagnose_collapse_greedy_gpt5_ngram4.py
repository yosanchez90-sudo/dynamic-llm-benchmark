"""Phase-1c follow-up: (1) fill the missing
greedy + no_repeat_ngram_size=4 cell for factorial completeness; (2) measure
per-generation wall-clock time, for generations that run to the
full max_new_tokens=2048 (the worst case), to size the wall-clock guard
instead of inheriting the old 45s value. Runs on bp_gpt5(7B)
epoch30 (the most verbose/complex condition, worst case for timing) plus a
few problems from bp_own(7B) for contrast.

Usage: python scripts/diagnose_collapse_greedy_gpt5_ngram4.py
"""
from __future__ import annotations

import json
import os
import sys
import time
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
    print(f"{len(problems)} problems")

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
    peft_model = PeftModel.from_pretrained(base, str(ckpt_dir))
    peft_model.eval()

    # ---- Part C: missing cell, greedy + no_repeat_ngram_size=4 ----
    print("\n=== greedy + no_repeat_ngram_size=4 (missing factorial cell) ===")
    gen_config = GenerationConfig(
        max_new_tokens=2048, do_sample=False, repetition_penalty=1.1,
        no_repeat_ngram_size=4,
        eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
    )
    rows = []
    n_clean = 0
    timings = []
    for prob in problems:
        prompt = tokenizer.apply_chat_template(prob.messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(peft_model.device)
        t0 = time.monotonic()
        with torch.inference_mode():
            out_ids = peft_model.generate(**inputs, generation_config=gen_config)
        elapsed = time.monotonic() - t0
        new_tokens = out_ids[0][inputs["input_ids"].shape[1]:]
        n_tok = int(new_tokens.shape[0])
        raw = tokenizer.decode(new_tokens, skip_special_tokens=True)
        extracted = extract_test_file(raw)
        sanitized, repairs = sanitize_test_file(extracted, prob.fn_name)
        clean = raw.split("\n", 1)[0].strip() == f"from under_test import {prob.fn_name}"
        n_clean += clean
        timings.append((n_tok, elapsed))
        rows.append({
            "template_id": prob.template_id, "instance_seed": prob.instance_seed,
            "raw_response": raw, "n_new_tokens": n_tok, "elapsed_seconds": elapsed,
            "sanitized_test_file": sanitized, "sanitize_repairs": repairs,
        })
        print(".", end="", flush=True)
    print()
    print(f"clean import lines: {n_clean}/{len(problems)}")
    out_path = OUT_DIR / "finetune_qwen7b_bp_gpt5_30ep__epoch30__greedy_ngram4__raw.jsonl"
    with out_path.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {out_path}")

    # ---- Part D: timing distribution, greedy WITHOUT ngram ban (the policy
    # we're about to ship), specifically looking for full-length (2048 token)
    # generations to find worst-case per-generation wall-clock time ----
    print("\n=== timing pass: greedy, no_repeat_ngram_size=0 (shipping policy) ===")
    gen_config2 = GenerationConfig(
        max_new_tokens=2048, do_sample=False, repetition_penalty=1.1,
        eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
    )
    timings2 = []
    for prob in problems:
        prompt = tokenizer.apply_chat_template(prob.messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(peft_model.device)
        t0 = time.monotonic()
        with torch.inference_mode():
            out_ids = peft_model.generate(**inputs, generation_config=gen_config2)
        elapsed = time.monotonic() - t0
        new_tokens = out_ids[0][inputs["input_ids"].shape[1]:]
        n_tok = int(new_tokens.shape[0])
        timings2.append((n_tok, elapsed))
        print(f"  n_tok={n_tok:5d} elapsed={elapsed:6.1f}s  ({n_tok/elapsed if elapsed else 0:.1f} tok/s)")

    all_timings = timings + timings2
    max_n_tok = max(t[0] for t in all_timings)
    full_length = [t for t in all_timings if t[0] >= 2040]
    print(f"\nGenerations hitting ~full max_new_tokens (>=2040): {len(full_length)}/{len(all_timings)}")
    if full_length:
        max_elapsed = max(t[1] for t in full_length)
        print(f"  slowest full-length generation: {max_elapsed:.1f}s")
    rates = [t[0] / t[1] for t in all_timings if t[1] > 0]
    print(f"tok/s across all generations: min={min(rates):.1f} p50={sorted(rates)[len(rates)//2]:.1f} max={max(rates):.1f}")
    worst_case_2048 = 2048 / min(rates)
    print(f"Worst observed tok/s implies a full 2048-token generation could take up to {worst_case_2048:.0f}s")

    print("\nDone.")


if __name__ == "__main__":
    main()
