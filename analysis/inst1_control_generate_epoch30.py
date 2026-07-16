"""One-off inference pass (inst1-control investigation addendum): load the
epoch-30 inst1-condition LoRA adapter, greedy-generate test files for
inst1/inst2/inst3 (150 problems each), and dump raw per-problem results for
offline comparison against the inst1 training targets and a paired
seen-vs-unseen McNemar test.

Explicitly authorized as ONE inference pass beyond the otherwise read-only
inst1-control investigation -- see the addendum in
analysis/reports/inst1_control_verification.md. Reuses eval_checkpoints.py's
actual functions (imported, not reimplemented) so generation uses identical
prompts/params to every other checkpoint eval in this project:
_run_inference (same generation config, same _TimeLimitCriteria,
_ProcessWatchdog support), _score_fast (same exec-gate + baseline-pass
scoring), adapter_weights_hash (same provenance hash), and the same
test_gen.load() problem reconstruction eval_checkpoints.py uses.

Unlike eval_checkpoints.py's own CSV output, this script keeps the raw
per-problem text and per-problem pass/fail -- that's the entire point: the
prior investigation found eval_checkpoints.py discards both by design,
which blocked the literal step-E/F checks.

Submit via SLURM, not on the login node -- see
scripts/slurm/run_inst1_control_generate_epoch30.slurm.

Usage:
    python analysis/inst1_control_generate_epoch30.py \\
        --config configs/finetune_qwen1_5b_inst1_30ep.yaml --epoch 30 \\
        --out analysis/derived/inst1_control_epoch30_generation_qwen1_5b.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import eval_checkpoints as ec  # noqa: E402
from src.data import test_gen  # noqa: E402
from src.eval.test_gen_scorer import extract_test_file, sanitize_test_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--epoch", type=int, default=30)
    parser.add_argument("--instantiations", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--gen-max-seconds", type=float, default=ec.DEFAULT_MAX_SECONDS)
    parser.add_argument("--watchdog-timeout", type=float, default=ec.WATCHDOG_TIMEOUT_S)
    parser.add_argument("--timeout", type=int, default=60, help="Per-problem scoring subprocess timeout")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    model_cfg = cfg["model"]
    train_cfg = cfg["training"]
    ckpt_base = ROOT / train_cfg["output_dir"]

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    os.environ.setdefault("HF_HOME", f"/mnt/scratch2/users/{os.environ['USER']}/.huggingface")

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

    # ── discover checkpoint dirs, same epoch->step mapping eval_checkpoints.py uses ──
    ckpt_dirs = sorted(ckpt_base.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1]))
    if not ckpt_dirs:
        raise FileNotFoundError(f"No checkpoints found in {ckpt_base}")
    steps_per_epoch = int(ckpt_dirs[0].name.split("-")[1])

    def _ckpt_for_epoch(ep: int) -> Path | None:
        step = ep * steps_per_epoch
        for d in ckpt_dirs:
            if abs(int(d.name.split("-")[1]) - step) <= 1:
                return d
        return None

    ckpt_dir = _ckpt_for_epoch(args.epoch)
    if ckpt_dir is None:
        raise FileNotFoundError(f"no checkpoint found for epoch {args.epoch} in {ckpt_base}")
    print(f"Using checkpoint: {ckpt_dir}")
    adapter_path = str(ckpt_dir)
    adapter_hash = ec.adapter_weights_hash(ckpt_dir)
    print(f"adapter_weights_hash: {adapter_hash}")

    peft_model = PeftModel.from_pretrained(base, str(ckpt_dir))
    peft_model.eval()

    watchdog = None
    if args.watchdog_timeout > 0:
        watchdog = ec._ProcessWatchdog(args.watchdog_timeout).start()
        print(f"Watchdog armed: {args.watchdog_timeout}s per generate() call")

    # Resume support + incremental writes: a batched single write-at-the-end
    # (the original version of this script) loses ALL results if the SLURM
    # job is killed at its time limit before every instantiation finishes --
    # found the hard way when a first attempt's throughput estimate turned
    # out to be ~6x too optimistic for V100. Each problem's record is now
    # appended immediately after scoring, and any (instantiation, template_id,
    # instance_seed) already present in --out is skipped, so a resubmit after
    # a timeout picks up where it left off instead of redoing finished work.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    done_keys: set[tuple[int, str, int]] = set()
    if args.out.exists():
        with args.out.open() as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    done_keys.add((r["instantiation"], r["template_id"], r["instance_seed"]))
        print(f"Resuming: {len(done_keys)} problems already in {args.out}")

    out_file = args.out.open("a")
    n_written = 0
    for inst_id in args.instantiations:
        problems = test_gen.load(
            instantiation_id=str(inst_id),
            instantiation_seed=inst_id,
            instance_seeds=(101, 102, 103, 104, 105),
            tiers=("L1", "L2"),
            prompting_condition="zero_shot",
        )
        todo = [p for p in problems if (inst_id, p.template_id, p.instance_seed) not in done_keys]
        if not todo:
            print(f"inst{inst_id}: all {len(problems)} problems already done, skipping")
            continue
        print(f"inst{inst_id}: {len(todo)}/{len(problems)} problems to generate (greedy)…", flush=True)
        responses = ec._run_inference(
            peft_model, tokenizer, todo, do_sample=False, seed=None,
            max_seconds=args.gen_max_seconds, watchdog=watchdog,
        )

        n_exec = n_bp = 0
        for prob, raw in zip(todo, responses):
            extracted = extract_test_file(raw)
            sanitized, repairs = sanitize_test_file(extracted, prob.fn_name)
            exec_ok, baseline_passed = ec._score_fast(prob.source, prob.fn_name, sanitized, timeout=args.timeout)
            n_exec += int(exec_ok)
            n_bp += int(baseline_passed)
            record = {
                "model":                model_cfg["id"],
                "epoch":                args.epoch,
                "instantiation":        inst_id,
                "template_id":          prob.template_id,
                "instance_seed":        prob.instance_seed,
                "tier":                 prob.tier,
                "adapter_path":         adapter_path,
                "adapter_weights_hash": adapter_hash,
                "raw_response":         raw,
                "extracted_test_file":  extracted,
                "sanitized_test_file":  sanitized,
                "sanitize_repairs":     repairs,
                "exec_ok":              exec_ok,
                "baseline_passed":      baseline_passed,
            }
            out_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_file.flush()
            n_written += 1
        print(f"  inst{inst_id}: exec_ok={n_exec}/{len(todo)}  baseline_passed={n_bp}/{len(todo)}")

    out_file.close()
    if watchdog is not None:
        watchdog.stop()

    print(f"\nWrote {n_written} new records to {args.out} "
          f"({len(done_keys) + n_written} total)")


if __name__ == "__main__":
    main()
