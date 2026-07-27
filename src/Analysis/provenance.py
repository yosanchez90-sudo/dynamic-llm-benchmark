"""Shared provenance stamp for thesis-asset-generating scripts
(scripts/build_thesis_assets.py's registry) -- every registered step's
output should carry a generation timestamp + git commit hash, so a reader
can tell exactly which code produced a given table/figure. Previously
inconsistent: some scripts had it, several didn't (found 2026-07-28 while
auditing the registry).
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def stamp_block(script_path: str) -> str:
    """3-line 'Generated / Git commit / Script' block, the convention this
    project's *_PROVENANCE.md files already use (see e.g.
    analysis/COMPARISON_PROVENANCE.md) -- for embedding directly in a
    Markdown provenance doc.
    """
    return (
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n"
        f"Git commit: {git_commit()}\n"
        f"Script: {script_path}\n"
    )
