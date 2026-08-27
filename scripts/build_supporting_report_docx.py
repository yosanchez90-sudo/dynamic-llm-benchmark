"""Build the ECS8056 supporting report as a formatted .docx from its
markdown source (paper/supporting_report/REPORT.md), the single source
of truth checked by scripts/check_doc_citations.py.

Produces: paper/supporting_report/SUPPORTING_REPORT.docx
- Title page, a real (field-based) table of contents, numbered heading
  styles, page numbers in the footer, the flow-diagram figure embedded
  with a numbered caption, and the error-ledger table formatted as a
  real Word table.

Usage: python scripts/build_supporting_report_docx.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Inches, RGBColor, Cm

ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "paper" / "supporting_report" / "REPORT.md"
OUT_PATH = ROOT / "paper" / "supporting_report" / "SUPPORTING_REPORT.docx"
FIGURES = ROOT / "analysis" / "figures"

NAVY = RGBColor(0x1F, 0x3A, 0x5F)

# Usable text width at this document's margins (21cm page, 2.5cm each
# side -- see build()'s section setup): 21 - 2.5 - 2.5 = 16cm.
USABLE_WIDTH_CM = 16.0


def _set_table_column_widths(table, rows: list[list[str]]) -> None:
    """Give every column an explicit, content-proportional width summing to
    the page's usable width, and switch the table to fixed layout.

    Without this, python-docx tables default to Word's "autofit to
    contents" layout: a column sizes itself to its widest *unwrapped*
    cell, so a table with a long-prose column (e.g. "What it cannot do")
    next to short label columns (e.g. "#") renders far wider than the
    page and everything on it -- text included -- reads as oversized,
    because nothing is actually wrapping into a properly page-width
    column. Confirmed absent from every table this script writes
    (RUBRIC_ACTION_PLAN.md quality pass, 2026-08-28).
    """
    n_cols = len(rows[0])
    # Proportional to each column's average cell length, not equal widths:
    # a five-word "V or V" column next to a full-sentence "What it guards"
    # column should not get the same share of the page.
    avg_len = [
        sum(len(row[c]) for row in rows) / len(rows)
        for c in range(n_cols)
    ]
    min_frac = 0.09  # floor so a short column (e.g. "#", "n") stays legible
    raw = [max(x, 1) for x in avg_len]
    total = sum(raw)
    fracs = [max(x / total, min_frac) for x in raw]
    # Re-normalize after applying the floor, so fractions still sum to 1.
    fracs = [f / sum(fracs) for f in fracs]
    widths_cm = [USABLE_WIDTH_CM * f for f in fracs]

    table.autofit = False
    table.allow_autofit = False
    for row in table.rows:
        for c, cell in enumerate(row.cells):
            cell.width = Cm(widths_cm[c])
            _tighten_cell_margins(cell)


def _tighten_cell_margins(cell) -> None:
    """Word's default table-cell margins (~0.19cm left/right, more top/
    bottom) are generous for a 3-column table and wasteful for a 6-column
    one; tighten them so more of each column's already-narrow width goes
    to text, not padding."""
    tc_pr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for side, val in (("top", 40), ("bottom", 40), ("left", 60), ("right", 60)):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        mar.append(node)
    tc_pr.append(mar)


def _set_field(paragraph, field_code, result_text=""):
    """Insert a real Word field (e.g. TOC, PAGE) into a paragraph."""
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = field_code
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_text = OxmlElement("w:t")
    fld_text.text = result_text
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r_element = run._r
    r_element.append(fld_begin)
    r_element.append(instr)
    r_element.append(fld_sep)
    r_element.append(fld_text)
    r_element.append(fld_end)


def _add_inline_runs(paragraph, text: str):
    """Handle **bold**, *italic*, and `code` spans within one line of text."""
    token_re = re.compile(r"(\*\*.+?\*\*|\*.+?\*|`.+?`)")
    parts = token_re.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*"):
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(10)
        else:
            paragraph.add_run(part)


def _shade_paragraph(paragraph, hex_color: str) -> None:
    """Apply a solid background shade to one paragraph (a code-block line),
    via the raw w:shd element python-docx has no wrapper for."""
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    paragraph.paragraph_format.element.get_or_add_pPr().append(shd)


def _add_code_block(doc, code_lines: list[str]) -> None:
    """Render a fenced ```...``` block as monospace paragraphs on a shaded
    background, one Word paragraph per source line so long listings don't
    collapse into a single unreadable run. Blank lines keep the shading so
    the block reads as one continuous panel."""
    for line in code_lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        _shade_paragraph(p, "F0F0F0")
        r = p.add_run(line if line.strip() else " ")
        r.font.name = "Consolas"
        r.font.size = Pt(9)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)  # spacer after block


def _parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    """Parse a pipe-delimited markdown table starting at `start` (the
    header row). Returns (rows, next_line_index)."""
    def split_row(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    header = split_row(lines[start])
    i = start + 2  # skip header + separator row
    rows = [header]
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append(split_row(lines[i]))
        i += 1
    return rows, i


def build() -> None:
    text = MD_PATH.read_text()
    lines = text.splitlines()

    doc = Document()

    # ---- base style ----
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.15

    for lvl, size, color in ((1, 16, NAVY), (2, 13, NAVY), (3, 12, NAVY)):
        style = doc.styles[f"Heading {lvl}"]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = color
        style.paragraph_format.space_before = Pt(18 if lvl == 1 else 12)
        style.paragraph_format.space_after = Pt(8)

    # ---- page numbers in footer ----
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_field(fp, "PAGE", "1")

    # ---- title page ----
    title_lines = [l for l in lines[:10] if l.strip()]
    # lines[0] = "# Supporting Report"; find module line, title line, author, supervisor, school
    module_line = next(l.strip("*").strip() for l in lines if l.startswith("**ECS8056"))
    full_title = next(l.strip("*").strip() for l in lines if l.startswith("**Memorisation-Robust"))
    author_line = next(l for l in lines if l.startswith("Yohan"))
    supervisor_line = next(l for l in lines if l.startswith("Supervisor"))
    school_line = next(l for l in lines if l.startswith("School"))

    doc.add_paragraph().add_run()  # top spacer
    doc.add_paragraph().add_run()
    doc.add_paragraph().add_run()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Supporting Report")
    r.bold = True
    r.font.size = Pt(28)
    r.font.color.rgb = NAVY

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(module_line)
    r.font.size = Pt(13)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(24)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(full_title)
    r.bold = True
    r.font.size = Pt(16)

    for line, size in ((author_line, 12), (supervisor_line, 12), (school_line, 11)):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(line)
        r.font.size = Pt(size)

    doc.add_page_break()

    # ---- table of contents ----
    p = doc.add_paragraph()
    r = p.add_run("Table of Contents")
    r.bold = True
    r.font.size = Pt(16)
    r.font.color.rgb = NAVY
    p.paragraph_format.space_after = Pt(12)

    toc_p = doc.add_paragraph()
    _set_field(
        toc_p,
        'TOC \\o "1-3" \\h \\z \\u',
        "Right-click and choose “Update Field” to build the table of contents.",
    )
    doc.add_page_break()

    # ---- body: walk the markdown from the first "## 1." heading onward ----
    body_start = next(i for i, l in enumerate(lines) if l.startswith("## 1. Project development"))
    i = body_start
    fig_counter = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            j = i + 1
            code_lines: list[str] = []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                code_lines.append(lines[j])
                j += 1
            _add_code_block(doc, code_lines)
            i = j + 1
        elif stripped.startswith("### "):
            doc.add_heading(stripped[4:], level=2)
            i += 1
        elif stripped.startswith("## "):
            doc.add_heading(stripped[3:], level=1)
            i += 1
        elif stripped.startswith("{{FIGURE:") or stripped.startswith("{{IMAGE:"):
            fig_counter += 1
            is_image = stripped.startswith("{{IMAGE:")
            if is_image:
                m = re.match(r"\{\{IMAGE:([^|]+)\|(.+)\}\}", stripped)
                img_path = ROOT / m.group(1)
            else:
                m = re.match(r"\{\{FIGURE:([a-z0-9_]+)\|(.+)\}\}", stripped)
                img_path = FIGURES / f"{m.group(1)}.png"
            caption = m.group(2)
            doc.add_picture(str(img_path), width=Inches(6.3))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap = doc.add_paragraph(style="Caption") if "Caption" in doc.styles else doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _add_inline_runs(cap, caption)
            for run in cap.runs:
                run.italic = True
                run.font.size = Pt(10)
            i += 1
        elif stripped == "---":
            i += 1  # rendered via heading spacing; no explicit rule needed
        elif stripped.startswith("| ") or stripped.startswith("|-"):
            # Table: detect header + separator + rows.
            rows, i = _parse_table(lines, i)
            n_cols = len(rows[0])
            # Smaller body text and tighter row spacing for wide tables
            # (5+ columns): the same 8.5pt/9.5pt that reads fine at 3
            # columns is cramped once that width is split six ways.
            header_size = Pt(9.5) if n_cols <= 4 else Pt(8.5)
            body_size = Pt(8.5) if n_cols <= 4 else Pt(7.5)
            table = doc.add_table(rows=1, cols=n_cols)
            table.style = "Light Grid Accent 1" if "Light Grid Accent 1" in [s.name for s in doc.styles] else "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            hdr_cells = table.rows[0].cells
            for c, text_cell in enumerate(rows[0]):
                # No cell.text = "" first: a freshly added cell's paragraph
                # already has zero runs, so clearing it first only adds a
                # stray empty run alongside the real one (harmless to
                # rendering, but pointless).
                p = hdr_cells[c].paragraphs[0]
                r = p.add_run(text_cell)
                r.bold = True
                r.font.size = header_size
            for row_vals in rows[1:]:
                row_cells = table.add_row().cells
                for c, cell_val in enumerate(row_vals):
                    p = row_cells[c].paragraphs[0]
                    p.paragraph_format.space_after = Pt(2)
                    _add_inline_runs(p, cell_val)
                    for run in p.runs:
                        run.font.size = body_size
            _set_table_column_widths(table, rows)
            doc.add_paragraph()  # spacer after table
        elif stripped == "":
            i += 1
        elif stripped.startswith("- "):
            bullet_style = "List Bullet" if "List Bullet" in doc.styles else None
            p = doc.add_paragraph(style=bullet_style)
            _add_inline_runs(p, stripped[2:])
            i += 1
        else:
            p = doc.add_paragraph()
            _add_inline_runs(p, stripped)
            i += 1

    # RUBRIC_ACTION_PLAN.md PS-5: force Word to recompute every field
    # (the TOC included) the moment the document opens, so a marker never
    # sees the literal "Right-click and choose 'Update Field'..." Word
    # placeholder -- python-docx cannot itself run Word's layout engine to
    # fill in real page numbers, so the field is written with that
    # placeholder text, but this setting makes Word overwrite it with the
    # real, page-numbered contents on the very first open, before anyone
    # looks at it.
    settings_el = doc.settings.element
    update_fields = OxmlElement("w:updateFields")
    update_fields.set(qn("w:val"), "true")
    settings_el.append(update_fields)

    doc.save(OUT_PATH)
    print(f"Saved: {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
