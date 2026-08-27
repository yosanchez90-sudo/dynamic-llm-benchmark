"""Generate paper/table1.tex: a compact hypothesis/prediction/verdict table,
read live from docs/Research_questions.xlsx's Hypotheses sheet.

Two things are NOT auto-derived from the sheet's own prose:

1. **Prediction** is a fixed, hand-written one-line paraphrase per
   hypothesis, not a truncation of the sheet's "Approved wording
   (condensed)" column (already 1-2 full sentences, too long to safely
   shorten by string-slicing without risking a misleading cut). The
   pre-registered wording itself doesn't change, so a fixed paraphrase
   carries no drift risk, see docs/Approved_Hypotheses.md for the
   source text each paraphrase compresses.
2. **Verdict** IS read live, as the leading tag of the sheet's own "Final
   verdict" cell (everything before the first " - " or ". ", whichever
   comes first). This is the part that can actually change as data
   lands, so it must track the sheet, not be hand-typed here.

A hypothesis ID present in PARAPHRASES but absent from the sheet (or vice
versa) raises loudly instead of silently producing a mismatched table,
same "fail loud on a coverage gap" discipline as the rest of this
project's validators.

The section-pointer column (FIGURE_TABLE_SPEC.md T-4) uses \\ref{} to each
hypothesis's own Section 4 subsection label, not a hardcoded number, so it
can never go stale if Section 4 is ever reordered.

Usage:
    python scripts/build_paper_table1.py

Writes: paper/table1.tex
"""
from __future__ import annotations

import re
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "docs" / "Research_questions.xlsx"
OUT_PATH = ROOT / "paper" / "table1.tex"

# (hypothesis ID in the sheet, RQ, abbreviated row label, section label to
# \ref{}, one-line prediction paraphrase). Abbreviated labels are defined in
# the table's own note (FIGURE_TABLE_SPEC.md T-3): trims "H1 Test 1/2" to
# "H1a/H1b", "H6 clause 1/2" to "H6a/H6b", "H2-supplementary" to "H2-supp.",
# freeing width for the Prediction column.
PARAPHRASES: list[tuple[str, str, str, str, str]] = [
    ("H1 Test 1", "RQ1", "H1a", "sec:results-h1test1", "DyMuT scores lower than static, CC-matched"),
    ("H1 Test 2", "RQ1", "H1b", "sec:results-h1test2", "Leaked twin (PLT) scores higher than decontaminated ULT"),
    ("H2", "RQ1", "H2", "sec:results-h2", "Static-benchmark gain from fine-tuning exceeds dynamic gain"),
    ("H2-supplementary", "RQ1", "H2-supp.", "sec:results-h2supp", "Leaked instantiation inflates itself, not fresh instantiations (post-hoc)"),
    ("H3", "RQ2", "H3", "sec:results-h3", "Mutation score never increases from L1 to L4"),
    ("H4", "RQ3", "H4", "sec:results-h4", "Static-dynamic gap larger at low tiers than high tiers"),
    ("H5", "RQ4", "H5", "sec:results-h5", "Cross-instantiation Kendall $\\tau$ exceeds \\HFiveTauThreshold{}"),
    ("H6 clause 1", "RQ5", "H6a", "sec:results-h6", "DyMuT-proxy correlation positive but imperfect"),
    ("H6 clause 2", "RQ5", "H6b", "sec:results-h6", "DyMuT-proxy correlation weaker than static-proxy"),
]

# RQ legend + abbreviation key, as a wrapped table note (FIGURE_TABLE_SPEC.md
# T-2): one RQ per line so a five-item legend is scannable, not one wrapped
# paragraph. Kept inside the table (not only in the Introduction's prose,
# see PA-7) so the table reads standalone.
TABLE_NOTE_LINES = [
    "RQ1: contamination resistance versus a static benchmark.",
    "RQ2: effect of complexity tier.",
    "RQ3: whether overestimation is larger at low tiers.",
    "RQ4: stability of rankings across re-instantiations.",
    "RQ5: agreement with an external code-generation proxy.",
    "H1a/H1b: H1 Test 1/Test 2. H2-supp.: H2-supplementary (post-hoc). H6a/H6b: H6 clause 1/clause 2.",
]

_VERDICT_SPLIT_RE = re.compile(r"\s+-\s+|\.\s+")


def _verdict_tag(full_verdict: str) -> str:
    m = _VERDICT_SPLIT_RE.search(full_verdict)
    tag = full_verdict[: m.start()] if m else full_verdict
    return tag.strip()


def _escape(s: str) -> str:
    return s.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")


def main() -> None:
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb["Hypotheses"]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    id_col = header.index("ID")
    verdict_col = header.index("Final verdict")

    verdicts: dict[str, str] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        hyp_id = row[id_col]
        if hyp_id is None or "draft" in str(hyp_id).lower() or "NOT PURSUED" in str(hyp_id):
            continue
        verdicts[str(hyp_id).strip()] = _verdict_tag(str(row[verdict_col]))

    paraphrase_ids = {hid for hid, *_ in PARAPHRASES}
    sheet_ids = set(verdicts)
    if paraphrase_ids != sheet_ids:
        missing_in_sheet = paraphrase_ids - sheet_ids
        missing_in_script = sheet_ids - paraphrase_ids
        raise SystemExit(
            f"Table 1 coverage mismatch -- fix PARAPHRASES before regenerating.\n"
            f"  In script, not in sheet: {missing_in_sheet or 'none'}\n"
            f"  In sheet, not in script: {missing_in_script or 'none'}"
        )

    rows_tex = []
    for hyp_id, rq, short_label, sec_label, prediction in PARAPHRASES:
        verdict = _escape(verdicts[hyp_id])
        rows_tex.append(
            f"{_escape(rq)} & {short_label} & \\ref{{{sec_label}}} & {prediction} & {verdict} \\\\"
        )

    body = "\n".join(rows_tex)
    # Each RQ/abbreviation-key line on its own row inside the note cell
    # (FIGURE_TABLE_SPEC.md T-2: "a five-item legend as one wrapped
    # paragraph is harder to scan than five short lines"), not joined into
    # one run-on paragraph.
    # \newline, not a bare \\: a \\ inside a p{}/X paragraph cell that also
    # sits inside a tabularx environment conflicts with tabularx's own
    # column-width measuring pass (confirmed: "Missing \endgroup inserted"
    # at \end{tabularx} when this used \\). \newline forces the same
    # visible line break without being misread as a row separator.
    note = " \\newline\n".join(TABLE_NOTE_LINES)
    # table* (not table): a 5-column RQ/Hyp./Sec./Prediction/Verdict table no
    # longer fits a single IEEEtran column (confirmed 2026-08-27 -- adding
    # the RQ column overflowed the column width by ~35pt and visibly
    # collided with the adjacent column's text). table* spans the full
    # page width and is placed at a page's top/bottom, not inline in one
    # column, which is the standard IEEEtran fix for a table too wide for
    # one column. tabularx's X column (Prediction) absorbs whatever width
    # the other four natural-width columns leave unused, so the table
    # actually reaches \\textwidth instead of leaving blank space to the
    # right of Verdict, and long predictions wrap instead of overflowing.
    tex = f"""% Auto-generated by scripts/build_paper_table1.py -- DO NOT EDIT DIRECTLY.
% Compact hypothesis/prediction/verdict table. Predictions are fixed
% paraphrases (see script docstring); verdicts are read live from
% docs/Research_questions.xlsx's Hypotheses sheet; the section pointer is a
% live \\ref{{}}, not a hardcoded number. table* (full page width, not
% table): see script docstring for why this must not be a single-column
% table. tabularx's X column lets Prediction absorb the table's full
% width instead of leaving it unused on the right.
\\begin{{table*}}[t]
\\caption{{Pre-registered hypotheses, predictions, and verdicts}}
\\label{{tab:hypotheses}}
\\centering
\\small
\\setlength{{\\tabcolsep}}{{4pt}}
\\renewcommand{{\\arraystretch}}{{1.15}}
\\begin{{tabularx}}{{\\textwidth}}{{@{{}}llc X l@{{}}}}
\\toprule
\\textbf{{RQ}} & \\textbf{{Hyp.}} & \\textbf{{\\S}} & \\textbf{{Prediction}} & \\textbf{{Verdict}} \\\\
\\midrule
{body}
\\bottomrule
\\multicolumn{{5}}{{@{{}}p{{\\textwidth}}@{{}}}}{{\\small {note}}} \\\\
\\end{{tabularx}}
\\end{{table*}}
"""
    OUT_PATH.write_text(tex)
    print(f"Wrote {OUT_PATH.relative_to(ROOT)} ({len(PARAPHRASES)} rows)")


if __name__ == "__main__":
    main()
