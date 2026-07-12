"""Evaluate LoRA checkpoints across instantiations to plot performance vs epoch.

Loads the base model ONCE, then hot-swaps adapter weights for each checkpoint
so we don't pay the 14GB reload cost at every epoch. Only runs exec gate +
baseline pass — mutation scoring is skipped to keep runtime tractable
(~15 min per checkpoint × 3 instantiations vs ~6h with mutation).

MEASUREMENT POLICY (fixed 2026-07-12 after a multi-session investigation —
see PROJECT_BRIEF-adjacent notes / analysis/README.md — into a false
"collapse" in three of six fine-tuning conditions):
  - no_repeat_ngram_size is NEVER used here. It was added 2026-07-07 to
    combat a genuine problem (see below) but the fix was wrong: HF's
    generate() applies it over the FULL sequence including the prompt, and
    the system prompt (src/data/test_gen.py:SYSTEM_INSTRUCTION) contains the
    literal phrase "from under_test import <function_name>" as a formatting
    instruction. Any checkpoint that correctly follows that instruction gets
    its own mandatory first line corrupted, because generating it again
    trips the n-gram repeat ban. Confirmed at n=50 (0/50 clean import lines
    with it enabled vs 50/50 with it disabled, under both greedy and
    sampling, independent of repetition_penalty) — this single setting
    explained the entire recorded collapse in three of six conditions.
  - The wall-clock stopping criteria (_TimeLimitCriteria) IS kept — job
    9315777 (2026-07-05, the original bp_gpt5/7B sweep) hung for real: it
    stalled at epoch 5/instantiation 1, generation 73/150, and produced zero
    further output for ~11.5 hours until SLURM force-killed it at the
    12-hour job limit. That was a genuine problem needing a genuine
    safeguard. Its timeout is now deliberately sized rather than inherited:
    measured throughput on V100 for this model is ~20 tok/s (min observed
    15.8 tok/s across 100 timed generations, none of which came anywhere
    near max_new_tokens=2048); at the slowest observed rate a full
    2048-token generation would take ~129s. The default below (240s) clears
    that with ~1.85x headroom while remaining orders of magnitude short of
    an actual hang.
  - repetition_penalty is set explicitly (not left to silently inherit from
    the base model's own generation_config.json — confirmed via explicit A/B
    toggling to have zero effect on the corruption either way, but per
    CLAUDE.md's "resolved generation config is part of run identity" rule,
    an inherited default must never be implicit).
  - Every row logs the full resolved generation config, not just exec/
    baseline outcomes.

Usage:
    python scripts/eval_checkpoints.py \\
        --config configs/finetune_qwen7b_inst1_30ep.yaml \\
        --epochs 1 3 5 10 15 20 25 30 \\
        --instantiations 1 2 3 \\
        --greedy --sampling-seeds 42 43 44

    # Also pass --baseline to include the no-adapter baseline (epoch 0):
    python scripts/eval_checkpoints.py \\
        --config configs/finetune_qwen7b_inst1_30ep.yaml \\
        --epochs 1 3 5 10 15 20 25 30 \\
        --instantiations 1 2 3 \\
        --baseline --greedy --sampling-seeds 42 43 44
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

REPETITION_PENALTY = 1.1  # matches the base model's own inherited generation_config.json
REPETITION_PENALTY_SOURCE = "explicit (matches base model's inherited generation_config.json default)"
DEFAULT_MAX_SECONDS = 240  # see module docstring for how this was sized


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


# ── inference for one (adapter, instantiation, draw) ──────────────────────────

class _TimeLimitCriteria:
    """Stop generation once a wall-clock budget is exceeded — a genuine
    safety net for the real hang recorded in job 9315777 (see module
    docstring), NOT a substitute for no_repeat_ngram_size, which must never
    be re-added here (see module docstring for why).
    """

    def __init__(self, max_seconds: float):
        import time
        self._time = time
        self.deadline = time.monotonic() + max_seconds

    def __call__(self, input_ids, scores, **kwargs):
        import torch
        done = self._time.monotonic() > self.deadline
        return torch.full((input_ids.shape[0],), done, dtype=torch.bool, device=input_ids.device)


def resolved_generation_config(do_sample: bool, seed: int | None, max_seconds: float) -> dict:
    """The full resolved generation config for one draw — logged into every
    result row per CLAUDE.md's "resolved generation config is part of run
    identity" rule.
    """
    return {
        "do_sample": do_sample,
        "temperature": 0.2 if do_sample else None,
        "top_p": 1.0 if do_sample else None,
        "repetition_penalty": REPETITION_PENALTY,
        "repetition_penalty_source": REPETITION_PENALTY_SOURCE,
        "no_repeat_ngram_size": 0,
        "no_repeat_ngram_size_source": "explicitly disabled — see module docstring, confirmed root "
                                        "cause of the 2026-07 false collapse",
        "max_new_tokens": 2048,
        "seed": seed,
        "max_seconds": max_seconds,
    }


def _run_inference(model, tokenizer, problems, do_sample: bool, seed: int | None,
                    max_seconds: float) -> list[str]:
    """Return raw response strings for each problem, for one (do_sample, seed) draw."""
    import torch
    from transformers import StoppingCriteriaList

    responses = []
    for prob in problems:
        prompt = tokenizer.apply_chat_template(
            prob.messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        if seed is not None:
            torch.manual_seed(seed)
        stopping_criteria = StoppingCriteriaList([_TimeLimitCriteria(max_seconds)])
        gen_kwargs: dict = dict(
            max_new_tokens=2048,
            do_sample=do_sample,
            repetition_penalty=REPETITION_PENALTY,
            stopping_criteria=stopping_criteria,
        )
        if do_sample:
            gen_kwargs["temperature"] = 0.2
            gen_kwargs["top_p"] = 1.0
        with torch.inference_mode():
            out_ids = model.generate(**inputs, **gen_kwargs)
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
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--epochs", type=int, nargs="+",
                        default=[1, 3, 5, 10, 15, 20, 25, 30])
    parser.add_argument("--instantiations", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--baseline", action="store_true",
                        help="Also evaluate epoch 0 (no adapter)")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=60,
                        help="Per-problem subprocess timeout in seconds")
    parser.add_argument("--gen-max-seconds", type=float, default=DEFAULT_MAX_SECONDS,
                        help=f"Wall-clock cutoff per generation call, guarding against a genuine "
                             f"hang (see module docstring). Default {DEFAULT_MAX_SECONDS}s, sized "
                             f"empirically from measured throughput, not inherited.")
    parser.add_argument("--greedy", action=argparse.BooleanOptionalAction, default=True,
                        help="Include a greedy (do_sample=False) draw — the primary measurement "
                             "the checkpoint-selection rule gates on (default: on)")
    parser.add_argument("--sampling-seeds", type=int, nargs="*", default=[],
                        help="Seeds for additional temperature=0.2 sampling draws, e.g. "
                             "--sampling-seeds 42 43 44 for the R=3 secondary measurement. "
                             "Empty (default) means no sampling draws.")
    args = parser.parse_args()

    if not args.greedy and not args.sampling_seeds:
        parser.error("at least one of --greedy or --sampling-seeds is required")

    cfg = yaml.safe_load(args.config.read_text())
    model_cfg  = cfg["model"]
    train_cfg  = cfg["training"]
    ckpt_base  = ROOT / train_cfg["output_dir"]

    # New authoritative location — see analysis/README.md for why the old
    # analysis/epoch_perf_*.csv files are quarantined, not overwritten.
    out_path = args.out or ROOT / f"data/results/finetune_rebuild/epoch_perf_{cfg['name']}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    draws: list[tuple[str, bool, int | None]] = []
    if args.greedy:
        draws.append(("greedy", False, None))
    for s in args.sampling_seeds:
        draws.append((f"sampling_seed{s}", True, s))

    # Resume: read already-completed (epoch, instantiation, draw) triples.
    fieldnames = [
        "model", "epoch", "instantiation", "draw", "n", "exec_rate", "baseline_pass",
        "do_sample", "temperature", "top_p", "repetition_penalty",
        "repetition_penalty_source", "no_repeat_ngram_size", "no_repeat_ngram_size_source",
        "max_new_tokens", "seed", "max_seconds",
    ]
    done_triples: set[tuple[int, int, str]] = set()
    if out_path.exists():
        with out_path.open(newline="") as f:
            for row in csv.DictReader(f):
                done_triples.add((int(row["epoch"]), int(row["instantiation"]), row["draw"]))
        print(f"Resuming: {len(done_triples)} (epoch, inst, draw) triples already in {out_path.name}")
    else:
        with out_path.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()

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
            problems = inst_problems[inst_id]

            for draw_label, do_sample, seed in draws:
                if (epoch, inst_id, draw_label) in done_triples:
                    print(f"  inst{inst_id}/{draw_label}: already done, skipping")
                    continue

                print(f"  inst{inst_id}/{draw_label}: generating {len(problems)} responses…", flush=True)
                responses = _run_inference(model, tokenizer, problems, do_sample, seed,
                                            args.gen_max_seconds)

                print(f"  inst{inst_id}/{draw_label}: scoring…", flush=True)
                scores = _score_responses(problems, responses, args.timeout)
                resolved = resolved_generation_config(do_sample, seed, args.gen_max_seconds)

                row = {
                    "model":          model_cfg["id"],
                    "epoch":          epoch,
                    "instantiation":  inst_id,
                    "draw":           draw_label,
                    "n":              scores["n"],
                    "exec_rate":      scores["exec_rate"],
                    "baseline_pass":  scores["baseline_pass"],
                    **resolved,
                }
                # Write immediately so partial progress survives a crash.
                with out_path.open("a", newline="") as f:
                    csv.DictWriter(f, fieldnames=fieldnames).writerow(row)
                done_triples.add((epoch, inst_id, draw_label))

                print(f"  inst{inst_id}/{draw_label}: exec={scores['exec_rate']:.1%}  "
                      f"baseline_pass={scores['baseline_pass']:.1%}")

    print(f"\nResults saved: {out_path}")


if __name__ == "__main__":
    main()
