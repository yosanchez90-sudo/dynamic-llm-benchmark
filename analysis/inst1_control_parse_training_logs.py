"""Read-only helper for the inst1-control investigation (steps B and C):
parse SLURM training stdout logs into a structured per-step loss/lr/grad_norm
table, and print schedule-sanity numbers (steps/epoch, total steps, warmup
steps vs total, first/last loss, relative drop).

Does not touch any pipeline code or launch anything -- pure log parsing.

Usage:
    python analysis/inst1_control_parse_training_logs.py \\
        --log logs/finetune-30ep-9264922.out --config configs/finetune_qwen1_5b_inst1_30ep.yaml
"""
from __future__ import annotations

import argparse
import ast
import math
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

STEP_LINE = re.compile(r"^\{'loss':.*'epoch': [\d.]+\}$")


def parse_log(log_path: Path) -> list[dict]:
    """Return the list of per-logging-step dicts HF Trainer printed
    (ast.literal_eval on each '{...}' line), in file order."""
    steps = []
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if STEP_LINE.match(line):
            steps.append(ast.literal_eval(line))
    return steps


def schedule_summary(config_path: Path, n_train_examples: int, steps: list[dict]) -> dict:
    cfg = yaml.safe_load(config_path.read_text())
    t = cfg["training"]
    per_device_bs = t["per_device_train_batch_size"]
    grad_accum = t["gradient_accumulation_steps"]
    world_size = 1  # single-GPU training throughout (see SLURM logs: 1 GPU requested)
    effective_bs = per_device_bs * grad_accum * world_size
    steps_per_epoch = math.ceil(n_train_examples / effective_bs)
    total_steps = steps_per_epoch * t["num_train_epochs"]
    warmup_steps = math.floor(t.get("warmup_ratio", 0.0) * total_steps)

    lrs = [s["learning_rate"] for s in steps if "learning_rate" in s]
    grad_norms = [s["grad_norm"] for s in steps if "grad_norm" in s]
    losses = [s["loss"] for s in steps if "loss" in s]

    return {
        "config": str(config_path),
        "n_train_examples": n_train_examples,
        "effective_batch_size": effective_bs,
        "steps_per_epoch": steps_per_epoch,
        "num_train_epochs": t["num_train_epochs"],
        "total_steps": total_steps,
        "warmup_ratio": t.get("warmup_ratio"),
        "warmup_steps": warmup_steps,
        "warmup_lt_total": warmup_steps < total_steps,
        "peak_lr_reached": max(lrs) if lrs else None,
        "configured_lr": t["learning_rate"],
        "peak_lr_pct_of_configured": (max(lrs) / t["learning_rate"] * 100) if lrs else None,
        "final_lr": lrs[-1] if lrs else None,
        "any_zero_grad_norm": any(g == 0 for g in grad_norms),
        "min_grad_norm": min(grad_norms) if grad_norms else None,
        "max_grad_norm": max(grad_norms) if grad_norms else None,
        "first_loss": losses[0] if losses else None,
        "last_loss": losses[-1] if losses else None,
        "relative_drop_pct": ((losses[0] - losses[-1]) / losses[0] * 100) if losses else None,
        "n_logged_steps": len(steps),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--n-train-examples", type=int, default=None,
                         help="Override; otherwise parsed from the log's "
                              "'After quality filter' line")
    args = parser.parse_args()

    text = args.log.read_text()
    n = args.n_train_examples
    if n is None:
        m = re.search(r"After quality filter \([^)]+\): (\d+) training examples", text)
        if not m:
            raise SystemExit(f"could not find training-example count in {args.log}; pass --n-train-examples")
        n = int(m.group(1))

    steps = parse_log(args.log)
    summary = schedule_summary(args.config, n, steps)
    for k, v in summary.items():
        print(f"{k:28s} {v}")


if __name__ == "__main__":
    main()
