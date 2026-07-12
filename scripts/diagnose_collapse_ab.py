"""Phase-1 follow-up: A/B test whether eval_checkpoints.py's extra generation
knobs (no_repeat_ngram_size=4, 45s wall-clock stopping criteria — both absent
from the original pre-finetune baseline eval) are what corrupts the
"from under_test import <fn>" line that diagnose_collapse.py found broken in
every single sample it inspected, including the "healthy" 7B bp_own control.

Rationale: no_repeat_ngram_size blocks ANY 4-gram from repeating across the
FULL sequence (prompt + generation so far, per HF's NoRepeatNGramLogitsProcessor).
The SYSTEM_INSTRUCTION in src/data/test_gen.py literally contains the phrase
"`from under_test import <function_name>`" as a formatting instruction —
so when the model tries to write that exact phrase for real, it can be a
repeat of a 4-gram already in the prompt, and generation gets forced off it.
This script tests that directly: same checkpoints, same problems, config A
(eval_checkpoints.py's, with the extra knobs) vs config B (the original
baseline's, without them).

Usage: python scripts/diagnose_collapse_ab.py
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
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

from src.data import test_gen  # noqa: E402
from src.eval.test_gen_scorer import extract_test_file, sanitize_test_file  # noqa: E402

OUT_DIR = ROOT / "data/results/debug_collapse"

TARGETS = [
    ("finetune_qwen7b_bp_gpt5_30ep", "checkpoint-480", "epoch30_primary_suspect"),
    ("finetune_qwen7b_bp_own_30ep",  "checkpoint-180", "epoch30_healthy_control"),
]

CONFIG_A_EVAL_CHECKPOINTS = dict(
    max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0, seed=42,
    max_seconds=45, no_repeat_ngram_size=4,
)
CONFIG_B_ORIGINAL_BASELINE = dict(
    max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0, seed=42,
    max_seconds=None, no_repeat_ngram_size=0,   # 0 = disabled in HF's generate()
)


class _TimeLimitCriteria:
    def __init__(self, max_seconds: float):
        import time
        self._time = time
        self.deadline = time.monotonic() + max_seconds

    def __call__(self, input_ids, scores, **kwargs):
        done = self._time.monotonic() > self.deadline
        return torch.full((input_ids.shape[0],), done, dtype=torch.bool, device=input_ids.device)


def _held_out_problems():
    problems = test_gen.load(
        instantiation_id="2", instantiation_seed=2,
        instance_seeds=(101, 102, 103, 104, 105),
        tiers=("L1", "L2"), prompting_condition="zero_shot",
    )
    l1 = [p for p in problems if p.tier == "L1"][::5][:5]
    l2 = [p for p in problems if p.tier == "L2"][::5][:5]
    return l1 + l2


def _generate(model, tokenizer, problems, cfg: dict):
    from transformers import StoppingCriteriaList
    out = []
    for prob in problems:
        prompt = tokenizer.apply_chat_template(
            prob.messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        torch.manual_seed(cfg["seed"])
        gen_kwargs = dict(
            max_new_tokens=cfg["max_new_tokens"], do_sample=cfg["do_sample"],
            temperature=cfg["temperature"], top_p=cfg["top_p"],
        )
        if cfg.get("no_repeat_ngram_size"):
            gen_kwargs["no_repeat_ngram_size"] = cfg["no_repeat_ngram_size"]
        if cfg.get("max_seconds"):
            gen_kwargs["stopping_criteria"] = StoppingCriteriaList(
                [_TimeLimitCriteria(cfg["max_seconds"])]
            )
        with torch.inference_mode():
            out_ids = model.generate(**inputs, **gen_kwargs)
        new_tokens = out_ids[0][inputs["input_ids"].shape[1]:]
        finished_naturally = bool((new_tokens == tokenizer.eos_token_id).any().item())
        text = tokenizer.decode(new_tokens, skip_special_tokens=True)
        out.append((text, int(new_tokens.shape[0]), finished_naturally))
        print(".", end="", flush=True)
    print()
    return out


def main() -> None:
    from peft import PeftModel

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    problems = _held_out_problems()

    cfg = yaml.safe_load((ROOT / f"configs/{TARGETS[0][0]}.yaml").read_text())
    model_id, rev = cfg["model"]["id"], cfg["model"]["revision"]
    print(f"Loading base model {model_id}@{rev[:8]}…")
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=rev, local_files_only=True)
    base = AutoModelForCausalLM.from_pretrained(
        model_id, revision=rev, dtype=torch.bfloat16, device_map="auto", local_files_only=True,
    )
    base.eval()

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

        for cfg_label, gen_cfg in [("configA_evalcheckpoints", CONFIG_A_EVAL_CHECKPOINTS),
                                    ("configB_original_baseline", CONFIG_B_ORIGINAL_BASELINE)]:
            print(f"  Generating: {config_name} / {label} / {cfg_label} …", flush=True)
            responses = _generate(peft_model, tokenizer, problems, gen_cfg)

            out_path = OUT_DIR / f"{config_name}__{label}__{cfg_label}__raw.jsonl"
            with out_path.open("w") as fh:
                for prob, (raw, n_tokens, finished_naturally) in zip(problems, responses):
                    extracted = extract_test_file(raw)
                    sanitized, repairs = sanitize_test_file(extracted, prob.fn_name)
                    fh.write(json.dumps({
                        "template_id": prob.template_id,
                        "tier": prob.tier,
                        "instance_seed": prob.instance_seed,
                        "raw_response": raw,
                        "n_new_tokens": n_tokens,
                        "finished_naturally_with_eos": finished_naturally,
                        "extracted_test_file": extracted,
                        "sanitized_test_file": sanitized,
                        "sanitize_repairs": repairs,
                    }, ensure_ascii=False) + "\n")
            print(f"  Wrote {out_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
