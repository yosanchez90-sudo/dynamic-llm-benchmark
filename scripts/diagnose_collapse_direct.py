"""Phase-1 follow-up #2: reuse eval_checkpoints.py's ACTUAL _run_inference and
_score_fast functions directly (imported, not reimplemented) to rule out a
transcription bug in diagnose_collapse.py/diagnose_collapse_ab.py as the
explanation for why they showed 0/10 exec_ok on a checkpoint whose real,
already-recorded CSV row shows 150/150 (1.0) on the exact same
(epoch, instantiation), a direct contradiction that needs to be resolved
before any diagnosis is trusted.

Usage: python scripts/diagnose_collapse_direct.py
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

# Import eval_checkpoints.py AS A MODULE so we call its real functions
# verbatim, not a hand-copied version of them.
spec = importlib.util.spec_from_file_location("eval_checkpoints", ROOT / "scripts/eval_checkpoints.py")
eval_checkpoints = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eval_checkpoints)

from src.data import test_gen  # noqa: E402

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
    problems = _held_out_problems()

    cfg = yaml.safe_load((ROOT / "configs/finetune_qwen7b_bp_own_30ep.yaml").read_text())
    model_id, rev = cfg["model"]["id"], cfg["model"]["revision"]
    ckpt_dir = ROOT / cfg["training"]["output_dir"] / "checkpoint-180"

    print(f"Loading base model {model_id}@{rev[:8]}…")
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=rev, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        model_id, revision=rev, dtype=torch.bfloat16, device_map="auto", local_files_only=True,
    )
    base.eval()

    print(f"Loading adapter: {ckpt_dir}")
    peft_model = PeftModel.from_pretrained(base, str(ckpt_dir))
    peft_model.eval()

    gen_cfg = {
        "max_new_tokens": 2048, "do_sample": True, "temperature": 0.2,
        "top_p": 1.0, "seed": 42, "max_seconds": 45, "no_repeat_ngram_size": 4,
    }

    print("Generating via eval_checkpoints._run_inference() directly…")
    responses = eval_checkpoints._run_inference(peft_model, tokenizer, problems, gen_cfg)

    print("Scoring via eval_checkpoints._score_responses() directly…")
    scores = eval_checkpoints._score_responses(problems, responses, timeout=60)
    print(f"RESULT: exec_rate={scores['exec_rate']}  baseline_pass={scores['baseline_pass']}  n={scores['n']}")

    out_path = OUT_DIR / "finetune_qwen7b_bp_own_30ep__epoch30__DIRECT_reimport__raw.jsonl"
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


if __name__ == "__main__":
    main()
