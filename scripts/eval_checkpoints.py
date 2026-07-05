"""Evaluate LoRA checkpoints across instantiations to plot performance vs epoch.

Loads the base model ONCE, then hot-swaps adapter weights for each checkpoint
so we don't pay the 14GB reload cost at every epoch. Only runs exec gate +
baseline pass — mutation scoring is skipped to keep runtime tractable
(~15 min per checkpoint × 3 instantiations vs ~6h with mutation).

Usage:
    python scripts/eval_checkpoints.py \\
        --config configs/finetune_qwen7b_inst1_30ep.yaml \\
        --epochs 1 3 5 10 15 20 25 30 \\
        --instantiations 1 2 3 \\
        --out analysis/epoch_perf_qwen7b.csv

    # Also pass --baseline to include the no-adapter baseline (epoch 0):
    python scripts/eval_checkpoints.py \\
        --config configs/finetune_qwen7b_inst1_30ep.yaml \\
        --epochs 1 3 5 10 15 20 25 30 \\
        --instantiations 1 2 3 \\
        --baseline \\
        --out analysis/epoch_perf_qwen7b.csv
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data import test_gen  # noqa: E402
from src.eval.test_gen_scorer import extract_test_file, sanitize_test_file  # noqa: E402


# ── fast scorer (exec + baseline only) ───────────────────────────────────────

def _score_fast(fn_source: str, fn_name: str, test_source: str,
                timeout: int = 60) -> tuple[bool, bool]:
    """Returns (exec_ok, baseline_passed). No mutation scoring.

    TimeoutExpired is caught and treated as exec_ok=False so one slow/hanging
    test cannot crash the entire evaluation run.
    """
    try:
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "under_test.py").write_text(fn_source)
            (tdp / "test_generated.py").write_text(test_source)

            # Exec gate: does the test file import without error?
            r = subprocess.run(
                [sys.executable, "-c", "import test_generated"],
                cwd=td, capture_output=True, timeout=timeout,
            )
            if r.returncode != 0:
                return False, False

            # Baseline: do all tests pass on the correct implementation?
            r = subprocess.run(
                [sys.executable, "-m", "pytest", "test_generated.py",
                 "-x", "-q", "--tb=no", "--no-header"],
                cwd=td, capture_output=True, timeout=timeout,
            )
            return True, (r.returncode == 0)
    except subprocess.TimeoutExpired:
        print(" [timeout]", end="", flush=True)
        return False, False


# ── inference for one (adapter, instantiation) pair ──────────────────────────

def _run_inference(model, tokenizer, problems, gen_cfg: dict) -> list[str]:
    """Return raw response strings for each problem."""
    import torch
    responses = []
    for prob in problems:
        prompt = tokenizer.apply_chat_template(
            prob.messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        torch.manual_seed(gen_cfg.get("seed", 42))
        with torch.inference_mode():
            out_ids = model.generate(
                **inputs,
                max_new_tokens=gen_cfg.get("max_new_tokens", 2048),
                do_sample=gen_cfg.get("do_sample", True),
                temperature=gen_cfg.get("temperature", 0.2),
                top_p=gen_cfg.get("top_p", 1.0),
            )
        new_tokens = out_ids[0][inputs["input_ids"].shape[1]:]
        responses.append(tokenizer.decode(new_tokens, skip_special_tokens=True))
        print(".", end="", flush=True)
    print()
    return responses


def _score_responses(problems, responses, timeout: int) -> dict:
    exec_ok_total = 0
    bp_total = 0
    for prob, resp in zip(problems, responses):
        test_file = extract_test_file(resp)
        test_file, _ = sanitize_test_file(test_file, prob.fn_name)
        exec_ok, bp = _score_fast(prob.source, prob.fn_name, test_file, timeout)
        if exec_ok:
            exec_ok_total += 1
        if bp:
            bp_total += 1
    n = len(problems)
    return {
        "n": n,
        "exec_rate":    round(exec_ok_total / n, 4) if n else None,
        "baseline_pass": round(bp_total / n, 4) if n else None,
    }


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--epochs", type=int, nargs="+",
                        default=[1, 3, 5, 10, 15, 20, 25, 30])
    parser.add_argument("--instantiations", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--baseline", action="store_true",
                        help="Also evaluate epoch 0 (no adapter)")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=60,
                        help="Per-problem subprocess timeout in seconds")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    model_cfg  = cfg["model"]
    train_cfg  = cfg["training"]
    ckpt_base  = ROOT / train_cfg["output_dir"]

    out_path = args.out or ROOT / f"analysis/epoch_perf_{cfg['name']}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume: read already-completed (epoch, instantiation) pairs.
    fieldnames = ["model", "epoch", "instantiation", "n", "exec_rate", "baseline_pass"]
    done_pairs: set[tuple[int, int]] = set()
    if out_path.exists():
        with out_path.open(newline="") as f:
            for row in csv.DictReader(f):
                done_pairs.add((int(row["epoch"]), int(row["instantiation"])))
        print(f"Resuming: {len(done_pairs)} (epoch, inst) pairs already in {out_path.name}")
    else:
        with out_path.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()

    gen_cfg = {
        "max_new_tokens": 2048,
        "do_sample": True,
        "temperature": 0.2,
        "top_p": 1.0,
        "seed": 42,
    }

    # ── load base model (once) ────────────────────────────────────────────────
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    from peft.utils import set_peft_model_state_dict

    os.environ.setdefault("HF_HOME",
        f"/mnt/scratch2/users/{os.environ['USER']}/.huggingface")

    dtype = torch.bfloat16 if model_cfg.get("dtype") == "bfloat16" else torch.float32
    print(f"Loading base model: {model_cfg['id']}")
    tokenizer = AutoTokenizer.from_pretrained(
        model_cfg["id"], revision=model_cfg["revision"], local_files_only=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base = AutoModelForCausalLM.from_pretrained(
        model_cfg["id"], revision=model_cfg["revision"],
        dtype=dtype, device_map="auto", local_files_only=True,
    )
    base.eval()

    # ── discover checkpoint dirs ──────────────────────────────────────────────
    # SFTTrainer names them checkpoint-<step>. Map epoch → step dir.
    # steps_per_epoch = ceil(n_train / effective_batch) — read from saved state.
    ckpt_dirs = sorted(ckpt_base.glob("checkpoint-*"),
                       key=lambda p: int(p.name.split("-")[1]))
    if not ckpt_dirs:
        raise FileNotFoundError(f"No checkpoints found in {ckpt_base}")

    n_ckpts = len(ckpt_dirs)
    steps_per_epoch = int(ckpt_dirs[0].name.split("-")[1])  # epoch 1 step count
    print(f"Found {n_ckpts} checkpoints, steps/epoch ≈ {steps_per_epoch}")

    def _ckpt_for_epoch(ep: int) -> Path | None:
        step = ep * steps_per_epoch
        # Allow ±1 step tolerance for rounding
        for d in ckpt_dirs:
            s = int(d.name.split("-")[1])
            if abs(s - step) <= 1:
                return d
        return None

    # ── preload problems for all instantiations ───────────────────────────────
    print("Loading problems from template engine…")
    inst_problems: dict[int, list] = {}
    for inst_id in args.instantiations:
        inst_problems[inst_id] = test_gen.load(
            instantiation_id=str(inst_id),
            instantiation_seed=inst_id,
            instance_seeds=(101, 102, 103, 104, 105),
            tiers=("L1", "L2"),
            prompting_condition="zero_shot",
        )
        print(f"  inst{inst_id}: {len(inst_problems[inst_id])} problems")

    # ── evaluate ──────────────────────────────────────────────────────────────
    epochs_to_eval = ([0] if args.baseline else []) + list(args.epochs)
    peft_model = None  # will be created on first adapter load

    for epoch in epochs_to_eval:
        if epoch == 0:
            # Baseline: no adapter
            model = base
            print(f"\n=== Epoch 0 (baseline, no adapter) ===")
        else:
            ckpt_dir = _ckpt_for_epoch(epoch)
            if ckpt_dir is None:
                print(f"  WARNING: no checkpoint found for epoch {epoch}, skipping")
                continue
            print(f"\n=== Epoch {epoch} ({ckpt_dir.name}) ===")

            if peft_model is None:
                # First adapter load — wrap base model
                peft_model = PeftModel.from_pretrained(base, str(ckpt_dir))
                peft_model.eval()
            else:
                # Hot-swap: load new adapter weights without reloading base model
                import safetensors.torch as st
                adapter_file = ckpt_dir / "adapter_model.safetensors"
                if not adapter_file.exists():
                    adapter_file = ckpt_dir / "adapter_model.bin"
                state = st.load_file(str(adapter_file)) if adapter_file.suffix == ".safetensors" \
                    else torch.load(str(adapter_file), map_location="cpu")
                set_peft_model_state_dict(peft_model, state)
            model = peft_model

        for inst_id in args.instantiations:
            if (epoch, inst_id) in done_pairs:
                print(f"  inst{inst_id}: already done, skipping")
                continue

            problems = inst_problems[inst_id]
            print(f"  inst{inst_id}: generating {len(problems)} responses…", flush=True)
            responses = _run_inference(model, tokenizer, problems, gen_cfg)

            print(f"  inst{inst_id}: scoring…", flush=True)
            scores = _score_responses(problems, responses, args.timeout)

            row = {
                "model":          model_cfg["id"],
                "epoch":          epoch,
                "instantiation":  inst_id,
                "n":              scores["n"],
                "exec_rate":      scores["exec_rate"],
                "baseline_pass":  scores["baseline_pass"],
            }
            # Write immediately so partial progress survives a crash.
            with out_path.open("a", newline="") as f:
                csv.DictWriter(f, fieldnames=fieldnames).writerow(row)
            done_pairs.add((epoch, inst_id))

            print(f"  inst{inst_id}: exec={scores['exec_rate']:.1%}  "
                  f"baseline_pass={scores['baseline_pass']:.1%}")

    print(f"\nResults saved: {out_path}")


if __name__ == "__main__":
    main()
