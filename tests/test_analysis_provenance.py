"""Unit tests for src/Analysis/provenance.py."""
from __future__ import annotations

from src.Analysis.provenance import git_commit, stamp_block


def test_git_commit_returns_short_hash_or_unknown():
    result = git_commit()
    assert result == "unknown" or (len(result) >= 7 and all(
        c in "0123456789abcdef" for c in result
    ))


def test_stamp_block_has_three_labelled_lines():
    block = stamp_block("scripts/example.py")
    lines = block.strip().splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("Generated: ")
    assert lines[1].startswith("Git commit: ")
    assert lines[2] == "Script: scripts/example.py"
