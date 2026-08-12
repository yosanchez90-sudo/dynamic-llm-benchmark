# Gap list: what the paper still needs, and what does not exist yet

Everything below is either (a) something outside this write-up's control
to close (an external action item), or (b) a disclosed limitation the
paper already states honestly rather than papers over. Nothing here was
worked around with a fabricated number or a placeholder figure -- per the
project's own citation-gate discipline, a missing number is reported
missing, not guessed.

## External action items (not blocked, but not closeable from here)

1. **EEECS GitLab mirror.** No `eeecs` remote is configured
   (`git remote -v` shows only `origin`). Once the URL is available:
   ```
   git remote add eeecs <EEECS_GITLAB_URL>
   git push eeecs main
   ```
   Not attempted here -- this environment cannot authenticate to a
   second remote, and the URL was still pending from the supervisor as of
   the last status check this write-up phase began from.

2. **Reference [16] (`dong2026generalization`) metadata is
   `PARTIALLY_VERIFIED`, not `COMPLETE`**, in `paper/references.yaml`.
   The DOI resolves to a real, live IEEE TSE record; the full author
   list, exact page range, and precise venue string were not
   independently confirmed (IEEE Xplore's page returned an empty
   response to two fetch attempts, consistent with a paywall/bot-check
   block already noted elsewhere in this file's history). A final check
   with institutional IEEE Xplore access, if convenient before
   submission, would upgrade this to fully verified; the citation as it
   stands is not believed wrong, only not independently re-derived from
   the primary source the way every other reference in the file was.

## Disclosed limitations (already stated in the paper itself, not hidden)

3. **Equivalent-mutant validation is 0/120 complete**
   (`analysis/equiv_mutants/inspection_sheet.xlsx`). The paper's
   Additional Disclosures subsection states this plainly rather than
   reporting a placeholder validated score. The pipeline is wired and
   ready: `scripts/build_paper_values.py` picks up
   `analysis/equiv_mutants/validated_scores.csv` automatically the moment
   `scripts/compute_validated_score.py` has real rows to write, with zero
   further code change needed (verified by re-running the generator with
   the file absent: the conditional block is a confirmed no-op).

4. **No results table, only three figures.** The module handbook's
   "figures/tables numbered, captioned, referenced" requirement is
   satisfied by the three figures actually used (onset curve,
   collapse-vs-survival, ranking-matrix heatmap), each numbered,
   captioned, and referenced from the text that discusses it. A fourth
   artifact -- a summary table of all six hypothesis verdicts -- was
   considered and not added: the paper compiles at exactly 8 pages, the
   strict hard limit, with no slack for an additional table without
   cutting prose elsewhere. If a verdict table is wanted, the source data
   already exists (`analysis/HYPOTHESIS_COVERAGE_AUDIT.md`'s own
   per-hypothesis verdict column) and would need roughly half a column of
   space reclaimed from elsewhere to fit.

5. **`paper/paper.docx`'s reference list uses pandoc's default citation
   style, not IEEE numeric `[1]`-style in-text citations.** Content is
   complete and independently verified (all six hypothesis verdicts,
   every `\NumXXX` macro resolved to its live value, all 18 references
   present) via a scripted diff of the converted text against
   `paper/values.tex` and `paper/references.bib`, but no IEEE CSL style
   file was available in this environment to match `paper.pdf`'s
   citation formatting exactly. `paper.pdf`, built directly by the
   `IEEEtran` LaTeX class, is the authoritative, venue-formatted
   deliverable; the `.docx` is a secondary, editable convenience copy.

6. **The compiled PDF has not had a full manual page-by-page visual
   proofread in this pass** (figure placement, column balance, and
   general layout were checked only via `pdftotext` content extraction
   and the LaTeX compiler's own warnings, both of which came back clean,
   but neither substitutes for looking at the rendered pages). Worth a
   final visual pass before submission, particularly for the two pages
   carrying a figure (results, pages 4 and 5-6) where two-column
   float placement can occasionally surprise.

## Explicitly not gaps (checked and closed this phase)

- Abstract, keywords, reference count, and page count are all within the
  module handbook's stated limits (213 words against a ~200-word target;
  5 keywords against a limit of 5; 18 references against a limit of 35;
  8 pages against a strict 8-page cap).
- Every quantitative claim in the paper's prose is a `\NumXXX` macro
  traced to a live `analysis/*.csv` source or an explicitly marked
  pre-registered design constant -- see `paper/NUMBER_AUDIT.md`. Zero
  hand-typed result values remain (citation gate: 0 hand-typed findings).
- All 18 references in `paper/references.yaml` are cited at least once
  in the prose; all `\cite{}` keys resolve; zero bibtex warnings.
