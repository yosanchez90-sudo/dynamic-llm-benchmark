"""Phase-1 root-cause diagnostic: dump RAW, pre-extraction model completions
for specific fine-tuned checkpoints on held-out problems, to determine why
held-out exec_rate collapsed to ~0 for three of six Comparison-C conditions.

Raw completions are never persisted anywhere else in the pipeline
(eval_checkpoints.py scores and discards them). This is the zero-cost-first
check confirmed absent, so this script is the cheapest way to actually see
what the collapsed checkpoints produce.

Reuses eval_checkpoints.py's exact generation config (including the
wall-clock stopping criteria and no_repeat_ngram_size safety nets it adds)
so this reproduces precisely what generated the zero-exec results, not a
cleaned-up config that might behave differently. The ORIGINAL pre-finetune
baseline eval (src/models/local.py) used max_new_tokens=2048, do_sample=True,
temperature=0.2, top_p=1.0, seed=42 with NO extra stopping criteria and NO
no_repeat_ngram_size. That delta is itself part of what this script's
output should let us evaluate (n_new_tokens close to 2048 and
finished_naturally_with_eos=False both distinguish "hit the wall-clock cap
mid-stream" from "model emitted EOS and stopped cleanly").

Output: data/results/debug_collapse/<config_name>__<label>__raw.jsonl
Fields: template_id, tier, instance_seed, raw_response, n_new_tokens,
finished_naturally_with_eos, extracted_test_file, sanitized_test_file,
sanitize_repairs, i.e. the raw text AND what our actual current extraction
function does with it, so extraction failures are visible directly.

Usage (submit via SLURM, see scripts/slurm/run_diagnose_collapse.slurm):
    python scripts/diagnose_collapse.py
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

# (config_name, checkpoint dir name, label). Checkpoint dirs confirmed to
# exist on disk before wiring this in (steps_per_epoch differs per run:
# bp_gpt5/7B = 16 steps/epoch -> epoch4=checkpoint-64, epoch30=checkpoint-480;
# bp_own/7B = 6 steps/epoch -> epoch30=checkpoint-180;
# bp_own/1.5B = 2 steps/epoch -> epoch30=checkpoint-60).
TARGETS = [
    ("finetune_qwen7b_bp_gpt5_30ep",  "checkpoint-480", "epoch30_primary_suspect"),
    ("finetune_qwen7b_bp_gpt5_30ep",  "checkpoint-64",  "epoch4_pre_cliff"),
    ("finetune_qwen1_5b_bp_own_30ep", "checkpoint-60",  "epoch30"),
    ("finetune_qwen7b_bp_own_30ep",   "checkpoint-180", "epoch30_healthy_control"),
]

GEN_CFG = dict(
    max_new_tokens=2048, do_sample=True, temperature=0.2, top_p=1.0, seed=42,
    max_seconds=45, no_repeat_ngram_size=4,
)


class _TimeLimitCriteria:
    """Identical to eval_checkpoints.py's. Reproducing its exact behavior,
    not a cleaned-up version, is the point of this diagnostic."""

    def __init__(self, max_seconds: float):
        import time
        self._time = time
        self.deadline = time.monotonic() + max_seconds

    def __call__(self, input_ids, scores, **kwargs):
        done = self._time.monotonic() > self.deadline
        return torch.full((input_ids.shape[0],), done, dtype=torch.bool, device=input_ids.device)


def _held_out_problems():
    """5 L1 + 5 L2 problems from instantiation 2 (never used in training,
    which drew only on instantiation 1), spread across 5 different templates
    per tier (stride-5, since each template contributes 5 seed-instances) so
    this isn't just one template repeated 5 times.
    """
    problems = test_gen.load(
        instantiation_id="2", instantiation_seed=2,
        instance_seeds=(101, 102, 103, 104, 105),
        tiers=("L1", "L2"), prompting_condition="zero_shot",
    )
    l1 = [p for p in problems if p.tier == "L1"][::5][:5]
    l2 = [p for p in problems if p.tier == "L2"][::5][:5]
    return l1 + l2


def _generate(model, tokenizer, problems):
    from transformers import StoppingCriteriaList
    out = []
    for prob in problems:
        prompt = tokenizer.apply_chat_template(
            prob.messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        torch.manual_seed(GEN_CFG["seed"])
        stopping = StoppingCriteriaList([_TimeLimitCriteria(GEN_CFG["max_seconds"])])
        with torch.inference_mode():
            out_ids = model.generate(
                **inputs,
                max_new_tokens=GEN_CFG["max_new_tokens"],
                do_sample=GEN_CFG["do_sample"],
                temperature=GEN_CFG["temperature"],
                top_p=GEN_CFG["top_p"],
                no_repeat_ngram_size=GEN_CFG["no_repeat_ngram_size"],
                stopping_criteria=stopping,
            )
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
    print(f"{len(problems)} held-out problems: "
          f"{[p.template_id for p in problems]}")

    by_model_id: dict[str, list] = {}
    for config_name, ckpt, label in TARGETS:
        cfg = yaml.safe_load((ROOT / f"configs/{config_name}.yaml").read_text())
        by_model_id.setdefault(cfg["model"]["id"], []).append((config_name, cfg, ckpt, label))

    for model_id, jobs in by_model_id.items():
        rev = jobs[0][1]["model"]["revision"]
        print(f"\nLoading base model {model_id}@{rev[:8]}…")
        tokenizer = AutoTokenizer.from_pretrained(model_id, revision=rev, local_files_only=True)
        base = AutoModelForCausalLM.from_pretrained(
            model_id, revision=rev, dtype=torch.bfloat16,
            device_map="auto", local_files_only=True,
        )
        base.eval()

        peft_model = None
        for config_name, cfg, ckpt, label in jobs:
            ckpt_dir = ROOT / cfg["training"]["output_dir"] / ckpt
            print(f"  Loading adapter: {ckpt_dir}")
            if peft_model is None:
                peft_model = PeftModel.from_pretrained(base, str(ckpt_dir))
            else:
                import safetensors.torch as st
                from peft.utils import set_peft_model_state_dict
                adapter_file = ckpt_dir / "adapter_model.safetensors"
                state = st.load_file(str(adapter_file))
                set_peft_model_state_dict(peft_model, state)
            peft_model.eval()

            print(f"  Generating: {config_name} / {label} …", flush=True)
            responses = _generate(peft_model, tokenizer, problems)

            out_path = OUT_DIR / f"{config_name}__{label}__raw.jsonl"
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

        del base, peft_model
        torch.cuda.empty_cache()

    print("\nDone.")


if __name__ == "__main__":
    main()
