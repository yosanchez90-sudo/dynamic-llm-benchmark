"""Read-only helper for the inst1-control investigation (step D): compute
sum of ||lora_B|| (Frobenius norm, summed across all lora_B tensors) for
each epoch checkpoint of a LoRA run. lora_B initialises at all-zeros in
standard PEFT LoRA init (init_lora_weights=true, confirmed in every
adapter_config.json in this repo), so this norm is 0 at epoch 0 by
construction and its growth across epochs is direct evidence the adapter
weights actually changed during training (or didn't).

Does not touch any pipeline code, load any base model, or launch anything
-- reads adapter_model.safetensors files directly via `safetensors`.

Usage:
    python analysis/inst1_control_lora_b_norms.py \\
        --run-dir data/finetune/qwen1_5b_lora_inst1_30ep
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from safetensors import safe_open

ROOT = Path(__file__).resolve().parent.parent


def lora_b_norm(safetensors_path: Path) -> float:
    total = 0.0
    with safe_open(str(safetensors_path), framework="pt") as f:
        for key in f.keys():
            if "lora_B" in key:
                t = f.get_tensor(key)
                total += float(t.float().norm().item())
    return total


def checkpoint_step(name: str) -> int | None:
    m = re.match(r"checkpoint-(\d+)$", name)
    return int(m.group(1)) if m else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True,
                         help="e.g. data/finetune/qwen1_5b_lora_inst1_30ep")
    parser.add_argument("--steps-per-epoch", type=int, default=None,
                         help="If given, print epoch number alongside step number")
    args = parser.parse_args()

    ckpts = sorted(
        (p for p in args.run_dir.iterdir() if p.is_dir() and checkpoint_step(p.name) is not None),
        key=lambda p: checkpoint_step(p.name),
    )
    if not ckpts:
        raise SystemExit(f"no checkpoint-<N> directories found under {args.run_dir}")

    print(f"{'step':>6s} {'epoch':>7s} {'sum||lora_B||':>16s}  path")
    prev_norm = None
    for ckpt in ckpts:
        st = ckpt / "adapter_model.safetensors"
        if not st.exists():
            print(f"  MISSING adapter_model.safetensors in {ckpt}")
            continue
        step = checkpoint_step(ckpt.name)
        epoch = f"{step / args.steps_per_epoch:.2f}" if args.steps_per_epoch else "?"
        norm = lora_b_norm(st)
        delta = "" if prev_norm is None else f"  (delta {norm - prev_norm:+.4f})"
        print(f"{step:6d} {epoch:>7s} {norm:16.6f}{delta}  {ckpt}")
        prev_norm = norm


if __name__ == "__main__":
    main()
