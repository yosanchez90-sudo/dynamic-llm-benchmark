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

from src.Analysis.provenance import stamp_block  # noqa: E402

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

    # Two-timescale annotation (see analysis/COMPARISON_C_INTERPRETATION.md's
    # "Onset curve -- two timescales, not one"): a fast, one-time
    # generic-improvement jump shared by all three arms at epoch 0->1, then a
    # slower, seen-ULT-only memorization climb from epoch 5 onward. Marking
    # both directly on the figure so a reader doesn't mistake this for one
    # smooth trend.
    ax1.axvline(1, color="gray", linestyle="-", linewidth=0.8, alpha=0.6, zorder=0)
    ax1.annotate("generic gain\n(all arms, epoch 0→1)", xy=(1, 27), xytext=(3.2, 55),
                 fontsize=8.5, color="dimgray", ha="left",
                 arrowprops=dict(arrowstyle="->", color="dimgray", alpha=0.7))
    ax1.axvspan(5, 20, color="#d62728", alpha=0.06, zorder=0)
    ax1.annotate("memorization\n(seen-ULT only, epochs 5‒20)", xy=(12, 72), xytext=(12, 88),
                 fontsize=8.5, color="#d62728", ha="center",
                 arrowprops=dict(arrowstyle="->", color="#d62728", alpha=0.7))

    ax1.set_xlabel("Training epoch", fontsize=11)
    ax1.set_ylabel("Baseline pass rate (%)", fontsize=11)
    ax1.set_title("Comparison C onset curve — baseline pass rate", fontsize=12)
    ax1.legend(fontsize=9, loc="center right")
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

    fig.suptitle(
        "Two timescales: a shared, one-time generic-improvement jump (epoch 0→1, all arms) "
        "vs. a slower, seen-ULT-only memorization climb (epochs 5→20)",
        fontsize=9.5, color="#333333", y=1.02,
    )
    fig.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_PATH.with_suffix(".png"), dpi=150, bbox_inches="tight")

    provenance = f"""# Comparison C onset-curve figure — provenance

{stamp_block("scripts/plot_comparison_c_onset_curve.py")}
Sources: {ONSET_CSV.relative_to(ROOT)} (epochs {{1,3,5,10,20}} subsample),
{MANIFEST.relative_to(ROOT)} (fixed subsample IDs for the epoch-0/epoch-30
anchors), {POST_ULT_FILE.relative_to(ROOT)} and
{[str(p.relative_to(ROOT)) for p in POST_DYN_L1L2_FILES]} (epoch-30 anchor,
full-n Stage 3a/3b landed results, not re-run).

Output: {OUT_PATH.relative_to(ROOT)} (+ .png).
"""
    # NOT alongside the figure: analysis/figures/ is entirely gitignored
    # (.gitignore:49), so a sidecar written there would never be committed --
    # defeating the point of stamping it. Root of analysis/, like every other
    # *_PROVENANCE.md, is only ignored for .csv/.xlsx (.gitignore:47-48).
    PROVENANCE_OUT = ROOT / "analysis" / (OUT_PATH.stem + "_PROVENANCE.md")
    PROVENANCE_OUT.write_text(provenance)
    print(f"Saved: {OUT_PATH} and .png, {PROVENANCE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
