"""Comparison C analysis (RQ1 / H2): assemble pre/post Dynamic-benchmark
frames for each fine-tuned Qwen checkpoint and run the DiD estimator
(src/Contamination/did.py) against whatever benchmarks actually have data
on both sides.

As of today only the Dynamic (control) benchmark has real pre AND post
data — ULT/PLT have neither (no model has been evaluated against them yet,
see src/data/ult_plt.py). This script still reports the Dynamic control's
own pre->post change directly (useful on its own: "did fine-tuning move the
needle on a benchmark it wasn't trained on"), and states plainly why the
full 2x3 DiD table is empty rather than silently producing nothing.

Usage:
    python scripts/analyze_contamination.py
    python scripts/analyze_contamination.py --config configs/finetune_qwen7b_bp_gpt5_30ep.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.Contamination.data import (  # noqa: E402
    CAVEAT_METRIC, DEFAULT_RESULTS_ROOT, RECOMMENDED_METRIC,
    load_pre_post_for_config, load_pre_post_same_instrument,
)
from src.Contamination.did import compute_did, did_table  # noqa: E402

FINETUNE_CONFIGS = [
    "configs/finetune_qwen1_5b_inst1_30ep.yaml",
    "configs/finetune_qwen1_5b_bp_own_30ep.yaml",
    "configs/finetune_qwen1_5b_bp_gpt5_30ep.yaml",
    "configs/finetune_qwen7b_inst1_30ep.yaml",
    "configs/finetune_qwen7b_bp_own_30ep.yaml",
    "configs/finetune_qwen7b_bp_gpt5_30ep.yaml",
]


def analyze_one(config_path: Path) -> None:
    config = yaml.safe_load(config_path.read_text())
    hf_id = config["model"]["id"]
    csv_path = ROOT / DEFAULT_RESULTS_ROOT / f"epoch_perf_{config['name']}.csv"

    print(f"=== {config_path.name} ({hf_id}) ===")
    if not csv_path.exists():
        print(f"  no epoch_perf CSV found at {csv_path}, skipping")
        print()
        return

    try:
        pre, post = load_pre_post_same_instrument(csv_path)
        source_note = "same-instrument (epoch=0 baseline vs final epoch, both via eval_checkpoints.py)"
    except ValueError:
        # No --baseline (epoch=0) rows in this CSV yet — fall back to the
        # cross-source loader (different exec-check instrument pre vs post).
        pre, post = load_pre_post_for_config(hf_id, csv_path)
        source_note = "cross-source (pre from data/results/dynamic/, different instrument — see src/Contamination/data.py)"
    print(f"  pre/post source: {source_note}")

    if pre.empty:
        print(f"  no pre-finetune Dynamic results found for {hf_id}")
        print()
        return
    if post.empty:
        print(f"  no post-finetune rows in {csv_path.name} for the requested epoch/instantiations "
              f"(checkpoint sweep may still be running)")
        print()
        return

    for metric in (RECOMMENDED_METRIC, CAVEAT_METRIC):
        pre_mean = pre[pre["benchmark"] == "dynamic"][metric].mean()
        post_mean = post[post["benchmark"] == "dynamic"][metric].mean()
        tag = ("" if metric == RECOMMENDED_METRIC else
               "  (caveat: exec check differs pre vs post — see src/Contamination/data.py)")
        print(f"  Dynamic control [{metric}]: pre={pre_mean:.3f} -> post={post_mean:.3f} "
              f"(delta={post_mean - pre_mean:+.3f}, n_pre={len(pre)}, n_post={len(post)}){tag}")

    results = compute_did(pre, post, metric=RECOMMENDED_METRIC)
    table = did_table(results)
    if table.empty:
        print("  2x3 DiD table: EMPTY — no treatment benchmark (ULT/PLT) has both pre AND "
              "post data yet. The design needs a model actually evaluated against ULT/PLT "
              "(pre-finetune) and the fine-tuned checkpoint re-evaluated against them (post) "
              "before this table can be filled in — see src/data/ult_plt.py.")
    else:
        print(table.to_string(index=False))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None,
                        help="One finetune config; default runs all 6.")
    args = parser.parse_args()

    configs = [args.config] if args.config else [ROOT / c for c in FINETUNE_CONFIGS]
    for c in configs:
        analyze_one(c)


if __name__ == "__main__":
    main()
