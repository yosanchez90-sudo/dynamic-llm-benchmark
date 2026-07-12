"""Assemble pre/post fine-tune tidy frames for the DiD estimator (did.py)
from this project's actual result files. Kept separate from did.py so the
estimator itself stays source-agnostic and unit-testable without real data.

SOURCE (updated 2026-07-12): data/results/finetune_rebuild/epoch_perf_*.csv,
written by the patched scripts/eval_checkpoints.py, is now the default and
recommended source for BOTH pre and post — see analysis/README.md for why
the old analysis/epoch_perf_*.csv files are quarantined (they were measured
under a generation config, no_repeat_ngram_size=4, that fabricated a
collapse in 3 of 6 fine-tuning conditions).

This also resolves a measurement-instrument gap that existed before:
eval_checkpoints.py now supports --baseline (epoch=0, no adapter), measured
through the exact same exec/baseline check as every other epoch. Loading
BOTH pre and post from the same CSV (see load_pre_post_same_instrument)
means the two sides are no longer measured by two different tools — the old
cross-source loader (pre from data/results/dynamic/'s test_gen_scorer.py
`pytest --collect-only`; post from eval_checkpoints.py's bare
`python -c "import test_generated"`) is kept below for callers that need
mutation_score (only data/results/dynamic/ has it), but is no longer the
default.

Every result row in the new CSVs also carries a `draw` column (e.g.
"greedy", "sampling_seed42") since eval_checkpoints.py can now record
multiple draws per (epoch, instantiation) — callers MUST filter to one draw
before aggregating, or rows from different draws get summed together.
load_post_finetune_dynamic defaults to draw="greedy", the primary policy
the checkpoint-selection rule gates on.

ULT/PLT: no model has been evaluated against them yet (pre OR post) — there
is nothing to load. did.compute_did() already handles a benchmark missing
from either side gracefully (skips it, doesn't zero-fill); add loaders here
once src/data/ult_plt.py-based evaluation runs exist.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from src.Analysis.loader import load_records
from src.eval.test_gen_problem import compute_model_label

RECOMMENDED_METRIC = "baseline_pass"   # see module docstring
CAVEAT_METRIC = "exec_rate"            # usable; see docstring for the now-resolved instrument gap
TRAIN_INSTANTIATION = 1                # every current fine-tune config trains on inst1
DEFAULT_DRAW = "greedy"                # the primary measurement policy
DEFAULT_RESULTS_ROOT = Path("data/results/finetune_rebuild")  # see module docstring

# Base (non-adapted) model's label is just compute_model_label() with no
# adapter — kept as its own name here for read­ability at call sites that
# are specifically about identifying a *base* model's result file.
hf_id_to_model_label = compute_model_label


def load_pre_finetune_dynamic(
    model_label: str, results_dir: str | Path = "data/results/dynamic",
) -> pd.DataFrame:
    """Base (non-fine-tuned) model's Dynamic-benchmark problem-level scores
    — the "pre" side for benchmark="dynamic". Real per-problem exec_rate,
    baseline_pass, and mutation_score (mutation_score usable here even
    though the post side won't have it — just don't request that metric
    from compute_did() until a post-finetune mutation-scored source exists).
    """
    df = load_records(results_dir, benchmark="dynamic")
    df = df[df["model_label"] == model_label].copy()
    df["baseline_pass"] = df["baseline_passed"].astype(float)
    return df


def _expand_epoch_perf_rows(rows: list[dict]) -> pd.DataFrame:
    """(n, rate) per selected row -> problem-level 0/1 columns. Lossless for
    the mean/variance of a boolean rate — the multiset of 0/1 values is
    exactly recoverable from (n, rate), only *which specific problem* each 1
    belongs to isn't — so this is a re-expansion of what's already reported,
    not fabricated data. exec_rate and baseline_pass are reconstructed
    independently (the CSV never records their joint per-problem pairing):
    do not treat same-index rows across the two columns as the same
    problem's paired outcome.
    """
    exec_vals: list[int] = []
    bp_vals: list[int] = []
    for r in rows:
        n = int(r["n"])
        exec_ones = round(float(r["exec_rate"]) * n)
        bp_ones = round(float(r["baseline_pass"]) * n)
        exec_vals.extend([1] * exec_ones + [0] * (n - exec_ones))
        bp_vals.extend([1] * bp_ones + [0] * (n - bp_ones))
    n_total = len(exec_vals)
    return pd.DataFrame({
        "benchmark": ["dynamic"] * n_total,
        "exec_rate": exec_vals,
        "baseline_pass": bp_vals,
    })


def load_post_finetune_dynamic(
    epoch_perf_csv: str | Path,
    epoch: int | None = None,
    instantiations: tuple[int, ...] = (2, 3),
    draw: str = DEFAULT_DRAW,
) -> pd.DataFrame:
    """Fine-tuned checkpoint's Dynamic-benchmark scores, re-expanded to
    problem-level rows from eval_checkpoints.py's aggregate CSV.

    epoch: which checkpoint epoch counts as "post" (default: the last epoch
        present in the file — the most fine-tuned checkpoint).
    instantiations: which Dynamic instantiations to include (default 2,3 —
        the HELD-OUT instantiations). Every current fine-tune config trains
        on instantiation 1, so including it here would make the control's
        own pre->post "improvement" partly circular (the model was directly
        optimised against that exact instantiation's outputs).
    draw: which measurement draw to use (default "greedy" — the primary
        policy). The CSV can hold multiple draws (greedy + several sampling
        seeds) per (epoch, instantiation); NOT filtering by draw would sum
        rows from different draws together.
    """
    rows = list(csv.DictReader(Path(epoch_perf_csv).read_text().splitlines()))
    if not rows:
        return pd.DataFrame(columns=["benchmark", "exec_rate", "baseline_pass"])

    if epoch is None:
        epoch = max(int(r["epoch"]) for r in rows)

    selected = [r for r in rows
                if int(r["epoch"]) == epoch and int(r["instantiation"]) in instantiations
                and r.get("draw", DEFAULT_DRAW) == draw]
    return _expand_epoch_perf_rows(selected)


def load_pre_post_same_instrument(
    epoch_perf_csv: str | Path,
    post_epoch: int | None = None,
    instantiations: tuple[int, ...] = (2, 3),
    draw: str = DEFAULT_DRAW,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Preferred loader (2026-07-12): pre AND post from the SAME CSV, same
    exec/baseline instrument (eval_checkpoints.py's _score_fast for both —
    pre is epoch=0, i.e. --baseline, no adapter). Eliminates the old
    cross-source instrument mismatch (see module docstring). Only usable if
    the CSV actually has epoch=0 rows (run eval_checkpoints.py --baseline).
    """
    rows = list(csv.DictReader(Path(epoch_perf_csv).read_text().splitlines()))
    if not any(int(r["epoch"]) == 0 for r in rows):
        raise ValueError(
            f"{epoch_perf_csv} has no epoch=0 (--baseline) rows — re-run "
            f"eval_checkpoints.py with --baseline, or use load_pre_finetune_dynamic "
            f"+ load_post_finetune_dynamic (cross-source, has the instrument caveat)."
        )
    pre_rows = [r for r in rows
                if int(r["epoch"]) == 0 and int(r["instantiation"]) in instantiations
                and r.get("draw", DEFAULT_DRAW) == draw]
    pre = _expand_epoch_perf_rows(pre_rows)
    post = load_post_finetune_dynamic(epoch_perf_csv, epoch=post_epoch,
                                       instantiations=instantiations, draw=draw)
    return pre, post


def load_pre_post_for_config(
    hf_model_id: str,
    epoch_perf_csv: str | Path,
    epoch: int | None = None,
    instantiations: tuple[int, ...] = (2, 3),
    results_dir: str | Path = "data/results/dynamic",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cross-source convenience wrapper: pre = base model's Dynamic results
    from data/results/dynamic/ (has mutation_score; different instrument —
    see module docstring), post = one fine-tuned checkpoint's Dynamic
    results from an epoch_perf CSV. Prefer load_pre_post_same_instrument()
    unless you specifically need mutation_score on the pre side.
    """
    model_label = hf_id_to_model_label(hf_model_id)
    pre = load_pre_finetune_dynamic(model_label, results_dir=results_dir)
    post = load_post_finetune_dynamic(epoch_perf_csv, epoch=epoch, instantiations=instantiations)
    return pre, post
