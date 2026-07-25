"""Load dynamic-benchmark result JSONL files into a flat pandas DataFrame
for cross-run analysis (stability, comparisons).

`model_label` is the first-class identity field on TestGenRecord (added
2026-07-09, see src/eval/test_gen_problem.py:compute_model_label) that
distinguishes a base model from a LoRA-adapted variant of the same
model/model_revision (adapters don't change the base checkpoint's SHA, so
those two fields alone can't tell them apart). Records written before that
change don't have it — for those we fall back to deriving it from the
filename, which follows the same convention:
    <model_label>__<benchmark>__<prompting_condition>__inst<N>__<...>.jsonl
(see scripts/migrate_add_model_label.py, which backfills the field in place
for exactly this reason — the fallback here is defense in depth for any
record that predates both the field and the migration).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_RECORD_COLUMNS = [
    "model", "model_revision", "instantiation_id", "template_id",
    "instance_seed", "tier", "K", "prompting_condition", "benchmark",
    "exec_rate", "statement_coverage", "branch_coverage", "mutation_score",
    "mutants_total", "mutants_killed", "mutants_dropped_for_import_failure",
    "baseline_passed", "notes", "model_label", "adapter_path", "adapter_hash",
    "timestamp",
]

_BENCHMARKS = ("dynamic", "ult", "plt")

# Natural key for one (model variant, problem) evaluation. Superseded reruns
# (a stale partial-tier retry file left behind after a later complete rerun —
# seen for claude-sonnet-4-6/claude-haiku-4-5 dynamic inst1-4, ~560 keys,
# 2026-07-25 audit) share this key across two source files; load_records
# keeps only the newest by timestamp so aggregates (StableMut@K, Kendall tau)
# don't silently double-count a problem with two different scored outcomes.
_DEDUP_KEY = [
    "model_label", "benchmark", "instantiation_id", "template_id",
    "instance_seed", "tier", "K", "prompting_condition",
]


def _model_label_from_filename(path: Path) -> str:
    """Fallback for records written before model_label existed — derive it
    from the filename, keeping any fine-tune/adapter suffix that precedes
    the benchmark name (see module docstring).
    """
    stem = path.stem
    for benchmark in _BENCHMARKS:
        marker = f"__{benchmark}__"
        if marker in stem:
            return stem.split(marker)[0]
    return stem


def load_records(results_dir: str | Path, benchmark: str | None = "dynamic") -> pd.DataFrame:
    """Load every *.jsonl file in `results_dir` into one flat DataFrame.

    One row per (model variant, problem) evaluation, deduplicated on
    `_DEDUP_KEY` (keeping the newest by `timestamp`) — a superseded rerun
    left in the same directory as its complete replacement must not be
    double-counted in an aggregate mean. Pass benchmark=None to load all
    benchmarks (dynamic/ult/plt) together instead of filtering.
    """
    results_dir = Path(results_dir)
    rows: list[dict] = []
    for path in sorted(results_dir.glob("*.jsonl")):
        fallback_label = _model_label_from_filename(path)
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if benchmark is not None and record.get("benchmark") != benchmark:
                continue
            row = {col: record.get(col) for col in _RECORD_COLUMNS}
            row["model_label"] = record.get("model_label") or fallback_label
            row["source_file"] = path.name
            rows.append(row)

    df = pd.DataFrame(rows, columns=[*_RECORD_COLUMNS, "source_file"])
    if df.empty:
        return df

    df["_ts_sort"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.sort_values("_ts_sort", na_position="first", kind="stable")
    df = df.drop_duplicates(subset=_DEDUP_KEY, keep="last")
    df = df.sort_values("_ts_sort", na_position="first", kind="stable").drop(columns="_ts_sort")
    return df.reset_index(drop=True)
