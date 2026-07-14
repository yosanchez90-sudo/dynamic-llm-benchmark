# Equivalent-mutant hand-inspection pack

## Purpose

Some SAC-operator mutants are semantically equivalent to the original function
under every input the template's parameter domain permits -- no test suite,
however good, can ever kill them. Counting these against a model's mutation
score unfairly penalises tests that are doing everything right. Formal
equivalent-mutant detection is out of scope for this project (PROJECT_BRIEF.md
Sec. 4); instead we hand-inspect a stratified representative sample and use
the observed rate to correct the headline score (PROJECT_BRIEF.md Sec. 5.5).

## Sampling method

- **Pool**: every mutant `generate_mutants()` produces, across all 15
  templates x 5 canonical instantiation seeds (101, 102, 103, 104, 105) per tier -- the same
  seeds diversity_v2.py uses for its within-tier diversity check.
- **Stratification**: 30 seats per tier apportioned across the 7 SAC operators
  by largest-remainder (Hamilton) apportionment, proportional to each
  operator's share of that tier's candidate pool. This makes the sample's
  operator mix mirror the corpus's actual operator mix (e.g. CR/AOR are
  naturally more common than SDL/RSM at low tiers) rather than forcing an
  artificial uniform 30/7 split.
- **Draw**: `random.Random(20260714)`, fixed seed -- rerunning
  `scripts/build_equiv_mutant_sample.py` reproduces this exact pack.
- **Total**: 30 x 4 tiers = 120 mutants.

Per-tier pool size and operator apportionment actually used:

- **L1**: pool=572 (AOR=190, CR=307, RSM=75) -> sample={'AOR': 10, 'CR': 16, 'RSM': 4}
- **L2**: pool=1005 (AOR=40, BM=170, CR=350, LOR=15, ROR=270, RSM=160) -> sample={'AOR': 1, 'BM': 5, 'CR': 11, 'LOR': 0, 'ROR': 8, 'RSM': 5}
- **L3**: pool=1585 (AOR=45, BM=270, CR=485, LOR=25, ROR=415, RSM=105, SDL=240) -> sample={'AOR': 1, 'BM': 5, 'CR': 9, 'LOR': 0, 'ROR': 8, 'RSM': 2, 'SDL': 5}
- **L4**: pool=2670 (AOR=75, BM=510, CR=620, LOR=80, ROR=780, RSM=135, SDL=470) -> sample={'AOR': 1, 'BM': 6, 'CR': 7, 'LOR': 1, 'ROR': 9, 'RSM': 1, 'SDL': 5}

## How to fill in `inspection_sheet.xlsx`

One row per sampled mutant. Columns:

- `template_id`, `instance_seed`, `operator` -- identify the exact source
  instance and which SAC operator produced the mutant.
- `unified_diff` -- the mutant against the original instance source
  (`-` = removed, `+` = added), enough context to judge the change in place.
- `verdict` -- pick one from the dropdown:
  - **equivalent** -- the mutant computes the same function as the original
    on every input in the template's declared parameter domain; no possible
    test could distinguish them.
  - **non-equivalent** -- some input in the domain would reveal the
    difference (an ordinary, killable mutant).
  - **unsure** -- genuinely ambiguous, or would need more investigation than
    the inspection budget allows. Excluded from the equivalent-rate estimate
    by default (see below); leave a note on why.
- `notes` -- free text; especially useful for `unsure` rows.

`sample_manifest.json` has the same 120 rows machine-readable (including full
`original_source` / `mutant_source`, not just the diff) if you want to open a
mutant in an editor or paste it somewhere else to reason about it.

## Downstream: validated score

Once the sheet is filled, `scripts/compute_validated_score.py` reads the
`verdict` column, estimates each tier's equivalent-mutant rate (Wilson 95% CI
on `equivalent / (equivalent + non-equivalent)`; `unsure` rows are excluded
from that denominator by default -- pass `--unsure-policy` to change this),
and applies it to every scored problem in that tier:

```
Mut@K_validated = mutants_killed / (mutants_total * (1 - equivalent_rate_tier))
```

aggregated with a bootstrap 95% CI that resamples both the evaluated problems
and the 30-mutant inspection sample, so the reported interval reflects
uncertainty from both sources. Output: `analysis/equiv_mutants/validated_scores.csv`.
