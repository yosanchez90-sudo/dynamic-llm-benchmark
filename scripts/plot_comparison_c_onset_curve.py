"""Plot Gate C Stage 3c's epoch-onset curve, styled to mirror
scripts/plot_epoch_perf.py (the supplementary study's own epoch curves) --
same colour/linestyle language (seen=red solid, unseen=blue dashed,
dynamic=purple dotted) so the two experiments read as mirror images.

Left panel: baseline_pass_rate, all three splits (seen/unseen/dynamic_l1l2).
Right panel: verbatim-match rate (exact), seen split only -- the sharper
memorization-onset diagnostic this canonical experiment adds. Both panels
include epoch 0 (PRE, hardcoded 0%) and epoch 30 (Stage 3a/3b, full n=112/
288/150) as anchors alongside the epochs {1,3,5,10,20} subsample.

Usage: python scripts/plot_comparison_c_onset_curve.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ONSET_CSV = ROOT / "analysis" / "comparison_c_onset_curve.csv"
MANIFEST = ROOT / "data" / "raw" / "ult_plt" / "comparison_c_onset_curve_manifest.json"
POST_ULT_FILE = ROOT / "data/results/ult/Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep__ult__zero_shot__instcore_400__20260726T142439.jsonl"
POST_DYN_L1L2_FILES = [
    ROOT / f"data/results/dynamic/Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep__dynamic__zero_shot__inst{i}__tiersL1L2__20260726T234427.jsonl"
    for i in (1,)
]
TRAIN_FILE = ROOT / "data" / "finetune" / "train_ult_final.jsonl"
OUT_PATH = ROOT / "analysis" / "figures" / "comparison_c_onset_curve.pdf"

SPLIT_STYLE = {
    "seen":         {"color": "#d62728", "linestyle": "-",  "marker": "o", "label": "seen-ULT (train)"},
    "unseen":       {"color": "#1f77b4", "linestyle": "--", "marker": "s", "label": "unseen-ULT (held-out)"},
    "dynamic_l1l2": {"color": "#9467bd", "linestyle": ":",  "marker": "^", "label": "Dynamic L1/L2 (control)"},
}


def _epoch30_anchor():
    """epoch-30 baseline_pass_rate on the SAME fixed subsample IDs, from the
    already-landed full-n Stage 3a/3b files (not re-run)."""
    manifest = json.loads(MANIFEST.read_text())
    seen_ids = set(manifest["ult_seen"]["task_ids"])
    unseen_ids = set(manifest["ult_unseen"]["task_ids"])
    dyn_pairs = {(p["template_id"], p["instance_seed"])
                 for p in manifest["dynamic_l1l2_inst1"]["problems"]}

    seen_bp, unseen_bp = [], []
    for line in POST_ULT_FILE.read_text().splitlines():
        r = json.loads(line)
        tid = r["template_id"].split("-", 1)[1]
        if tid in seen_ids:
            seen_bp.append(1.0 if r["baseline_passed"] else 0.0)
        elif tid in unseen_ids:
            unseen_bp.append(1.0 if r["baseline_passed"] else 0.0)

    dyn_bp = []
    for fp in POST_DYN_L1L2_FILES:
        for line in fp.read_text().splitlines():
            r = json.loads(line)
            if (r["template_id"], r["instance_seed"]) in dyn_pairs:
                dyn_bp.append(1.0 if r["baseline_passed"] else 0.0)

    return {
        "seen": sum(seen_bp) / len(seen_bp) if seen_bp else None,
        "unseen": sum(unseen_bp) / len(unseen_bp) if unseen_bp else None,
        "dynamic_l1l2": sum(dyn_bp) / len(dyn_bp) if dyn_bp else None,
    }


def main() -> None:
    rows = list(csv.DictReader(ONSET_CSV.open()))

    bp_by_split_epoch: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    verb_by_epoch: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        epoch = int(r["epoch"])
        split = r["split"]
        bp_by_split_epoch[split][epoch].append(1.0 if r["baseline_passed"] == "True" else 0.0)
        if split == "seen":
            verb_by_epoch[epoch].append(1.0 if r["verbatim_exact"] == "True" else 0.0)

    epoch30 = _epoch30_anchor()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5))

    for split, style in SPLIT_STYLE.items():
        epochs = sorted(bp_by_split_epoch[split].keys())
        vals = [sum(bp_by_split_epoch[split][e]) / len(bp_by_split_epoch[split][e]) * 100 for e in epochs]
        epochs_full = [0] + epochs + [30]
        vals_full = [0.0] + vals + [epoch30[split] * 100]
        ax1.plot(epochs_full, vals_full, label=style["label"],
                 color=style["color"], linestyle=style["linestyle"], marker=style["marker"])

    ax1.set_xlabel("Training epoch", fontsize=11)
    ax1.set_ylabel("Baseline pass rate (%)", fontsize=11)
    ax1.set_title("Comparison C onset curve — baseline pass rate", fontsize=12)
    ax1.legend(fontsize=9)
    ax1.set_ylim(0, 105)
    ax1.grid(True, linestyle="--", alpha=0.4)

    epochs = sorted(verb_by_epoch.keys())
    vals = [sum(verb_by_epoch[e]) / len(verb_by_epoch[e]) * 100 for e in epochs]
    epochs_full = [0] + epochs + [30]
    vals_full = [0.0] + vals + [100.0]  # epoch 30: 112/112 exact match, PROVENANCE.md
    ax2.plot(epochs_full, vals_full, label="seen-ULT verbatim match",
             color=SPLIT_STYLE["seen"]["color"], linestyle="-", marker="o")
    ax2.set_xlabel("Training epoch", fontsize=11)
    ax2.set_ylabel("Verbatim-match rate (%)", fontsize=11)
    ax2.set_title("Comparison C onset curve — verbatim reproduction (seen-ULT)", fontsize=12)
    ax2.legend(fontsize=9)
    ax2.set_ylim(0, 105)
    ax2.grid(True, linestyle="--", alpha=0.4)

    fig.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150)
    fig.savefig(OUT_PATH.with_suffix(".png"), dpi=150)
    print(f"Saved: {OUT_PATH} and .png")


if __name__ == "__main__":
    main()
