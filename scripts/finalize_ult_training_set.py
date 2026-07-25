"""Final fine-tune-readiness filter for the Comparison C ULT training set.

scripts/repair_ult_ground_truth.py verifies each pair is functionally
correct (baseline_passed=True); it says nothing about whether the pair
actually FITS the fine-tune's context window. Checked while preparing STOP
GATE B: a handful of ULT `code` blobs are enormous (max ~116k tokens in a
300-example sample -- one exceeds even Qwen2.5-Coder-1.5B's own 32,768-token
position-embedding limit). configs/finetune_qwen1_5b_ult_30ep.yaml's
max_length=3072 (matching the six existing runs) would silently truncate
these mid-`code`-block, before the sequence ever reaches the assistant's
test-file completion -- training on a truncated example like that spends a
full step's compute for zero actual learning signal on the target, not a
harmless approximation.

This script tokenizes every verified pair with the actual target-model
tokenizer and drops any example whose full (system+user+assistant)
token count exceeds `--max-length`, writing the survivors to
data/finetune/train_ult_final.jsonl -- the file the fine-tune config should
actually point at. scripts/build_comparison_c_seen_manifest.py must be
re-run after this (it reads whichever file is passed via --train-file) so
the frozen seen-manifest reflects what was actually trained on, not merely
what was repair-verified.

Usage:
    python scripts/finalize_ult_training_set.py
    python scripts/finalize_ult_training_set.py --max-length 3072
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

IN_PATH = ROOT / "data" / "finetune" / "train_ult_repaired.jsonl"
OUT_PATH = ROOT / "data" / "finetune" / "train_ult_final.jsonl"
MODEL_ID = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
MODEL_REVISION = "2e1fd397ee46e1388853d2af2c993145b0f1098a"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-length", type=int, default=3072)
    parser.add_argument("--in-file", type=Path, default=IN_PATH)
    parser.add_argument("--out-file", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    os.environ.setdefault("HF_HOME", f"/mnt/scratch2/users/{os.environ['USER']}/.huggingface")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION, local_files_only=True)

    records = [json.loads(l) for l in args.in_file.read_text().splitlines() if l.strip()]
    print(f"Loaded {len(records)} verified pairs from {args.in_file}")

    kept, dropped = [], []
    lengths = []
    for d in records:
        text = tok.apply_chat_template(d["messages"], tokenize=False, add_generation_prompt=False)
        n_tok = len(tok(text, add_special_tokens=False)["input_ids"])
        lengths.append(n_tok)
        if n_tok <= args.max_length:
            kept.append(d)
        else:
            dropped.append((d["template_id"], n_tok))

    args.out_file.parent.mkdir(parents=True, exist_ok=True)
    with args.out_file.open("w") as fh:
        for d in kept:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")

    lengths.sort()
    n = len(lengths)
    print(f"\nToken-length distribution (n={n}): "
          f"mean={sum(lengths)/n:.0f} p50={lengths[n//2]} "
          f"p90={lengths[int(n*0.9)]} p99={lengths[int(n*0.99)]} max={lengths[-1]}")
    print(f"\nDropped {len(dropped)} example(s) exceeding max_length={args.max_length}:")
    for tid, n_tok in dropped:
        print(f"  {tid}: {n_tok} tokens")
    print(f"\nKept {len(kept)}/{len(records)} -> {args.out_file}")


if __name__ == "__main__":
    main()
