"""Build the stratified equivalent-mutant hand-inspection pack: 30 mutants per
tier (120 total), sampled from every mutant candidate_mutants() produces
across all 15 templates x 5 canonical instantiation seeds (101-105) per tier.

Stratification: largest-remainder (Hamilton) apportionment of the 30 seats
across the 7 SAC operators, proportional to each operator's share of that
tier's candidate pool. So the sample's operator mix mirrors the corpus's
actual operator mix, not an artificial uniform split. Draw within each
operator stratum is a fixed-seed random.sample (SAMPLE_SEED below), so the
pack is exactly reproducible.

Writes:
  analysis/equiv_mutants/inspection_sheet.xlsx  - one row per sampled mutant,
                                                   verdict column left blank
                                                   for hand inspection
  analysis/equiv_mutants/sample_manifest.json   - same rows, machine-readable
  analysis/equiv_mutants/README.md              - inspection protocol
"""
import difflib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TROOT = ROOT / "template_corpus" / "templates"
sys.path.insert(0, str(TROOT))
sys.path.insert(0, str(TROOT / "_smoke"))

from engine import instantiate, load_template  # noqa: E402
from mutator import generate_mutants  # noqa: E402

OUT = ROOT / "analysis" / "equiv_mutants"
TIERS = ["L1", "L2", "L3", "L4"]
SEEDS = [101, 102, 103, 104, 105]  # same canonical seeds as diversity_v2.py
N_PER_TIER = 30
SAMPLE_SEED = 20260714


def build_pool(tier: str) -> list[dict]:
    pool = []
    for path in sorted((TROOT / tier).glob("*.py")):
        t = load_template(path)
        for seed in SEEDS:
            inst = instantiate(t, seed)
            if not inst.get("source"):
                continue
            for m in generate_mutants(inst["source"]):
                pool.append({
                    "tier": tier,
                    "template_id": t.template_id,
                    "instance_seed": seed,
                    "operator": m.operator,
                    "original_source": inst["source"],
                    "mutant_source": m.source,
                })
    return pool


def apportion(counts_by_op: dict, total: int) -> dict:
    """Largest-remainder apportionment of `total` seats across operators,
    proportional to counts_by_op. Never allocates more than an operator's
    own pool size."""
    pool_total = sum(counts_by_op.values())
    raw = {op: (n / pool_total) * total for op, n in counts_by_op.items()}
    seats = {op: int(v) for op, v in raw.items()}
    remainder = total - sum(seats.values())
    fracs = sorted(raw.items(), key=lambda kv: kv[1] - seats[kv[0]], reverse=True)
    for op, _ in fracs:
        if remainder <= 0:
            break
        if seats[op] < counts_by_op[op]:
            seats[op] += 1
            remainder -= 1
    for op in seats:
        seats[op] = min(seats[op], counts_by_op[op])
    return seats


def sample_tier(tier: str, rng: random.Random) -> tuple[list[dict], dict, dict]:
    pool = build_pool(tier)
    by_op: dict[str, list[dict]] = {}
    for m in pool:
        by_op.setdefault(m["operator"], []).append(m)
    counts = {op: len(v) for op, v in by_op.items()}
    seats = apportion(counts, N_PER_TIER)

    sampled = []
    for op, k in seats.items():
        sampled.extend(rng.sample(by_op[op], k))

    if len(sampled) < N_PER_TIER:
        # Apportionment capped by a small operator pool; top up at random
        # from whatever's left (should not happen at this corpus's scale,
        # but keep the pack at exactly N_PER_TIER regardless).
        chosen_ids = {id(m) for m in sampled}
        remaining = [m for m in pool if id(m) not in chosen_ids]
        sampled.extend(rng.sample(remaining, min(N_PER_TIER - len(sampled), len(remaining))))

    rng.shuffle(sampled)
    return sampled, counts, seats


def unified_diff(m: dict) -> str:
    a = m["original_source"].splitlines(keepends=True)
    b = m["mutant_source"].splitlines(keepends=True)
    diff = difflib.unified_diff(
        a, b,
        fromfile=f"{m['template_id']}_seed{m['instance_seed']}_original.py",
        tofile=f"{m['template_id']}_seed{m['instance_seed']}_{m['operator']}_mutant.py",
        lineterm="",
    )
    return "\n".join(diff)


def write_xlsx(rows: list[dict], path: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "Inspection"

    headers = ["row_id", "tier", "template_id", "instance_seed", "operator",
               "unified_diff", "verdict", "notes"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for r in rows:
        ws.append([r["row_id"], r["tier"], r["template_id"], r["instance_seed"],
                   r["operator"], r["diff"], "", ""])

    widths = {"row_id": 8, "tier": 6, "template_id": 20, "instance_seed": 12,
              "operator": 10, "unified_diff": 70, "verdict": 16, "notes": 40}
    for col_cells in ws.iter_cols(min_row=1, max_row=1):
        header = col_cells[0].value
        letter = col_cells[0].column_letter
        ws.column_dimensions[letter].width = widths.get(header, 14)

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"

    dv = DataValidation(type="list", formula1='"equivalent,non-equivalent,unsure"',
                         allow_blank=True, showDropDown=False)
    dv.error = "Choose one of: equivalent, non-equivalent, unsure"
    dv.prompt = "equivalent / non-equivalent / unsure"
    ws.add_data_validation(dv)
    dv.add(f"G2:G{ws.max_row}")

    wb.save(path)


README_TEMPLATE = """# Equivalent-mutant hand-inspection pack

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
  templates x 5 canonical instantiation seeds ({seeds}) per tier -- the same
  seeds diversity_v2.py uses for its within-tier diversity check.
- **Stratification**: 30 seats per tier apportioned across the 7 SAC operators
  by largest-remainder (Hamilton) apportionment, proportional to each
  operator's share of that tier's candidate pool. This makes the sample's
  operator mix mirror the corpus's actual operator mix (e.g. CR/AOR are
  naturally more common than SDL/RSM at low tiers) rather than forcing an
  artificial uniform 30/7 split.
- **Draw**: `random.Random({sample_seed})`, fixed seed -- rerunning
  `scripts/build_equiv_mutant_sample.py` reproduces this exact pack.
- **Total**: 30 x 4 tiers = 120 mutants.

Per-tier pool size and operator apportionment actually used:

{apportionment_table}

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
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SAMPLE_SEED)

    all_rows = []
    manifest_rows = []
    apportion_lines = []
    row_id = 1
    for tier in TIERS:
        sampled, counts, seats = sample_tier(tier, rng)
        assert len(sampled) == N_PER_TIER, f"{tier}: got {len(sampled)}, want {N_PER_TIER}"
        apportion_lines.append(f"- **{tier}**: pool={sum(counts.values())} "
                                f"({', '.join(f'{op}={n}' for op, n in sorted(counts.items()))}) "
                                f"-> sample={dict(sorted(seats.items()))}")
        for m in sampled:
            diff = unified_diff(m)
            all_rows.append({"row_id": row_id, "diff": diff, **m})
            manifest_rows.append({
                "row_id": row_id, "tier": m["tier"], "template_id": m["template_id"],
                "instance_seed": m["instance_seed"], "operator": m["operator"],
                "original_source": m["original_source"], "mutant_source": m["mutant_source"],
                "verdict": None, "notes": None,
            })
            row_id += 1

    write_xlsx(all_rows, OUT / "inspection_sheet.xlsx")
    (OUT / "sample_manifest.json").write_text(json.dumps(manifest_rows, indent=2))
    (OUT / "README.md").write_text(README_TEMPLATE.format(
        seeds=", ".join(str(s) for s in SEEDS),
        sample_seed=SAMPLE_SEED,
        apportionment_table="\n".join(apportion_lines),
    ))

    print(f"Wrote {len(all_rows)} rows across {len(TIERS)} tiers to {OUT}")
    for tier in TIERS:
        n = sum(1 for r in all_rows if r["tier"] == tier)
        print(f"  {tier}: {n}")


if __name__ == "__main__":
    main()
