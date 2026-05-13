"""Append-only JSONL logging."""
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