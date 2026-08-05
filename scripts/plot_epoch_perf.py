"""Plot performance-vs-epoch curves for the contamination-simulation experiment.

Reads the CSV produced by eval_checkpoints.py and plots one line per
instantiation (inst1 = training set, inst2/inst3 = held-out), showing
how baseline_pass evolves across training epochs.

Usage:
    python scripts/plot_epoch_perf.py \\
        --csv analysis/epoch_perf_finetune_qwen7b_inst1_30ep.csv \\
        --metric baseline_pass \\
        --out analysis/figures/epoch_perf_qwen7b.pdf

    # Overlay two models on one plot:
    python scripts/plot_epoch_perf.py \\
        --csv analysis/epoch_perf_finetune_qwen7b_inst1_30ep.csv \\
              analysis/epoch_perf_finetune_qwen1_5b_inst1_30ep.csv \\
        --metric baseline_pass \\
        --out analysis/figures/epoch_perf_combined.pdf

NOTE on --draw: the finetune_rebuild/epoch_perf_*.csv files (written by the
post-2026-07-12 eval_checkpoints.py) carry a greedy row for every epoch PLUS
3 extra sampling_seed{42,43,44} rows at epoch 30 only (R=3 secondary draws).
plot() groups purely by (instantiation, epoch) x-position, so leaving all
draws in would put 4 stacked points at x=30 per instantiation and draw a
zigzag between them. --draw greedy (the default) keeps one consistent
value per epoch, which is what a curve needs; the sampling draws are a
separate endpoint-table concern (mean+-SD at epoch 30), not part of the
curve.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.Analysis.provenance import stamp_block  # noqa: E402


INST_LABELS = {
    1: "inst1 (train)",
    2: "inst2 (held-out)",
    3: "inst3 (held-out)",
}

# Colours and styles per instantiation — consistent across plots
INST_STYLE = {
    1: {"color": "#d62728", "linestyle": "-",  "marker": "o"},  # red, solid
    2: {"color": "#1f77b4", "linestyle": "--", "marker": "s"},  # blue, dashed
    3: {"color": "#9467bd", "linestyle": ":",  "marker": "^"},  # purple, dotted
}


def _read_csv(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def _model_shortname(model_id: str) -> str:
    """Qwen/Qwen2.5-Coder-7B-Instruct → Qwen 7B"""
    last = model_id.split("/")[-1]
    # "Qwen2.5-Coder-7B-Instruct" → "Qwen 7B"
    for size in ("1.5B", "7B", "32B", "72B"):
        if size in last:
            return f"Qwen {size}"
    return last


def plot(rows: list[dict], metric: str, title: str, out_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.5))

    # Group by instantiation
    inst_data: dict[int, tuple[list[int], list[float]]] = {}
    for row in rows:
        inst = int(row["instantiation"])
        epoch = int(row["epoch"])
        val = row.get(metric)
        if val in (None, "", "None"):
            continue
        val = float(val)
        if inst not in inst_data:
            inst_data[inst] = ([], [])
        inst_data[inst][0].append(epoch)
        inst_data[inst][1].append(val)

    for inst, (epochs, vals) in sorted(inst_data.items()):
        style = INST_STYLE.get(inst, {})
        ax.plot(
            epochs, [v * 100 for v in vals],
            label=INST_LABELS.get(inst, f"inst{inst}"),
            **style,
        )

    ax.set_xlabel("Training epoch", fontsize=11)
    ylabel = "Baseline pass rate (%)" if metric == "baseline_pass" else "Exec rate (%)"
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=12)
    ax.legend(fontsize=10)
    ax.set_ylim(0, 105)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    print(f"Saved: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, nargs="+", required=True,
                        help="CSV file(s) from eval_checkpoints.py")
    parser.add_argument("--metric", choices=["baseline_pass", "exec_rate"],
                        default="baseline_pass")
    parser.add_argument("--draw", default="greedy",
                        help="Which 'draw' column value to plot as the curve (default: greedy, "
                             "the primary measurement present at every epoch). CSVs written after "
                             "2026-07-12 also carry sampling_seed{42,43,44} rows at epoch 30 only "
                             "-- left in, they'd stack multiple points at x=30. Pass '' to disable "
                             "filtering (e.g. for older single-draw CSVs with no 'draw' column).")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    all_rows = []
    model_names: list[str] = []
    for csv_path in args.csv:
        rows = _read_csv(csv_path)
        if args.draw and rows and "draw" in rows[0]:
            rows = [r for r in rows if r["draw"] == args.draw]
        all_rows.extend(rows)
        if rows:
            model_names.append(_model_shortname(rows[0].get("model", csv_path.stem)))

    if not all_rows:
        print("No data found in CSV(s).", file=sys.stderr)
        sys.exit(1)

    model_label = " & ".join(dict.fromkeys(model_names))  # deduplicated, ordered
    title = f"Contamination experiment — {model_label}\nPerformance vs training epoch (LoRA, inst1 train data)"

    out_path = args.out or ROOT / "analysis/figures/epoch_perf.pdf"
    plot(all_rows, args.metric, title, out_path)

    # analysis/figures/ is entirely gitignored (.gitignore:49) -- a sidecar
    # written there would never be committed, so (matching
    # plot_comparison_c_onset_curve.py / plot_rq5_correlation.py's
    # convention) it's written to analysis/ root instead, which is only
    # ignored for .csv/.xlsx. Added 2026-08-05: this script previously had
    # no provenance stamping at all (analysis/FIGURE_AUDIT.md). Only for
    # real output under analysis/figures/ -- guards against
    # tests/ad hoc runs with an arbitrary --out (e.g. a pytest tmp_path)
    # leaking a stray sidecar into the tracked repo, which happened once
    # (analysis/out_PROVENANCE.md, found and removed 2026-08-05).
    figures_dir = (ROOT / "analysis" / "figures").resolve()
    if figures_dir in out_path.resolve().parents:
        provenance = f"""# {out_path.stem} — provenance

{stamp_block("scripts/plot_epoch_perf.py")}
Sources: {[str(p) for p in args.csv]} (draw filter: {args.draw!r}).
Metric: {args.metric}.

Output: {out_path.relative_to(ROOT)}.
"""
        provenance_out = ROOT / "analysis" / (out_path.stem + "_PROVENANCE.md")
        provenance_out.write_text(provenance)
        print(f"Provenance: {provenance_out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
