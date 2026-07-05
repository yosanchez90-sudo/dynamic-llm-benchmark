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
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    all_rows = []
    model_names: list[str] = []
    for csv_path in args.csv:
        rows = _read_csv(csv_path)
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


if __name__ == "__main__":
    main()
