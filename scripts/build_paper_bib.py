"""Generate paper/references.bib from paper/references.yaml.

paper/references.yaml is the single source of truth for every citation's
metadata (see that file's own header for how each entry was resolved and
verified). This script is the only place a .bib entry is produced.
Never hand-edit paper/references.bib, regenerate it here after any
references.yaml change.

BibTeX entry type is chosen per-entry from the `venue` field (a crude
heuristic: "arXiv preprint" -> @misc, "Proceedings of"/"Findings of"/
"International Conference" -> @inproceedings, "Transactions"/"Journal" ->
@article, else @misc as a safe fallback). Correct manually in
references.yaml (not here) if a specific entry needs a different type.

Usage:
    python scripts/build_paper_bib.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml

YAML_PATH = ROOT / "paper" / "references.yaml"
BIB_PATH = ROOT / "paper" / "references.bib"


# references.yaml keeps every author on every entry. The full record is
# the point of that file. Rendering all of them in the printed bibliography
# is standard for most entries but genuinely costly for a handful of very-
# large-team papers (e.g. Codex/HumanEval's 58 authors); IEEE convention
# for these is "First Author et al.", triggered in (IEEEtran and most
# other) .bst styles by ending the BibTeX author field with "and others".
ET_AL_THRESHOLD = 10


def _bibtex_authors(authors: list[str]) -> str:
    if len(authors) > ET_AL_THRESHOLD:
        return f"{authors[0]} and others"
    return " and ".join(authors)


def _entry_type(venue: str) -> str:
    v = venue.lower()
    if "arxiv" in v or "preprint" in v:
        return "misc"
    if "transactions" in v or "journal" in v:
        return "article"
    if "proceedings" in v or "findings" in v or "conference" in v or "workshop" in v:
        return "inproceedings"
    return "misc"


def _escape(s: str) -> str:
    # Minimal BibTeX-safe escaping. These fields are plain prose/titles,
    # not LaTeX source, so only characters BibTeX itself treats specially
    # need protecting.
    return s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def _venue_field(entry_type: str, venue: str) -> tuple[str, str]:
    """Return (field_name, value) for the venue, matching the entry type."""
    if entry_type == "inproceedings":
        return "booktitle", venue
    if entry_type == "article":
        return "journal", venue
    return "howpublished", venue


def build_entry(e: dict) -> str:
    key = e["key"]
    entry_type = _entry_type(e["venue"])
    lines = [f"@{entry_type}{{{key},"]
    lines.append(f"  author = {{{_bibtex_authors(e['authors'])}}},")
    lines.append(f"  title = {{{{{_escape(e['title'])}}}}},")
    field_name, field_value = _venue_field(entry_type, e["venue"])
    lines.append(f"  {field_name} = {{{_escape(field_value)}}},")
    lines.append(f"  year = {{{e['year']}}},")
    if e.get("doi"):
        lines.append(f"  doi = {{{e['doi']}}},")
    if e.get("arxiv"):
        lines.append(f"  eprint = {{{e['arxiv']}}},")
        lines.append("  archivePrefix = {arXiv},")
    if e.get("url"):
        lines.append(f"  url = {{{e['url']}}},")
    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    data = yaml.safe_load(YAML_PATH.read_text())
    entries = data["entries"]

    unverified = [e["key"] for e in entries if e.get("status") not in (None, "COMPLETE")]

    blocks = [
        "% Auto-generated from paper/references.yaml -- DO NOT EDIT DIRECTLY.",
        f"% Regenerate: python scripts/{Path(__file__).name}",
        f"% {len(entries)} entries.",
    ]
    if unverified:
        blocks.append(
            "% NOT FULLY VERIFIED (status != COMPLETE in references.yaml, "
            f"see that file's source_used note): {', '.join(unverified)}"
        )
    blocks.append("")
    blocks.extend(build_entry(e) for e in entries)

    BIB_PATH.write_text("\n\n".join(blocks) + "\n")
    print(f"Wrote {BIB_PATH.relative_to(ROOT)} ({len(entries)} entries)")
    if unverified:
        print(f"  WARNING: {len(unverified)} entr{'y' if len(unverified)==1 else 'ies'} "
              f"not fully verified: {unverified}")


if __name__ == "__main__":
    main()
