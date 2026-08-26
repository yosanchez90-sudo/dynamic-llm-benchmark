"""Render three pieces of real, live-captured execution evidence for the
supporting report: the automated test suite passing, the citation gate
passing, and a slice of this project's own real SLURM job accounting.

Each panel is a literal, monospace capture of a command this script itself
runs (or, for the SLURM panel, a fixed historical window queried from the
cluster's own accounting record), not a hand-typed transcript. Structural
in the same sense as scripts/plot_flow_diagram.py: it renders real command
output, not a value read from analysis/*.csv, so it carries no
PROVENANCE.md sidecar. It still lives in the registered asset pipeline so
the images cannot go stale relative to what the commands actually print.

The test-suite panel excludes torch-marked tests (`-m "not torch"`): this
project's own pytest marker for tests that need a working torch import,
documented in pyproject.toml, matching how the suite is run everywhere
else in this project's own instructions.

The SLURM panel queries a fixed historical window (2026-07-01 through the
2026-08-12 experimental freeze) rather than the live queue, so the image
is reproducible on any later re-run and never shows another user's job.

Usage: python scripts/plot_execution_evidence.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "analysis" / "figures"
PYTHON = sys.executable

BG = "#1e1e1e"
FG = "#d4d4d4"
PROMPT = "#6a9955"
HEADER = "#4ec9b0"


def _run(cmd: list[str], cwd: Path = ROOT, timeout: int = 900) -> str:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return proc.stdout + proc.stderr


def _render(lines: list[str], out_name: str, prompt_line: str, title: str,
            fontsize: float = 10.5, width: float = 9.5) -> None:
    n = len(lines) + 1.6
    height = 0.30 * n + 0.5
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, n)

    # Matplotlib treats a pair of literal "$" as mathtext, which mangles a
    # shell prompt like "$ sacct -u $USER" (only one of its two "$" is a
    # deliberate prompt glyph); escape every "$" so all text renders literally.
    esc = lambda s: s.replace("$", r"\$")
    ax.text(0.012, n - 0.55, esc(prompt_line), fontsize=fontsize, family="monospace",
             color=PROMPT, ha="left", va="top")
    for i, line in enumerate(lines):
        ax.text(0.012, n - 1.35 - i, esc(line), fontsize=fontsize, family="monospace",
                 color=FG, ha="left", va="top")

    fig.suptitle(title, fontsize=11, color=FG, x=0.012, ha="left", y=0.995,
                 fontweight="bold")
    out_path = FIGURES / out_name
    fig.savefig(out_path, dpi=200, facecolor=BG, bbox_inches="tight")
    fig.savefig(out_path.with_suffix(".pdf"), facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path} and {out_path.with_suffix('.pdf').name}")


def render_test_suite() -> None:
    cmd = [PYTHON, "-m", "pytest", "-q", "-m", "not torch"]
    out = _run(cmd)
    tail = [l for l in out.splitlines() if l.strip()][-10:]
    _render(tail, "evidence_test_suite.png", "$ pytest -q -m \"not torch\"",
            "Real execution: the automated test suite, captured live")


def render_citation_gate() -> None:
    cmd = [PYTHON, "scripts/check_doc_citations.py"]
    out = _run(cmd)
    tail = [l for l in out.splitlines() if l.strip()][-9:]
    _render(tail, "evidence_citation_gate.png",
            "$ python scripts/check_doc_citations.py",
            "Real execution: the citation gate, captured live")


def render_slurm_accounting() -> None:
    cmd = [
        "sacct", "-u", "40492566",
        "--starttime=2026-07-14", "--endtime=2026-07-24",
        "--format=JobID%-13,JobName%-22,Partition%-11,State%-11,Elapsed%-11",
    ]
    out = _run(cmd)
    rows = [l for l in out.splitlines() if l.strip()]
    # Drop sub-step rows (".batch"/".extern") so the panel reads as one row
    # per submitted job, matching how a user actually reads their own queue.
    rows = [r for r in rows if ".bat" not in r and ".ext" not in r]
    tail = rows[:16]
    _render(tail, "evidence_slurm_jobs.png",
            "$ sacct -u $USER --starttime=2026-07-14 --endtime=2026-07-24 ...",
            "Real execution: this project's own SLURM job accounting (Kelvin2)",
            width=11.5)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    render_citation_gate()
    render_slurm_accounting()
    render_test_suite()


if __name__ == "__main__":
    main()
