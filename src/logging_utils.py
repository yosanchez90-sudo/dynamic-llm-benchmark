"""Append-only JSONL result logging, used throughout the eval/scoring pipeline.

Inputs: a record (a dict, or a dataclass instance from src/eval/test_gen_problem.py
or similar) and the output path. Outputs: one JSON line appended to that path.

Position in the pipeline: the single write path every result row goes through,
from src/eval/test_gen_runner.py (per-problem results) and scripts/process_batch.py
(batch-API results). Append-only by design (never truncates or rewrites the file)
so a crashed or killed job keeps every row it already wrote, see CONVENTIONS.md's
data/results/ convention ("JSONL outputs, never overwritten").
"""
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def append_jsonl(record: Any, path: Path) -> None:
    """Append one record (dict or dataclass) to a JSONL file.

    Never overwrites, each call adds one line. Survives interrupted jobs:
    if a 1000-prompt eval crashes at prompt 500, we keep the first 499.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if is_dataclass(record):
        record = asdict(record)
    with open(path, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")