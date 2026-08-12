"""Citation checker: scan hand-written analysis/*.md docs for numeric
claims (Kendall tau, Spearman rho, Pearson r, p-values, percentage-point
figures, n_models, n_defined) and check whether each value currently
appears anywhere in this project's live, auto-regenerated provenance
sources (the *_PROVENANCE.md / STABILITY.md / RANKING_MATRIX.md /
RQ5_DIAGNOSTICS.md family, plus their underlying CSVs).

WHAT THIS CATCHES: a hand-written doc citing a number that no longer
appears anywhere in the current pipeline output -- exactly the failure
mode found and fixed earlier in this pass (RQ5_INTERPRETATION.md citing
tau=0.333 for the pooled Dynamic<->ULT primary after a data landing moved
the live value to 0.278; STABILITY_INTERPRETATION.md citing a stale mean
pairwise tau).

WHAT THIS DOES NOT DO -- read before trusting a MISMATCH as a bug:
- It matches on VALUE within a small tolerance per statistic type, not on
  full semantic context (which exact pair/scope/metric a number claims to
  be). A MATCH means "this number is live somewhere in the reference
  corpus for this statistic type," not "this is definitely the correct
  citation for this exact sentence."
- MISMATCH lists the closest live value(s) of the same statistic type as
  a lead, not a guaranteed replacement.

SUPPRESSING LEGITIMATE FINDINGS -- two mechanisms, use whichever fits:
1. Inline marker, same line as the claim: `<!-- cite:historical -->` or
   `<!-- cite:external -->`. Suppresses every claim found on that line.
   For a multi-line span (e.g. a frozen historical table), bracket it with
   `<!-- cite:historical:start -->` ... `<!-- cite:historical:end -->` (or
   `:external:`) on their own lines.
2. `analysis/CITATION_ALLOWLIST.md`, a markdown table keyed on
   file+line+kind+value (line matched with a small tolerance so minor
   nearby edits don't silently break the entry) with a required one-line
   reason. Use this when an inline marker would be awkward to place, or
   for values the checker can't verify due to a known extraction gap
   (documented per-entry) rather than genuine document staleness.
Both produce a SUPPRESSED verdict, counted separately from MATCH so a
suppressed-but-wrong value doesn't silently look verified.

Usage:
    python scripts/check_doc_citations.py                 # full report
    python scripts/check_doc_citations.py --only rq5_interpretation
    python scripts/check_doc_citations.py --list           # list doc keys
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "analysis"

# Reference sources: auto-regenerated, safe to treat as "what the pipeline
# currently says" -- re-run scripts/build_thesis_assets.py before trusting
# this checker's output as current. Paths are ROOT-relative.
REFERENCE_FILES = [
    "analysis/COMPARISON_PROVENANCE.md",
    "analysis/comparison_rq1_holm.csv",
    "analysis/COMPARISON_C_PROVENANCE.md",
    "analysis/RQ5_PROVENANCE.md",
    "analysis/RQ5_DIAGNOSTICS.md",
    "analysis/RQ5_CROSS_FAMILY_PROVENANCE.md",
    "analysis/RQ5_SANITIZER_SENSITIVITY.md",
    "analysis/STABILITY.md",
    "analysis/H3_TIER_GRADIENT_PROVENANCE.md",
    "analysis/RANKING_MATRIX.md",
    "analysis/comparison_a_paired.csv",
    "analysis/comparison_a_coverage.csv",
    "analysis/comparison_a_coverage_adjusted.csv",
    "analysis/comparison_b_coverage.csv",
    "analysis/comparison_b_coverage_adjusted.csv",
    "analysis/comparison_c_did.csv",
    "analysis/comparison_c_gradient.csv",
    "analysis/comparison_c_mutk.csv",
    "analysis/rq5_model_ranking.csv",
    "analysis/rq5_cross_family_model_ranking.csv",
    "analysis/rq5_correlations.csv",
    "analysis/rq5_cross_family_correlations.csv",
    "analysis/rq5_sanitizer_sensitivity.csv",
    "analysis/stability_kendall.csv",
    "analysis/stability_stablemut.csv",
    "analysis/h3_tier_gradient_all_tier.csv",
    "analysis/h3_tier_gradient_l2l4.csv",
    # paper/values.tex is itself generated straight from the analysis/*.csv
    # files above (scripts/build_paper_values.py) -- included as a reference
    # source too so its own macros count as "live" for any OTHER paper/
    # source that might cite the same figure a second time in different form.
    "paper/values.tex",
]

# Hand-written docs to check -- key -> ROOT-relative path, so --only can
# target one.
DOC_FILES = {
    "comparison_a_interpretation": "analysis/COMPARISON_A_INTERPRETATION.md",
    "comparison_c_interpretation": "analysis/COMPARISON_C_INTERPRETATION.md",
    "rq5_interpretation": "analysis/RQ5_INTERPRETATION.md",
    "stability_interpretation": "analysis/STABILITY_INTERPRETATION.md",
    "h3_interpretation": "analysis/H3_INTERPRETATION.md",
    "hypothesis_deviations": "analysis/HYPOTHESIS_DEVIATIONS.md",
    "hypothesis_coverage_audit": "analysis/HYPOTHESIS_COVERAGE_AUDIT.md",
    "open_items": "analysis/OPEN_ITEMS.md",
    "metrics_and_findings_explained": "analysis/METRICS_AND_FINDINGS_EXPLAINED.md",
    "workbook_verification": "analysis/WORKBOOK_VERIFICATION.md",
    "paper_values": "paper/values.tex",
}
# paper/sections/*.tex are added dynamically in main() (the file set changes
# as the paper is drafted) rather than hardcoded here -- see _paper_section_docs().

# (type, tolerance, regex) -- regex must have exactly one capturing group,
# the numeric value (sign included where relevant).
PATTERNS: list[tuple[str, float, re.Pattern]] = [
    ("kendall_tau", 0.0006, re.compile(
        r"(?:kendall(?:'?s)?\s*(?:τ|tau)|(?<![A-Za-z])τ|kendall_tau)\s*[:=]?\s*\**\s*(-?\d\.\d{2,6})")),
    ("spearman_rho", 0.0006, re.compile(
        r"(?:spearman\s*(?:ρ|rho)|(?<![A-Za-z])ρ|spearman_rho)\s*[:=]?\s*\**\s*(-?\d\.\d{2,6})")),
    ("pearson_r", 0.0006, re.compile(
        r"pearson\s*r\s*[:=]?\s*\**\s*(-?\d\.\d{2,6})")),
    ("effect_r", 0.0006, re.compile(
        r"effect_r\s*[:=]?\s*\**\s*(-?\d\.\d{2,6})")),
    ("p_value", 0.0003, re.compile(
        r"\bp\s*[=<]\s*\**\s*(\d\.\d{2,6})")),
    ("pp", 0.06, re.compile(
        r"([+-]?\d+\.\d)\s*pp\b")),
    ("n_models", 0.5, re.compile(
        r"n_models\s*[:=]\s*(\d+)")),
    ("n_defined", 0.5, re.compile(
        r"n_defined\s*[:=]\s*(\d+)")),
]


@dataclass
class Claim:
    kind: str
    value: float
    file: str
    line_no: int
    context: str


ALLOWLIST_PATH = ROOT / "analysis" / "CITATION_ALLOWLIST.md"
_INLINE_MARKER_RE = re.compile(r"<!--\s*cite:(historical|external)\s*-->")
_BLOCK_START_RE = re.compile(r"<!--\s*cite:(historical|external):start\s*-->")
_BLOCK_END_RE = re.compile(r"<!--\s*cite:(historical|external):end\s*-->")


def _marked_lines(text: str) -> set[int]:
    """1-indexed line numbers covered by an inline or block cite: marker."""
    marked: set[int] = set()
    in_block = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        if _INLINE_MARKER_RE.search(line):
            marked.add(line_no)
        if _BLOCK_START_RE.search(line):
            in_block = True
            marked.add(line_no)
            continue
        if _BLOCK_END_RE.search(line):
            in_block = False
            marked.add(line_no)
            continue
        if in_block:
            marked.add(line_no)
    return marked


@dataclass
class AllowlistEntry:
    file: str
    line: int
    kind: str
    value: float
    reason: str


def _load_allowlist() -> list[AllowlistEntry]:
    if not ALLOWLIST_PATH.exists():
        return []
    entries: list[AllowlistEntry] = []
    for line in ALLOWLIST_PATH.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0] in ("file", "---"):
            continue
        if re.match(r"^-+$", cells[1]):
            continue
        try:
            entries.append(AllowlistEntry(
                file=cells[0], line=int(cells[1]), kind=cells[2],
                value=float(cells[3]), reason=cells[4],
            ))
        except ValueError:
            continue  # malformed row -- skip rather than crash the checker
    return entries


_LINE_DRIFT_TOLERANCE = 3  # allowlist entries survive small nearby edits


def _allowlist_covers(entry_list: list[AllowlistEntry], claim: Claim, tol: float) -> AllowlistEntry | None:
    for entry in entry_list:
        if (entry.file == Path(claim.file).name
                and entry.kind == claim.kind
                and abs(entry.line - claim.line_no) <= _LINE_DRIFT_TOLERANCE
                and abs(entry.value - claim.value) <= tol):
            return entry
    return None


# Markdown/CSV table column name -> claim kind. Matched case-insensitively
# against the header cell with non-alnum chars stripped. Only exact-ish
# matches map -- deliberately no bare "n" or "r" (too ambiguous across
# n_models/n_pairs/n_rows/n_problems and pearson_r/effect_r).
COLUMN_KIND_MAP = {
    "kendalltau": "kendall_tau",
    "kendall_tau": "kendall_tau",
    "spearmanrho": "spearman_rho",
    "spearman_rho": "spearman_rho",
    "pearsonr": "pearson_r",
    "pearson_r": "pearson_r",
    "effect_r": "effect_r",
    "p": "p_value",
    "pvalue": "p_value",
    "p_value": "p_value",
    "p_perm": "p_value",
    "kendallp_perm": "p_value",
    "kendall_p_perm": "p_value",
    "spearmanp_perm": "p_value",
    "pearsonp_perm": "p_value",
    "p_perm_holm": "p_value",
    "kendall_p_perm_holm": "p_value",
    "p_value_holm": "p_value",
    "n_models": "n_models",
    "n_defined": "n_defined",
}
# Columns on a 0-1 fraction scale that hand-written docs cite as "+X.Xpp" --
# multiply by 100 and tag as "pp" in addition to any other tagging.
PP_SCALE_COLUMNS = {"gain", "did", "delta", "control_delta",
                     "gain_ci_lo", "gain_ci_hi", "did_ci_lo", "did_ci_hi"}


def _norm_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", h.strip().lower())


# Normalize map keys too, so "effect_r" in the map matches a header cell
# normalized to "effectr" the same way "kendall_p_perm" matches "kendallpperm".
COLUMN_KIND_MAP = {_norm_header(k): v for k, v in COLUMN_KIND_MAP.items()}
PP_SCALE_COLUMNS = {_norm_header(c) for c in PP_SCALE_COLUMNS}


def _extract_prose(path: Path, text: str) -> list[Claim]:
    claims: list[Claim] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for kind, _tol, pattern in PATTERNS:
            for m in pattern.finditer(line):
                try:
                    value = float(m.group(1))
                except ValueError:
                    continue
                start = max(0, m.start() - 30)
                end = min(len(line), m.end() + 10)
                claims.append(Claim(kind, value, str(path.relative_to(ROOT)),
                                     line_no, line[start:end].strip()))
    return claims


def _extract_tables(path: Path, text: str) -> list[Claim]:
    """Parse pipe-delimited markdown tables (or comma-delimited CSVs),
    tagging each numeric cell by its column header via COLUMN_KIND_MAP."""
    claims: list[Claim] = []
    lines = text.splitlines()
    is_csv = path.suffix == ".csv"

    if is_csv:
        if not lines:
            return claims
        headers = [h.strip() for h in lines[0].split(",")]
        norm_headers = [_norm_header(h) for h in headers]
        for line_no, line in enumerate(lines[1:], start=2):
            cells = line.split(",")
            for col_idx, cell in enumerate(cells):
                if col_idx >= len(norm_headers):
                    break
                _tag_cell(claims, norm_headers[col_idx], headers[col_idx],
                          cell.strip(), path, line_no)
        return claims

    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        nxt = lines[i + 1]
        if "|" in line and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", nxt):
            headers = [c.strip() for c in line.strip().strip("|").split("|")]
            norm_headers = [_norm_header(h) for h in headers]
            j = i + 2
            while j < len(lines) and "|" in lines[j]:
                cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                for col_idx, cell in enumerate(cells):
                    if col_idx >= len(norm_headers):
                        break
                    _tag_cell(claims, norm_headers[col_idx], headers[col_idx],
                              cell, path, j + 1)
                j += 1
            i = j
        else:
            i += 1
    return claims


def _column_kind(norm_header: str) -> str | None:
    if norm_header in COLUMN_KIND_MAP:
        return COLUMN_KIND_MAP[norm_header]
    # compound headers, e.g. "dynamic_n_defined" / "ult_n_defined" /
    # "kendall_tau_ci_lo" -- suffix/substring match against known keys,
    # longest key first so "n_defined" wins over a shorter accidental hit.
    for key in sorted(COLUMN_KIND_MAP, key=len, reverse=True):
        if norm_header.endswith(key):
            return COLUMN_KIND_MAP[key]
    return None


def _is_pp_scale(norm_header: str) -> bool:
    return norm_header in PP_SCALE_COLUMNS or any(
        norm_header.endswith(c) for c in PP_SCALE_COLUMNS)


_INT_KINDS = {"n_models", "n_defined"}


def _tag_cell(claims: list[Claim], norm_header: str, raw_header: str,
              cell: str, path: Path, line_no: int) -> None:
    cell = cell.strip().strip("*")
    kind = _column_kind(norm_header)
    # n_models/n_defined columns are often plain integers (no decimal
    # point) in the source CSVs/tables -- match those too, but only for
    # count-type kinds, so a bare row index elsewhere isn't misread as a
    # correlation/p-value.
    if kind in _INT_KINDS and re.match(r"^-?\d+$", cell):
        claims.append(Claim(kind, float(cell), str(path.relative_to(ROOT)),
                             line_no, f"{raw_header}={cell}"))
        return
    m = re.match(r"^-?\d+\.\d+$", cell)
    if not m:
        return
    value = float(cell)
    context = f"{raw_header}={cell}"
    if kind:
        claims.append(Claim(kind, value, str(path.relative_to(ROOT)), line_no, context))
    if _is_pp_scale(norm_header):
        claims.append(Claim("pp", round(value * 100, 4),
                             str(path.relative_to(ROOT)), line_no, context))


def _extract_pandas_tables(path: Path, text: str) -> list[Claim]:
    """Parse space-aligned `print(df)`-style tables (no pipes), the format
    several provenance docs embed directly (e.g. COMPARISON_PROVENANCE.md's
    survivorship audit, COMPARISON_C_PROVENANCE.md's DiD tables). pandas
    right-justifies each column to a fixed width (= widest of header/any
    data value), so a header token's END position in the header line is a
    stable column boundary for every row below it -- sliced by character
    position, not by splitting on whitespace runs (adjacent columns can be
    separated by as little as one space when both are near their column's
    max width, which breaks naive whitespace-split parsing)."""
    claims: list[Claim] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        header_spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", lines[i])]
        header_tokens = [lines[i][s:e] for s, e in header_spans]
        if len(header_tokens) >= 3 and not any(
            re.match(r"^-?\d+\.?\d*$", t) for t in header_tokens
        ):
            j = i + 1
            data_rows = []
            while j < len(lines) and lines[j].strip():
                bounds = [0] + [e for _, e in header_spans[:-1]] + [len(lines[j])]
                cells = [lines[j][bounds[k]:bounds[k + 1]].strip()
                         for k in range(len(header_tokens))]
                if len(cells) == len(header_tokens) and any(
                    re.match(r"^-?\d+\.\d+$", c) for c in cells
                ):
                    data_rows.append((j, cells))
                    j += 1
                else:
                    break
            if data_rows:
                norm_headers = [_norm_header(h) for h in header_tokens]
                for line_idx, cells in data_rows:
                    for col_idx, cell in enumerate(cells):
                        _tag_cell(claims, norm_headers[col_idx], header_tokens[col_idx],
                                  cell, path, line_idx + 1)
                i = j
                continue
        i += 1
    return claims


# LaTeX \newcommand macro name suffix -> claim kind, longest suffix first
# so e.g. "...NDefined" wins over the shorter "...N" it also ends with.
# Matches build_paper_values.py's own naming convention (\Num<Hyp><Quantity>,
# digits spelled out since LaTeX macro names can't contain them).
MACRO_SUFFIX_KIND = [
    ("NDefined", "n_defined"),
    ("EffectR", "effect_r"),
    ("Tau", "kendall_tau"),
    ("Rho", "spearman_rho"),
    ("Gain", "pp"),
    ("Did", "pp"),
    ("HolmP", "p_value"),
    ("P", "p_value"),
    ("N", "n_models"),
]

_LATEX_MACRO_RE = re.compile(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}")


def _extract_latex_macros(path: Path, text: str) -> list[Claim]:
    """Parse \\newcommand{\\Name}{value} definitions (paper/values.tex's own
    format), inferring each macro's statistic kind from its name suffix.
    Values that aren't a bare int/float (CI ranges, SD bands, etc.) are
    skipped -- not every macro maps to a single checkable number."""
    claims: list[Claim] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        m = _LATEX_MACRO_RE.search(line)
        if not m:
            continue
        macro_name, raw_value = m.group(1), m.group(2).strip()
        if not re.match(r"^-?\d+\.?\d*$", raw_value):
            continue  # CI/range/count-pair strings -- not a single value
        value = float(raw_value)
        kind = next((k for suf, k in MACRO_SUFFIX_KIND if macro_name.endswith(suf)), None)
        if kind is None:
            continue
        if kind == "pp":
            value = round(value, 4)  # already 0-100 scale, matches PP_SCALE_COLUMNS' own scaling
        claims.append(Claim(kind, value, str(path.relative_to(ROOT)), line_no,
                             f"\\{macro_name}={raw_value}"))
    return claims


def _extract(path: Path) -> list[Claim]:
    try:
        text = path.read_text()
    except FileNotFoundError:
        return []
    if path.suffix == ".tex":
        return _extract_latex_macros(path, text)
    return (_extract_prose(path, text) + _extract_tables(path, text)
            + _extract_pandas_tables(path, text))


# paper/sections/*.tex prose must cite every result value via a \NumXXX
# macro (defined once in paper/values.tex, read live from analysis/*.csv),
# never as a bare literal -- otherwise a re-run after new data lands
# silently leaves the old, now-wrong number sitting in the prose. Distinct
# check from the MATCH/MISMATCH value-verification above: this doesn't ask
# "does this number match the live source", it asks "does a literal number
# exist here at all, when it should be a macro reference instead".
_TEX_COMMAND_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})*")
_BARE_NUMBER_RE = re.compile(r"(?<![\w\\])(-?\d+\.\d+|-?\d+pp\b|-?\d+%)")


def find_hand_typed_numbers(path: Path) -> list[tuple[int, str]]:
    """Return [(line_no, matched_text)] for numeric literals in prose that
    are not part of a LaTeX command (\\NumXXX{}, \\cite{}, \\ref{}, a
    percent-escape \\%, etc.) and are not inside a comment."""
    try:
        text = path.read_text()
    except FileNotFoundError:
        return []
    findings: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        code_part = line.split("%", 1)[0] if not line.lstrip().startswith("%") else ""
        if not code_part.strip():
            continue
        # Blank out every LaTeX command (and its brace groups) first, so a
        # number inside \cite{chen2021codex} or \ref{fig:onset} or a macro
        # NAME (macro names are letters-only, but this also strips the
        # command's own argument braces where a real citation year/label
        # number might otherwise false-positive) never reaches the bare-
        # number regex.
        stripped = _TEX_COMMAND_RE.sub(" ", code_part)
        for m in _BARE_NUMBER_RE.finditer(stripped):
            findings.append((line_no, m.group(0)))
    return findings


def _tolerance(kind: str, value: float = 0.0) -> float:
    base = 0.001
    for k, tol, _ in PATTERNS:
        if k == kind:
            base = tol
            break
    if kind == "p_value":
        # p-values are often quoted at 1-2 significant figures while the
        # reference CSV/table stores full float precision -- widen
        # proportionally so 0.331 vs 0.3312 (same value, different
        # rounding) doesn't read as a mismatch, without so wide a net
        # that a genuinely different p-value (e.g. 0.05 vs 0.20) matches.
        return max(base, 0.15 * abs(value))
    return base


def build_reference_index() -> dict[str, list[Claim]]:
    index: dict[str, list[Claim]] = {}
    for fname in REFERENCE_FILES:
        for claim in _extract(ROOT / fname):
            index.setdefault(claim.kind, []).append(claim)
    return index


def check_doc(doc_key: str, reference_index: dict[str, list[Claim]],
              allowlist: list[AllowlistEntry] | None = None) -> list[tuple[Claim, str, list[Claim]]]:
    """Return [(claim, verdict, closest_matches)] for one doc."""
    fname = DOC_FILES[doc_key]
    path = ROOT / fname
    marked = _marked_lines(path.read_text()) if path.exists() else set()
    allowlist = allowlist if allowlist is not None else _load_allowlist()
    results = []
    for claim in _extract(path):
        candidates = reference_index.get(claim.kind, [])
        tol = _tolerance(claim.kind, claim.value)
        exact = [c for c in candidates if abs(c.value - claim.value) <= tol]
        if exact:
            results.append((claim, "MATCH", exact[:1]))
            continue
        if claim.line_no in marked:
            results.append((claim, "SUPPRESSED", []))
            continue
        allow_hit = _allowlist_covers(allowlist, claim, tol)
        if allow_hit is not None:
            results.append((claim, "SUPPRESSED", []))
            continue
        # widen search for "closest" candidates to report as a lead
        near = sorted(candidates, key=lambda c: abs(c.value - claim.value))
        near = [c for c in near if abs(c.value - claim.value) <= max(tol * 10, 0.01)][:3]
        if near:
            results.append((claim, "MISMATCH", near))
        else:
            results.append((claim, "UNVERIFIABLE", []))
    return results


def _discover_paper_sections() -> None:
    """Add every paper/sections/*.tex file to DOC_FILES under a
    paper_section_<name> key -- called before argparse so --list/--only see
    them. The file set changes as the paper is drafted; hardcoding it would
    go stale the moment a new section file is added."""
    sections_dir = ROOT / "paper" / "sections"
    if not sections_dir.exists():
        return
    for tex_path in sorted(sections_dir.glob("*.tex")):
        key = f"paper_section_{tex_path.stem}"
        DOC_FILES[key] = str(tex_path.relative_to(ROOT))


def main() -> None:
    _discover_paper_sections()
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", choices=list(DOC_FILES),
                         help="Check only these doc keys (see --list).")
    parser.add_argument("--list", action="store_true", help="List doc keys and exit.")
    args = parser.parse_args()

    if args.list:
        for key, fname in DOC_FILES.items():
            print(f"  {key:32s} {fname}")
        return

    reference_index = build_reference_index()
    total_refs = sum(len(v) for v in reference_index.values())
    print(f"Reference corpus: {total_refs} tagged values from "
          f"{len(REFERENCE_FILES)} auto-regenerated sources "
          f"({', '.join(f'{k}={len(v)}' for k, v in sorted(reference_index.items()))})")
    allowlist = _load_allowlist()
    print(f"Allowlist: {len(allowlist)} entries from "
          f"{ALLOWLIST_PATH.relative_to(ROOT)}\n")

    selected = args.only or list(DOC_FILES)
    totals = {"MATCH": 0, "MISMATCH": 0, "UNVERIFIABLE": 0, "SUPPRESSED": 0}

    for key in selected:
        results = check_doc(key, reference_index, allowlist)
        if not results:
            continue
        fname = DOC_FILES[key]
        counts = {v: 0 for v in totals}
        for _, verdict, _ in results:
            counts[verdict] += 1
            totals[verdict] += 1
        print(f"=== {fname} ({counts['MATCH']} match, {counts['MISMATCH']} mismatch, "
              f"{counts['UNVERIFIABLE']} unverifiable, {counts['SUPPRESSED']} suppressed) ===")
        for claim, verdict, candidates in results:
            if verdict in ("MATCH", "SUPPRESSED"):
                continue  # quiet on matches and suppressed; report only what needs a look
            cand_str = "; ".join(
                f"{c.value} ({c.file}:{c.line_no})" for c in candidates
            ) or "no candidate of this type found anywhere in the reference corpus"
            print(f"  [{verdict}] {fname}:{claim.line_no} "
                  f"{claim.kind}={claim.value}  context: \"...{claim.context}...\"")
            print(f"      closest live value(s): {cand_str}")
        print()

    # Hand-typed-number lint: paper/sections/*.tex only -- values.tex is
    # exempt (it's the macro-DEFINITION file, its right-hand sides are
    # supposed to be literals).
    hand_typed_total = 0
    for key in selected:
        fname = DOC_FILES[key]
        if not key.startswith("paper_section_"):
            continue
        findings = find_hand_typed_numbers(ROOT / fname)
        if findings:
            print(f"=== {fname} -- {len(findings)} hand-typed number(s), "
                  f"should be \\NumXXX macro references ===")
            for line_no, text in findings:
                print(f"  [HAND_TYPED] {fname}:{line_no}  \"{text}\"")
            print()
        hand_typed_total += len(findings)

    print("=" * 70)
    print(f"TOTAL: {totals['MATCH']} match, {totals['MISMATCH']} mismatch, "
          f"{totals['UNVERIFIABLE']} unverifiable, {totals['SUPPRESSED']} suppressed, "
          f"{hand_typed_total} hand-typed")
    totals["MISMATCH"] += hand_typed_total
    if totals["MISMATCH"] == 0:
        print("GATE: PASS -- zero unsuppressed mismatches. Any UNVERIFIABLE "
              "entries above are unconfirmed, not known-wrong; triage them "
              "into a fix, an inline cite: marker, or an allowlist entry.")
    else:
        print(f"GATE: FAIL -- {totals['MISMATCH']} unsuppressed mismatch(es). "
              "Each is either a real stale citation (fix it) or a legitimate "
              "case missing its cite: marker/allowlist entry (suppress it) -- "
              "see this script's module docstring for both mechanisms.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
