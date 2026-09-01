# Figure and table specification

Scope: every figure produced by the matplotlib scripts registered in
`scripts/build_thesis_assets.py`, and every LaTeX table in `paper/`. Derived from the two
annotated screenshots plus a pass over the compiled `paper_v3.pdf`.

Apply these as **global rules in the plotting module**, not as per-figure patches — the
figures regenerate, so a hand-fix will be undone on the next `build_thesis_assets.py` run.

---

## G — Global rules

### G-1 · No titles on figures
No `ax.set_title()`, no `fig.suptitle()`. In IEEE style the caption is the title; a plot
title duplicates it and, in a two-column layout, wastes vertical space that the data should
have.

- Panel identity goes in the **axis labels**, which already carry it: the y-axis reads
  "Baseline pass rate (%)" and "Verbatim-match rate (%)". Delete the panel titles
  "Baseline pass rate" and "Verbatim reproduction (seen-ULT)" — they say nothing the y-axis
  and the caption do not.
- For multi-panel figures where the caption must point at a specific panel, use a small
  bold **(a) / (b)** label in the upper-left corner of each axes, and refer to "(a)" and
  "(b)" in the caption instead of "Left:" / "Right:".
- Fig. 2's suptitle ("Cross-family: raw Mut@K's BigCodeBench correlation collapses;
  coverage-adjusted survives") is an *argument*, not a label — move it verbatim into the
  caption. Fig. 2's two panel titles ("raw Mut@K", "coverage-adjusted") become (a) / (b),
  with the metric named in the caption and in the axis label.
- Fig. 3's title block ("Ranking matrix: cross-benchmark rank agreement / ** significant
  after Holm-Bonferroni (12-test family) / * significant raw p<0.05 only, not after
  correction") is a title plus a significance key. The title goes to the caption; the key
  goes to the caption as a final sentence. Fig. 3's panel labels ("Canonical (9 models)",
  "Canonical + cross-family (13 models)") are genuine data labels — keep them, but as
  left-aligned small text or (a)/(b), not centred titles.

### G-2 · No explanatory prose inside the axes
Anything a reader would read as a sentence belongs in the caption.

- **Delete** Fig. 1's floating text block: *"Two timescales: a shared, one-time
  generic-improvement jump (epoch 0→1, all arms) vs. a slower, seen-ULT-only memorization
  climb (5→20)."* It already exists, almost word for word, in the caption. This is the
  block marked "Text to be removed" in the screenshot.
- **Keep** short in-axes annotations that label a *region of the data* and would be
  ambiguous in a caption: "generic gain (all arms, epoch 0→1)" and "memorization (seen-ULT
  only, epochs 5→20)" sit on the curve regions they describe, and the shaded span is what
  they point at. Keep them, but tighten each to one line and drop the parenthetical epoch
  ranges — those are visible on the x-axis and already in the caption.
- **Keep** statistical annotations that are data: Fig. 2's `n_models=7  Kendall τ=0.429
  p=0.2413` and Fig. 3's per-cell `τ` / `n` values.

### G-3 · Figures fill the column
Both panels in Fig. 1 currently sit inside a box noticeably narrower than the column, with
dead margin on the right — this is what "make bigger to the edge" marks in the screenshot.

Confirm that thetext size is not as small but not the same as the normal letter in the
report, to ensure that the figure is readable and fits well in the column. 

Set the figure width to the **actual text measure**, not a default:

```python
COL_W  = 3.5   # inches, IEEE single column
FULL_W = 7.16  # inches, IEEE double-column span (figure*)

fig, ax = plt.subplots(figsize=(COL_W, COL_W * 0.72), constrained_layout=True)
fig.savefig(path, dpi=400, bbox_inches="tight", pad_inches=0.02)
```

- Use `constrained_layout=True` (or `tight_layout()`) so removing the titles reclaims the
  space rather than leaving a gap.
- In LaTeX, include at `\includegraphics[width=\columnwidth]{...}` (or `\textwidth` inside
  `figure*`) and **never** at a hand-tuned scale factor — a scale factor plus a
  `bbox_inches="tight"` export is what produces the inconsistent whitespace visible now.
- Fig. 1 is a two-panel figure stacked vertically inside one column. Once the titles and the
  floating text block are gone, either keep the stack with each panel at
  `figsize=(3.5, 1.9)`, or promote it to a `figure*` two-panel side-by-side at
  `figsize=(7.16, 2.4)`. Side-by-side reads better and matches the caption's "(a) … (b) …".

### G-4 · Typography
- One font size scheme across every figure: axis labels 8 pt, tick labels 7 pt, in-axes
  annotations 7 pt, legend 7 pt. After `\includegraphics[width=\columnwidth]` these land at
  roughly the caption's size, which is the target.
- Set it once: `plt.rcParams.update({"font.size": 8, "axes.labelsize": 8,
  "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7})`.
- Export vector PDF for the paper (`.pdf`) and PNG only for the Word supporting report.
  Fig. 2's markers and Fig. 3's cell text will look soft at 8 pp otherwise.

### G-5 · Colour, markers, and the red-ring convention
- Every series must be distinguishable in greyscale and to a colour-blind reader: pair each
  colour with a distinct marker and line style (Fig. 1 already does this — circle/square/
  triangle, solid/dashed/dotted — keep that pattern everywhere).
- Fig. 2's red-ringed "thin cell (n_defined<20)" marker is a good convention. Use the
  **same** ring in the new main results table (PA-1) and anywhere else thin cells appear,
  and define it once in a shared caption phrase.
- Do not encode meaning in colour alone in Fig. 3's heatmap — the `**` / `*` significance
  markers already carry it, which is correct.

### G-6 · Captions carry the argument
IEEE captions sit below the figure and can be several sentences. Structure each as:
*what is plotted → what the reader should see → any caveat*. Fig. 1's current caption is
close to right; it just needs to absorb the deleted text block and drop the awkward
trailing parenthetical about the L1–L3 control — fix this by giving the plotted L1–L2
series and the L1–L3 endpoint-control population unambiguous, distinct names (done in
`scripts/plot_comparison_c_onset_curve.py`'s `SPLIT_STYLE` labels) instead of explaining
the mismatch in the caption.

---

## T — Tables

### T-1 · Table I overflows the text block
Marked "table out of margins" in the screenshot. Fixes, in order of preference:

1. Promote to `table*` so it spans both columns (it is already a wide, four-column table
   with long prose cells — it wants the full width).
2. Set explicit column widths with `p{}` / `tabularx` so the Prediction column wraps instead
   of pushing the Verdict column past the margin:
   ```latex
   \begin{tabularx}{\textwidth}{@{}l l X l@{}}
   ```
   with `X` on Prediction and `l` on RQ / Hyp. / Verdict.
3. Only if 1 and 2 are not enough: `\small` or `\footnotesize` on the table body. Do not
   use `\resizebox` — it desynchronises the table's font size from the caption's, which a
   marker checking IEEE compliance will notice.
4. Remove the words suplementary from the RQ and Hyp. columns (see T-3) so the table fits
   without shrinking the font. These details will be given in the supporting text, where
   the table is already marked with a `SUPPLEMENTARY`.

Run a `\overfull\hbox` check after: `latexmk` warnings for the table's page must be clean.

### T-2 · Move Table I's RQ legend inside the table
The yellow block below Table I ("RQ1 contamination resistance vs a static benchmark; RQ2
effect of complexity tier; …") is marked "Organise inside the table, wrap text". It is a
table note, so make it one:

```latex
\multicolumn{4}{@{}p{\textwidth}@{}}{\footnotesize
  RQ1: contamination resistance versus a static benchmark. RQ2: effect of complexity tier.
  RQ3: whether overestimation is larger at low tiers. RQ4: stability of rankings across
  re-instantiations. RQ5: agreement with an external code-generation proxy.} \\
```
placed after `\bottomrule`, with the `p{}` column doing the wrapping. Set each RQ on its own
line if it fits — a five-item legend as one wrapped paragraph is harder to scan than five
short lines.

Note that this legend is currently the **only** place RQ1–RQ5 are defined. `PA-7` moves
them into the Introduction text; keep the table note as well, since a table should be
readable standalone.

### T-3 · Trim the redundant labels in Table I
The screenshot marks three cells as "text to be removed":

- **`RQ1 (supplementary)`** in the RQ column → just `RQ1`. The supplementary status is
  already carried by the Hyp. column and by the `SUPPLEMENTARY` verdict.
- **`H2-supplementary`** in the Hyp. column → `H2-supp.` (or `H2s`), so the column stays
  narrow. Define the abbreviation in the table note.
- **`H1 Test 1` / `H1 Test 2`** → move the test index out of the label. Either use a nested
  layout (`H1` once, spanning two rows via `\multirow`, with `Test 1` / `Test 2` in a thin
  adjacent column) or shorten to `H1a` / `H1b` and define it in the note. Same treatment for
  `H6 clause 1` / `H6 clause 2` → `H6a` / `H6b`, which are equally wide and equally
  repetitive.

The goal is a Hyp. column narrow enough that the Prediction column gets the width it needs.

### T-4 · Add a section pointer column
§4 reports the hypotheses out of RQ order (4.1 = H2, 4.3 = H1 Test 1, …), for a stated and
good reason. Add a `§` column to Table I giving the subsection for each row. It costs about
two characters of width and removes the only real navigation friction in the results
section.

### T-5 · General table rules
- `booktabs` only: `\toprule` / `\midrule` / `\bottomrule`, no vertical rules. Tables II and
  III already follow this — keep it consistent in the new tables from `PA-1` and `PA-3`.
- Caption above the table (IEEE), caption below the figure. Currently correct.
- Every table that reports a mean must also report the `n` it was taken over — this is
  error-ledger bug 7's own rule, and the new results tables must not reintroduce it.
- Name the metric in every caption. Table II reports `baseline_pass_rate`, not Mut@K, and
  the caption does not currently say so.
- Number formatting: one convention for percentages (`99.1`), one for correlations
  (`0.429`), one for p-values (`p = 0.0034`, and `p < 0.001` below that). Table III mixes
  `-2.3` and `2.3` — use a consistent minus sign (`\textminus` or siunitx) and align on the
  decimal point with `S` columns from `siunitx`.
- Table III's header renders as `B A S E L I N E_P A S S_R A T E` in the extracted text —
  a letter-spaced small-caps rendering of a monospace identifier. Set metric identifiers in
  `\texttt{}` and outside any `\textsc{}` scope so they stay readable.

---

## Per-figure checklist

| Figure | Actions |
|---|---|
| **Fig. 1** (contamination across epochs) | G-1 remove both panel titles · G-2 delete the floating "Two timescales" block, tighten the two region annotations · G-3 resize to column/full width, consider side-by-side · C-9 rename the control series so the legend and the text agree · caption absorbs the deleted text |
| **Fig. 2** (cross-family correlation) | G-1 suptitle → caption, panel titles → (a)/(b) · G-3 promote to `figure*` at 7.16 in if the two panels stay stacked · keep the τ/p/n annotations and the thin-cell ring · define the ring in the caption |
| **Fig. 3** (rank-agreement heatmap) | G-1 title and significance key → caption · keep the two panel labels as (a)/(b) with the model count in the caption · check cell text is ≥ 6 pt after scaling · G-5 ensure the diverging colormap is legible in greyscale |
| **Table I** | T-1 fit to margins · T-2 legend as a wrapped table note · T-3 trim labels · T-4 add § column |
| **Table II** | C-10 add the fifth population, add a DiD column, name the metric in the caption |
| **Table III** | C-13 align the condition label with the prose · T-5 fix the identifier rendering and the minus signs |
| **New: main results** (PA-1) | Follow T-5 throughout; include `n_defined` and the thin-cell ring |
| **New: H3 tier effect** (PA-3) | Figure preferred over table; no title; y = mutation score, x = tier L1…L4, one line per model, legend outside the axes if it crowds |
| **New: H5 stability** (PA-3) | Mean ± SD per model as a point-with-error-bar plot, or reuse the Fig. 3 heatmap style for the pairwise τ matrix — whichever keeps the "SD is tiny, τ is not" contrast visible in one glance |

---

## Where to implement

All of G-1 to G-5 belong in one place — a shared style module imported by every plotting
script under the `build_thesis_assets.py` registry — so that "no titles" and "fill the
column" are properties of the pipeline rather than of individual figures. A per-figure fix
will not survive the next regeneration.
