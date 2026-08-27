"""Plot Gate C Stage 3c's epoch-onset curve, styled to mirror
scripts/plot_epoch_perf.py (the supplementary study's own epoch curves),
same colour/linestyle language (seen=red solid, unseen=blue dashed,
dynamic=purple dotted) so the two experiments read as mirror images.

Top panel: baseline_pass_rate, all three splits (seen/unseen/dynamic_l1l2).
Bottom panel: verbatim-match rate (exact), seen split only, the sharper
memorization-onset diagnostic this canonical experiment adds. Both panels
include epoch 0 (PRE, hardcoded 0%) and epoch 30 (Stage 3a/3b, full n=112/
288/150) as anchors alongside the epochs {1,3,5,10,20} subsample. Panels
are stacked one above the other, not side by side (changed 2026-08-27,
print-legibility pass): stacking keeps each panel close to the paper's
actual single-column print width, so \includegraphics[width=\columnwidth]
applies almost no further shrink and axis/legend text stays readable in
print instead of shrinking by the ~3.7x a side-by-side layout at this same
content size would need.

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
from _figure_style import COL_W, apply_style  # noqa: E402

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
    # "epoch series" (not "control"), per RUBRIC_ACTION_PLAN.md C-9: this
    # plotted L1/L2 series and the L1--L3 population Section 4.1's prose
    # quotes at the pre/post endpoints are two different populations: the
    # unambiguous name difference is the fix, not a caption footnote.
    "dynamic_l1l2": {"color": "#9467bd", "linestyle": ":",  "marker": "^", "label": "DyMuT L1--L2 (epoch series)"},
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

    apply_style()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Stacked, not side-by-side (kept from the prior print-legibility pass,
    # see module docstring): each panel at the actual column width so
    # \includegraphics[width=\columnwidth] applies almost no further shrink.
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(COL_W, 2 * COL_W * 0.62),
                                    constrained_layout=True)

    for split, style in SPLIT_STYLE.items():
        epochs = sorted(bp_by_split_epoch[split].keys())
        vals = [sum(bp_by_split_epoch[split][e]) / len(bp_by_split_epoch[split][e]) * 100 for e in epochs]
        epochs_full = [0] + epochs + [30]
        vals_full = [0.0] + vals + [epoch30[split] * 100]
        ax1.plot(epochs_full, vals_full, label=style["label"], markersize=4, linewidth=1.2,
                 color=style["color"], linestyle=style["linestyle"], marker=style["marker"])

    # Two-timescale annotation (see analysis/COMPARISON_C_INTERPRETATION.md's
    # "Onset curve -- two timescales, not one"): a fast, one-time
    # generic-improvement jump shared by all three arms at epoch 0->1, then a
    # slower, seen-ULT-only memorization climb from epoch 5 onward. The full
    # argument (including the epoch ranges) is in the caption; these two
    # in-axes labels only need to mark *which region* they refer to.
    ax1.axvline(1, color="gray", linestyle="-", linewidth=0.8, alpha=0.6, zorder=0)
    ax1.annotate("generic gain", xy=(1, 27), xytext=(3.2, 58),
                 fontsize=7, color="dimgray", ha="left",
                 arrowprops=dict(arrowstyle="->", color="dimgray", alpha=0.7))
    ax1.axvspan(5, 20, color="#d62728", alpha=0.06, zorder=0)
    ax1.annotate("memorization", xy=(12, 72), xytext=(12, 92),
                 fontsize=7, color="#d62728", ha="center",
                 arrowprops=dict(arrowstyle="->", color="#d62728", alpha=0.7))

    ax1.set_xlabel("Training epoch")
    ax1.set_ylabel("Baseline pass rate (%)")
    ax1.text(0.02, 0.95, "(a)", transform=ax1.transAxes, fontsize=8, fontweight="bold", va="top")
    ax1.legend(loc="lower center", bbox_to_anchor=(0.62, 0.0), frameon=False,
               handlelength=1.6, labelspacing=0.3)
    ax1.set_ylim(0, 105)
    ax1.grid(True, linestyle="--", linewidth=0.4, alpha=0.4)

    epochs = sorted(verb_by_epoch.keys())
    vals = [sum(verb_by_epoch[e]) / len(verb_by_epoch[e]) * 100 for e in epochs]
    epochs_full = [0] + epochs + [30]
    vals_full = [0.0] + vals + [100.0]  # epoch 30: 112/112 exact match, PROVENANCE.md
    ax2.plot(epochs_full, vals_full, label="seen-ULT verbatim match", markersize=4, linewidth=1.2,
             color=SPLIT_STYLE["seen"]["color"], linestyle="-", marker="o")
    ax2.set_xlabel("Training epoch")
    ax2.set_ylabel("Verbatim-match rate (%)")
    ax2.text(0.02, 0.95, "(b)", transform=ax2.transAxes, fontsize=8, fontweight="bold", va="top")
    ax2.legend(frameon=False, handlelength=1.6)
    ax2.set_ylim(0, 105)
    ax2.grid(True, linestyle="--", linewidth=0.4, alpha=0.4)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=400, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(OUT_PATH.with_suffix(".png"), dpi=400, bbox_inches="tight", pad_inches=0.02)

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
