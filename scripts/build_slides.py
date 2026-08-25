"""Build the ECS8056 presentation deck as .pptx via python-pptx.

Sixteen slides, ten for the ten-minute video, all sixteen for the
twenty-minute live demo (the six "DEMO ONLY" slides are marked as such
in their own speaker notes so a presenter knows to skip them for the
video cut). Every number on every slide is transcribed from the same
values.tex / analysis/*.md sources the paper and the supporting report
cite, not re-derived here.

Usage: python scripts/build_slides.py
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "analysis" / "figures"
OUT_PATH = ROOT / "paper" / "slides" / "SLIDES.pptx"

NAVY = RGBColor(0x1F, 0x3A, 0x5F)
BLUE = RGBColor(0x1F, 0x5A, 0xA8)
LIGHT_BLUE = RGBColor(0xDB, 0xE9, 0xFB)
GREEN = RGBColor(0x21, 0x7A, 0x3A)
LIGHT_GREEN = RGBColor(0xDC, 0xF3, 0xDF)
RED = RGBColor(0xC0, 0x39, 0x2B)
LIGHT_RED = RGBColor(0xFB, 0xE0, 0xD6)
GREY = RGBColor(0x55, 0x55, 0x55)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK = RGBColor(0x1A, 0x1A, 0x1A)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def new_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def add_title(slide, text, size=32, color=NAVY, top=Inches(0.35), align=PP_ALIGN.LEFT,
              left=Inches(0.6), width=Inches(12.1)):
    box = slide.shapes.add_textbox(left, top, width, Inches(1.0))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = color
    run.font.name = "Calibri"
    return box


def add_body(slide, text, top=Inches(1.5), size=24, color=DARK, align=PP_ALIGN.LEFT,
             left=Inches(0.6), width=Inches(12.1), height=Inches(1.2), bold=False):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.name = "Calibri"
    return box


def add_notes(slide, text, demo_only=False):
    notes = slide.notes_slide.notes_text_frame
    if demo_only:
        text = "DEMO ONLY: cut for the 10-minute video. " + text
    notes.text = text


def add_picture_centered(slide, path, top, max_width, max_height):
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
    ratio = w / h
    width = max_width
    height = Emu(int(width / ratio))
    if height > max_height:
        height = max_height
        width = Emu(int(height * ratio))
    left = Emu(int((SLIDE_W - width) / 2))
    slide.shapes.add_picture(str(path), left, top, width=width, height=height)


def stat_callout(slide, left, top, width, height, number, label, color, light_color):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    box.fill.solid()
    box.fill.fore_color.rgb = light_color
    box.line.color.rgb = color
    box.line.width = Pt(2)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = number
    r.font.size = Pt(48)
    r.font.bold = True
    r.font.color.rgb = color
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = label
    r2.font.size = Pt(16)
    r2.font.color.rgb = DARK


def flow_box(slide, left, top, width, height, text, color, light_color, size=14):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    box.fill.solid()
    box.fill.fore_color.rgb = light_color
    box.line.color.rgb = color
    box.line.width = Pt(2)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.color.rgb = DARK
    return box


def add_table(slide, rows, left, top, width, height, header_color=NAVY, font_size=15):
    n_rows, n_cols = len(rows), len(rows[0])
    gt = slide.shapes.add_table(n_rows, n_cols, left, top, width, height).table
    for c, text in enumerate(rows[0]):
        cell = gt.cell(0, c)
        cell.text = text
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_color
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER
            for r in p.runs:
                r.font.bold = True
                r.font.size = Pt(font_size)
                r.font.color.rgb = WHITE
    for ri in range(1, n_rows):
        for c in range(n_cols):
            cell = gt.cell(ri, c)
            cell.text = rows[ri][c]
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if ri % 2 else LIGHT_BLUE
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.CENTER if c > 0 else PP_ALIGN.LEFT
                for r in p.runs:
                    r.font.size = Pt(font_size)
                    r.font.color.rgb = DARK
    return gt


def build() -> None:
    prs = new_deck()

    # ---- Slide 1: title ----
    s = blank_slide(prs)
    rect = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    rect.fill.solid()
    rect.fill.fore_color.rgb = NAVY
    rect.line.fill.background()
    add_title(s, "Dynamic, Template-Based Benchmarking Resists\nContamination-Induced Score Inflation",
               size=34, color=WHITE, top=Inches(1.6), left=Inches(0.8), width=Inches(8.0))
    add_body(s, "Yohan Sneider Sanchez Vega  |  40492566", top=Inches(4.0), size=22, color=WHITE,
              left=Inches(0.8), width=Inches(8.0))
    add_body(s, "ECS8056 MSc AI Themed Research Project  |  Supervisor: Pinzhen Chen",
              top=Inches(4.6), size=16, color=RGBColor(0xC9, 0xD8, 0xEC), left=Inches(0.8), width=Inches(8.0))
    photo_box = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(9.6), Inches(1.8), Inches(2.8), Inches(2.8))
    photo_box.fill.solid()
    photo_box.fill.fore_color.rgb = RGBColor(0x33, 0x4E, 0x73)
    photo_box.line.color.rgb = WHITE
    photo_box.line.width = Pt(2)
    tf = photo_box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "photo"
    r.font.size = Pt(16)
    r.font.color.rgb = RGBColor(0xC9, 0xD8, 0xEC)
    add_notes(s, "Title, name, student number, on camera for the photo requirement.")

    # ---- Slide 2: the problem ----
    s = blank_slide(prs)
    add_title(s, "The problem: benchmark contamination")
    add_body(s, "A benchmark's score stops meaning anything once the model has seen its problems.",
              top=Inches(1.3), size=24)
    add_picture_centered(s, FIG / "contamination_loop.png", Inches(2.1), Inches(6.5), Inches(5.0))
    add_notes(s, "State the one-sentence problem, point at the loop diagram, move on quickly.")

    # ---- Slide 3: why test generation ----
    s = blank_slide(prs)
    add_title(s, "Why test generation")
    add_body(s, "A test suite is checked by running it. No answer key to leak.",
              top=Inches(1.6), size=26)
    add_body(s, "Coverage checks execution, not correctness. An answer key is static content too.",
              top=Inches(3.3), size=18, color=GREY)
    add_notes(s, "Test generation is scored by execution, unlike a fixed-answer benchmark.")

    # ---- Slide 4: what was built ----
    s = blank_slide(prs)
    add_title(s, "What was built")
    add_picture_centered(s, FIG / "flow_diagram.png", Inches(1.15), Inches(12.2), Inches(6.1))
    add_notes(s, "Walk the diagram left to right, then down through the two gates and the three experiments.")

    # ---- Slide 5: template and instance side by side ----
    s = blank_slide(prs)
    add_title(s, "A template, and one generated instance")
    left_box = s.shapes.add_textbox(Inches(0.6), Inches(1.4), Inches(5.9), Inches(5.6))
    tf = left_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = "Template: L3-clamp-seq-001"; r.font.bold = True; r.font.size = Pt(18); r.font.color.rgb = NAVY
    p2 = tf.add_paragraph()
    r2 = p2.add_run()
    r2.text = "Body skeleton + parameter domain\n+ reference oracle + docstring\ntemplate with synonym variation."
    r2.font.size = Pt(17)
    r2.font.color.rgb = DARK

    right_box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.7), Inches(1.4), Inches(6.0), Inches(5.6))
    right_box.fill.solid()
    right_box.fill.fore_color.rgb = RGBColor(0x27, 0x2B, 0x33)
    right_box.line.fill.background()
    tf = right_box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.25)
    tf.margin_top = Inches(0.25)
    code = ('def sum_values(values):\n'
            '    """Build a list with values clamped\n'
            '    within the floor and ceiling,\n'
            '    or else unchanged."""\n'
            '    agg = []\n'
            '    for sample in values:\n'
            '        if sample < 8:\n'
            '            agg.append(8)\n'
            '        elif sample > 33:\n'
            '            agg.append(33)\n'
            '        else:\n'
            '            agg.append(sample)\n'
            '    return agg')
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = code
    r.font.name = "Consolas"
    r.font.size = Pt(14.5)
    r.font.color.rgb = RGBColor(0xE8, 0xE8, 0xE8)
    add_notes(s, "Point out the misleading name: sum_values clamps, it never sums. That is deliberate.")

    # ---- Slide 6: scoring ----
    s = blank_slide(prs)
    add_title(s, "How scoring works")
    labels = [("Generated\ntest suite", NAVY, LIGHT_BLUE),
              ("EXEC GATE\nimports & collects?", RED, LIGHT_RED),
              ("BASELINE GATE\npasses on the real\nfunction?", RED, LIGHT_RED),
              ("Mutation score\nkilled / total", GREEN, LIGHT_GREEN)]
    x = Inches(0.6)
    w = Inches(2.85)
    gap = Inches(0.25)
    for text, edge, face in labels:
        flow_box(s, x, Inches(2.6), w, Inches(1.5), text, edge, face, size=16)
        x = Emu(int(x) + int(w) + int(gap))
    add_body(s, "Two gates, in order. A generated suite that fails one never reaches the next.",
              top=Inches(4.7), size=20, color=GREY)
    add_notes(s, "Emphasise the two gates are sequential, and mutation score is only reached after both pass.")

    # ---- Slide 7: models and benchmarks ----
    s = blank_slide(prs)
    add_title(s, "Nine models, two static benchmarks")
    rows = [
        ["Provider", "Frontier", "Efficient"],
        ["OpenAI", "GPT-5", "GPT-5 mini"],
        ["Anthropic", "Claude Sonnet 4.6", "Claude Haiku 4.5"],
        ["Google", "Gemini 3.1 Pro Preview", "Gemini 3.1 Flash-Lite"],
        ["Open-source", "Qwen2.5-Coder 32B / 7B / 1.5B", ""],
    ]
    add_table(s, rows, Inches(0.9), Inches(1.5), Inches(11.5), Inches(3.0), font_size=17)
    add_body(s, "Plus ULT, a decontaminated static benchmark, and PLT, its leaked twin.",
              top=Inches(5.1), size=20, color=GREY)
    add_notes(s, "Nine canonical models, four providers, plus the ULT/PLT static comparator pair.")

    # ---- Slide 8: contamination experiment ----
    s = blank_slide(prs)
    add_title(s, "Creating contamination on purpose")
    add_body(s, "Fine-tune the smallest open-source model on ULT's ground-truth tests.",
              top=Inches(1.5), size=24)
    add_body(s, "Re-score it on ULT, on PLT, and on a fresh dynamic instantiation it never saw.",
              top=Inches(3.1), size=22, color=GREY)
    add_notes(s, "This is the causal probe: LoRA fine-tune on repair-verified ULT ground truth, 112 pairs.")

    # ---- Slide 9: headline result ----
    s = blank_slide(prs)
    add_title(s, "Headline result")
    stat_callout(s, Inches(0.9), Inches(1.6), Inches(3.6), Inches(2.6), "+99.1pp", "seen-ULT gain\n(trained on)", RED, LIGHT_RED)
    stat_callout(s, Inches(4.9), Inches(1.6), Inches(3.6), Inches(2.6), "+8.7pp", "generic control gain\n(dynamic L1-L3)", GREY, RGBColor(0xEC, 0xEC, 0xEC))
    stat_callout(s, Inches(8.9), Inches(1.6), Inches(3.6), Inches(2.6), "+0.0pp", "dynamic-L4 gain\n(hardest tier)", GREEN, LIGHT_GREEN)
    add_body(s, "The gain the model was trained to produce does not reach the dynamic benchmark.",
              top=Inches(4.6), size=22, color=DARK)
    add_notes(s, "99.1 points on the trained split, 8.7 points of that is plain improvement, 0.0 points on the dynamic benchmark's hardest tier.")

    # ---- Slide 10: onset curve ----
    s = blank_slide(prs)
    add_title(s, "The onset curve: two timescales")
    add_picture_centered(s, FIG / "comparison_c_onset_curve.png", Inches(1.15), Inches(11.5), Inches(5.8))
    add_notes(s, "Epoch 1's jump is generic capability. The seen-only climb from epoch 5 is memorisation.")

    # ---- Slide 11: hypotheses and verdicts ----
    s = blank_slide(prs)
    add_title(s, "Six hypotheses, nine verdicts")
    rows = [
        ["Hypothesis", "Verdict"],
        ["H1 Test 1: Dynamic vs ULT", "Not supported"],
        ["H1 Test 2: ULT vs PLT", "Mixed"],
        ["H2: fine-tuning DiD", "Supported"],
        ["H2-supplementary", "Supplementary"],
        ["H3: tier gradient", "Supported (trend)"],
        ["H4: tier interaction", "Dropped"],
        ["H5: stability", "Threshold not met"],
        ["H6 clause 1: proxy correlation", "Mixed"],
        ["H6 clause 2: dynamic vs static", "Not supported"],
    ]
    add_table(s, rows, Inches(1.6), Inches(1.15), Inches(10.1), Inches(5.9), font_size=15)
    add_notes(s, "Walk down the column. Do not skip the two not-supported rows or the dropped row.")

    # ---- Slide 12: limitations ----
    s = blank_slide(prs)
    add_title(s, "Limitations")
    add_body(s, "One model, one fine-tune method. Rank stability falls short of its target.",
              top=Inches(1.6), size=24)
    add_body(s, "Template-generated code, not scraped from real repositories. Equivalent-mutant validation not complete at submission.",
              top=Inches(3.3), size=20, color=GREY)
    add_notes(s, "Name these plainly: single fine-tune, stability shortfall, synthetic code, unfinished validation sample.")

    # ---- Slide 13: future work ----
    s = blank_slide(prs)
    add_title(s, "Future work")
    add_body(s, "Finish the mutant sample. Test the causal result at larger scale.",
              top=Inches(1.6), size=24)
    add_body(s, "Semantic-preserving operators. A public release of the template corpus.",
              top=Inches(3.3), size=20, color=GREY)
    add_notes(s, "Four items, none of them a surprise given the limitations slide.")

    # ---- Slide 14: DEMO ONLY repo structure ----
    s = blank_slide(prs)
    add_title(s, "DEMO ONLY: repository structure")
    add_body(s, "src/ the pipeline. scripts/ every analysis, plot, and build step. tests/ 152 tests. analysis/ every result and interpretation. paper/ the paper and this deck.",
              top=Inches(1.6), size=20)
    add_notes(s, "Live demo only. Open the repo, point at each top-level directory in turn.", demo_only=True)

    # ---- Slide 15: DEMO ONLY verification ----
    s = blank_slide(prs)
    add_title(s, "DEMO ONLY: how the numbers are checked")
    add_body(s, "152 tests. A citation gate that checks every hand-typed number against live output. An 11-bug error ledger, each with a named fix.",
              top=Inches(1.6), size=20)
    add_notes(s, "Live demo only. Run the citation gate on screen if time allows; show one row of the error ledger.", demo_only=True)

    # ---- Slide 16: DEMO ONLY what I'd do differently ----
    s = blank_slide(prs)
    add_title(s, "DEMO ONLY: what I would do differently")
    add_body(s, "Build the citation gate and config logging in week one.",
              top=Inches(1.6), size=22)
    add_body(s, "Budget the fifth instantiation from the start. Start the mutant sample earlier.",
              top=Inches(3.3), size=20, color=GREY)
    add_notes(s, "Live demo only, closing reflection.", demo_only=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT_PATH)
    print(f"Saved: {OUT_PATH.relative_to(ROOT)} ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
