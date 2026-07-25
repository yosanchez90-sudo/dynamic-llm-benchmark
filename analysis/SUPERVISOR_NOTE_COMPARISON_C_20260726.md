# Supervisor note (draft — not sent) — Comparison C training-data quality

Following up on the 2026-07-25 meeting's Comparison C approval: building the ULT
training pairs surfaced a data-quality issue worth flagging before we go further.
Only 8.5% of ULT's own shipped ground-truth tests (the ones we're using as
fine-tune targets) actually pass against ULT's own shipped reference code — the
rest have either a wrong expected value or code that can't run without a missing
import. We built a repair pipeline that mechanically corrects the "wrong expected
value" cases (re-deriving the correct output from ULT's own code, verified through
our real scoring harness) and recovers 1,017 of the ~3,676 problems as usable
training pairs — but only 112 of the 400 core_400 evaluation problems (28%) end up
verified-seen-in-training, and a ceiling analysis says that can't be pushed past
roughly 53% even with more repair engineering, because a third of the failures are
the underlying code itself being broken, which we can't fix without also touching
the pre-fine-tune baseline we've already measured against.

Rather than pause on this, we're proceeding: training on the 1,017 verified pairs
as-is, and analysing core_400 ULT results split by seen-in-training (112) vs not
(288) — an adaptation of the approved design, not a change to its intent, and it
gives us a sharper within-benchmark contrast (same CC band, same code, only
memorization differs) alongside the original ULT-vs-Dynamic comparison. Full
taxonomy and the pre-registered analysis plan are in
`data/raw/ult_plt/PROVENANCE.md` and `analysis/COMPARISON_C_ANALYSIS_PLAN.md` if
you want the detail. Flagging this week in case you'd rather we handle it
differently before the fine-tune run goes in.
