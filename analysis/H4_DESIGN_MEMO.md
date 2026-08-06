# H4 (RQ3) design memo — three options, costs, and a recommendation

**DECISION RECORDED 2026-08-05 — approved by supervisor Pinzhen Chen:
option (c), CLOSED, not built.** H4 is declared untestable-by-construction
on the CC-overlap evidence below; no mixed-effects model will be built,
`statsmodels` is not added as a dependency, and RQ3 is answered
narratively (H3's within-Dynamic tier gradient + this structural finding
itself — see `PROJECT_BRIEF.md` §3.1's H4 row and
`analysis/OPEN_ITEMS.md`). **This memo is preserved as-is below, unedited,
as the record of the reasoning behind that decision** — it originally
recommended option (b) (a Dynamic-only mixed model); the supervisor's
decision went with (c) instead, for reasons that are the supervisor's own
judgement call, not a correction of this memo's analysis. The CC-overlap
quantification and the rejection of option (a) both still stand as
accurate evidence regardless of which of (b)/(c) was ultimately chosen.

---

**Decision memo only — nothing for H4 is implemented in this document or
alongside it.** Per instruction: the user decides which option to pursue,
and it goes to the supervisor before anything is built. This memo exists
to make that decision informed, not to pre-empt it.

## Does an earlier H4a/H4b split already govern this?

**No.** Checked directly: no mention of "H4a"/"H4b" (or any restructuring
of H4) exists anywhere in `PROJECT_BRIEF.md` or the git history
(`git log --all --grep`). The "ULT contains only CC≥8 functions" fact is
real and already documented in several places (`data/raw/ult_plt/
PROVENANCE.md`'s "Tier / CC scoping" section, `analysis/
ULT_DATA_QUALITY_AUDIT.md` finding 2, `analysis/HYPOTHESIS_COVERAGE_AUDIT.md`'s
H4 entry) — but it was never formalised into a decision about what H4
should measure instead. This memo is that decision's first formal
treatment, not a rediscovery of something already settled.

## The structural problem, quantified

RQ3 asks whether static benchmarks overestimate performance at *lower*
tiers more than higher ones, relative to Dynamic. This presupposes ULT/PLT
has multiple tiers to compare a slope across. **It doesn't, and the
mismatch is large, not marginal** — computed directly (not assumed) for
this memo:

**Dynamic's tier CC ranges** (this project's own `compute_cc`, one
canonical instantiation per template, seed 42 — the same AST-based
measure used for both Dynamic and ULT/PLT):

| Tier | n templates | CC min | CC max | CC mean |
|---|---|---|---|---|
| L1 | 15 | 1 | 1 | 1.0 |
| L2 | 15 | 2 | 3 | 2.3 |
| L3 | 15 | 4 | 7 | 4.7 |
| L4 | 15 | 8 | 11 | 8.7 |

**ULT/PLT's CC distribution post-filter** (`data/raw/ult_plt/PROVENANCE.md`):
ULT's recomputed quartiles are **[8, 10, 12, 16, 82]** (min/Q1/median/Q3/max);
PLT (excl. ULT overlap) is **[8, 10, 12, 16, 1729]** — identical up to Q3,
diverging only in an extreme max outlier. Comparison B's own CC-quartile
bands (`analysis/comparison_b_matched_cc.csv`): CC8-9 (n_problems=19 ULT records),
CC10-11 (n_problems=119), CC12-15 (n_problems=108), CC16+ (n_problems=93).

**The overlap**: Dynamic's L1-L3 (CC 1-7) has **zero** representation in
ULT/PLT at all — both are filtered to CC≥8 by construction (ULT's own
authors' filter, independently confirmed by this project's own
recomputation). Dynamic's L4 (CC 8-11) overlaps only the bottom two of
Comparison B's four CC bands (CC8-9 and CC10-11, 138 of 339 ULT records
across the four bands, ~41%) — the CC12-15 and CC16+ bands (59% of the
already-CC-filtered ULT sample) have **no Dynamic counterpart whatsoever**.
And within the sliver where the two benchmarks' CC ranges do overlap,
Dynamic contributes only its single hardest tier (L4) — there is no
Dynamic tier *variation* inside the overlap region to compare against
ULT/PLT's own CC-band variation there.

**Consequence for option (a) below**: a tier×benchmark interaction built
on CC-quartile bands would be comparing two axes that share almost no
common range and, where they do overlap, one side (Dynamic) has no
internal variation left to contribute. This is not a "the interaction
might be weak" concern — it is a "the interaction is not measuring what
RQ3 asks" concern.

## Option (a) — CC-quartile bands as ULT/PLT's tier-analog

**What it would do**: reuse Comparison B's existing CC8-9/CC10-11/CC12-15/
CC16+ bands as ULT/PLT's "tier" variable, giving both sides of the
interaction a CC-derived ordinal factor.

**Cost**: low — the bands already exist and are already computed
(`src/Analysis/comparison.py::matched_cc_table`); this option is "reuse,"
not "build new."

**Threat, per the overlap evidence above**: the resulting interaction term
would be dominated by the fact that Dynamic only occupies the bottom
~40% of ULT/PLT's CC range, and only via one tier (L4) with no internal
Dynamic variation there. Any interaction effect this produces conflates
"the two benchmarks' CC ranges don't line up" with "the two benchmarks
respond differently to difficulty" — the two are not separable in this
design. **Not recommended**: it produces a number, but not one that
answers RQ3's actual question.

## Option (b) — Dynamic-only mixed model; declare the cross-benchmark form untestable

**What it would do**: fit a proper mixed-effects model on Dynamic alone
(tier as a fixed effect, model as a random effect — the "model as random
effect" requirement PROJECT_BRIEF.md §3.1 specifies, which neither H3 nor
any existing analysis in this project currently provides), and separately,
explicitly state that RQ3's cross-benchmark form (dynamic vs static,
"which overestimates more at lower tiers") cannot be tested given ULT/PLT
has no tier variation at all in the CC range Dynamic's lower tiers occupy.

**Cost**: moderate — requires adding a mixed-model dependency
(`statsmodels.formula.api.mixedlm` or equivalent; not currently installed,
`analysis/HYPOTHESIS_COVERAGE_AUDIT.md` confirmed), reshaping Dynamic's
result rows into long format (tier, model, mutation_score), and fitting +
interpreting a variance-components model — nontrivial but well within
reach, and the underlying data is already on disk (no new generation).

**Value beyond what already exists**: real. H3 (`analysis/H3_INTERPRETATION.md`,
just completed) already shows every model's own tier gradient via simple
per-model correlations — a mixed model would add: (i) a single pooled
tier-effect estimate that properly accounts for between-model variance
(unlike H3's pooled reading, which explicitly carries an unaddressed
between-model confound), (ii) a variance component for how much the tier
effect itself differs across models (a random slope, if fit), which no
current analysis provides, (iii) a single CI on the population-level tier
effect rather than 9 separate per-model tests requiring their own
correction. This is genuinely new information, not a restatement of H3
in fancier language — but it substantially overlaps with H3's territory,
and a reviewer could reasonably ask whether the added machinery is worth
it given H3 already answers "does score decline with tier" convincingly.

**Honest framing this option requires**: RQ3 as literally worded
("static benchmarks... vs the dynamic benchmark") does not get answered —
only the Dynamic-side half of the question does. This must be stated as
plainly as Comparison A's null was (`COMPARISON_A_INTERPRETATION.md`), not
softened.

## Option (c) — declare H4 untestable-by-construction; treat as a discussion finding

**What it would do**: no new analysis at all. Write up, as a discussion-
chapter point, that RQ3's premise (a static benchmark with tier variation
to compare against Dynamic's) does not hold for ULT/PLT, evidenced by the
CC-overlap analysis above, and that this is itself informative about
what a CC-filtered static benchmark can and cannot be used for.

**Cost**: none beyond writing the paragraph — the evidence already exists
in this memo.

**Value**: honest, cheap, and defensible, but delivers no new quantitative
result at all — RQ3 becomes a purely qualitative/discussion point with no
accompanying statistics, which is a weaker showing for a Layer-2
inferential hypothesis than either (a) [rejected above] or (b).

## Recommendation

**Option (b), with its own honesty requirement stated up front as part of
adopting it.** Reasoning:

- Option (a) is not a real fix — the quantified overlap above shows it
  would produce a number that doesn't answer RQ3's question, and reporting
  it without heavy caveats would risk looking like a rescued result rather
  than a genuine test (the same discipline this project has applied
  everywhere else — Comparison A's null, the Mut@K definition
  reconciliation — argues against adopting a technically-computable but
  substantively-uninterpretable option here).
- Option (c) is the safe fallback but leaves RQ3 with no statistical
  content at all, when a real, moderate-cost analysis (b) is available
  that at least delivers the "model as random effect" requirement §3.1
  asks for, on the half of RQ3 (the Dynamic-side tier gradient) that is
  actually testable.
- The overlap with H3 is real but not disqualifying: H3 and a Dynamic-only
  mixed model answer related but distinct questions (marginal per-model
  correlation vs a population-level effect with proper variance
  components), and H4's own spec explicitly asks for the latter.

**If the cost of adding a mixed-model dependency and the reshaping work is
judged not worth it relative to H3's already-strong, unanimous result**,
option (c) is the defensible fallback — but that is a cost/benefit call
for the user and supervisor to make explicitly, not a default this memo
assumes.
