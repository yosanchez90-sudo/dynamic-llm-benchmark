"""Compute StableMut@K and pairwise Kendall tau (RQ4.1) from dynamic-
benchmark result JSONL files.

Usage (from the dissertation root):
    python scripts/analyze_stability.py
    python scripts/analyze_stability.py --results-dir data/results/dynamic --out analysis/stability
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from coverage_matrix import CANONICAL_MODELS  # noqa: E402
from src.Analysis.loader import load_records  # noqa: E402
from src.Analysis.multiple_comparisons import holm_bonferroni  # noqa: E402
from src.Analysis.provenance import stamp_block  # noqa: E402
from src.Analysis.stability import (  # noqa: E402
    mean_pairwise_tau, mean_pairwise_tau_scoped, pairwise_kendall_tau, stable_mut_at_k,
)

# N=4 scope (PROJECT_BRIEF.md Sec 11): the project's headline reliability
# figure is pairs among instantiations 1-4 only, excluding instantiation 5
# (deferred K=5 sensitivity sweep, only ever partially run). Shared with
# analyze_rq5_diagnostics.py's attenuation correction via
# mean_pairwise_tau_scoped() -- do not hard-code this figure elsewhere.
N4_INSTANTIATIONS = {"1", "2", "3", "4"}
STABILITY_MD = ROOT / "analysis" / "STABILITY.md"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default="data/results/dynamic", type=Path)
    parser.add_argument("--out", default="analysis/stability", type=Path,
                        help="Output path prefix for the written CSVs")
    parser.add_argument("--min-instantiations", type=int, default=2,
                        help="Only report models with at least this many "
                             "scorable instantiations (default 2)")
    args = parser.parse_args()

    df = load_records(args.results_dir)
    if df.empty:
        print(f"No records found in {args.results_dir}")
        sys.exit(1)

    # Restrict to the 9 canonical models -- fine-tuned adapter variants
    # (Comparison C / supplementary-study artifacts) and any future
    # cross-family RQ5 model are a different model identity and must never
    # silently enter the reliability figure. Confirmed 2026-07-28: without
    # this filter, the two LoRA adapter labels (Qwen 1.5B/7B fine-tunes) fed
    # the instantiation-1-3 pairwise Kendall tau once their POST Dynamic eval
    # landed, moving the N=4 mean from 0.675 to 0.701 with no scope decision
    # behind it -- same bug class as comparison_b_paired.csv's spurious 8th
    # model (scripts/build_comparison_tables.py).
    excluded = sorted(set(df["model_label"].unique()) - set(CANONICAL_MODELS))
    df = df[df["model_label"].isin(CANONICAL_MODELS)]
    if excluded:
        print(f"Excluded {len(excluded)} non-canonical model_label(s) "
              f"(fine-tuned adapter / cross-family, not one of the 9 canonical "
              f"models): {excluded}\n")

    print(f"Loaded {len(df)} records from {df['source_file'].nunique()} files "
          f"({df['model_label'].nunique()} model variant(s), "
          f"instantiations={sorted(df['instantiation_id'].unique())}, "
          f"tiers={sorted(df['tier'].unique())})\n")

    stable = stable_mut_at_k(df)
    stable_reportable = stable[stable["n_instantiations"] >= args.min_instantiations]
    print("=== StableMut@K (mean Mut@K across instantiations, SD) ===")
    print(stable_reportable.to_string(index=False))
    if len(stable) > len(stable_reportable):
        dropped = sorted(set(stable["model_label"]) - set(stable_reportable["model_label"]))
        print(f"(omitted {len(dropped)} model(s) with < {args.min_instantiations} "
              f"scorable instantiations: {dropped})")
    print()

    by_tier = stable_mut_at_k(df, extra_group_cols=("tier",))
    by_tier_reportable = by_tier[by_tier["n_instantiations"] >= args.min_instantiations]
    print("=== StableMut@K by tier ===")
    print(by_tier_reportable.to_string(index=False))
    if len(by_tier) > len(by_tier_reportable):
        print(f"(omitted rows with < {args.min_instantiations} scorable instantiations "
              f"— sd_mut_at_k is undefined, not 0, for a single instantiation)")
    print()

    pairwise = pairwise_kendall_tau(df)
    print("=== Pairwise Kendall tau between instantiation rankings (model-level Mut@K) ===")
    print(pairwise.to_string(index=False))
    mean_tau_n4 = mean_pairwise_tau_scoped(pairwise, N4_INSTANTIATIONS)
    mean_tau_all = mean_pairwise_tau(pairwise)
    n4_label = f"N=4 (pairs among instantiations {sorted(N4_INSTANTIATIONS)}, headline scope)"
    print(f"\n{n4_label} mean pairwise tau: "
          f"{f'{mean_tau_n4:.3f}' if mean_tau_n4 is not None else 'n/a'}")
    print(f"All-pairs mean pairwise tau (incl. instantiation 5): "
          f"{f'{mean_tau_all:.3f}' if mean_tau_all is not None else 'n/a'}")

    # --- Holm-Bonferroni within the RQ4/H5 family (PROJECT_BRIEF.md Sec 3.1) --
    # Two SEPARATE corrections, not one pooled across both: the N=4 set (6
    # pairs among instantiations 1-4, the headline scope) and the all-pairs
    # set (10 pairs, incl. instantiation 5) are two different reported
    # families, not one 16-test family -- correcting them together would
    # conflate a scope decision with a multiple-comparisons one.
    pairwise = pairwise.copy()
    pairwise["p_value_holm"] = holm_bonferroni(pairwise["p_value"].tolist())
    n4_mask = (pairwise["instantiation_a"].isin(N4_INSTANTIATIONS)
               & pairwise["instantiation_b"].isin(N4_INSTANTIATIONS))
    pairwise_n4 = pairwise[n4_mask].copy()
    pairwise_n4["p_value_holm"] = holm_bonferroni(pairwise_n4["p_value"].tolist())
    n4_sig_raw = int((pairwise_n4["p_value"] < 0.05).sum())
    n4_sig_holm = int((pairwise_n4["p_value_holm"] < 0.05).sum())
    all_sig_raw = int((pairwise["p_value"] < 0.05).sum())
    all_sig_holm = int((pairwise["p_value_holm"] < 0.05).sum())
    print(f"\n=== Holm-Bonferroni within RQ4/H5 (two separate families: "
          f"N=4's 6 pairs, all-pairs' 10 pairs) ===")
    print(f"N=4 pairs (raw p, Holm-adjusted p):")
    print(pairwise_n4[["instantiation_a", "instantiation_b", "n_models", "tau",
                       "p_value", "p_value_holm"]].to_string(index=False))
    print(f"N=4: {n4_sig_raw}/{len(pairwise_n4)} significant at raw p<0.05, "
          f"{n4_sig_holm}/{len(pairwise_n4)} at Holm-adjusted p<0.05")
    print(f"\nAll-pairs (raw p, Holm-adjusted p, corrected separately from N=4 above):")
    print(pairwise[["instantiation_a", "instantiation_b", "n_models", "tau",
                    "p_value", "p_value_holm"]].to_string(index=False))
    print(f"All-pairs: {all_sig_raw}/{len(pairwise)} significant at raw p<0.05, "
          f"{all_sig_holm}/{len(pairwise)} at Holm-adjusted p<0.05")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    stable.to_csv(f"{args.out}_stablemut.csv", index=False)
    by_tier.to_csv(f"{args.out}_stablemut_by_tier.csv", index=False)
    pairwise.to_csv(f"{args.out}_kendall.csv", index=False)

    provenance = f"""# Stability (RQ4.1) — raw tables

{stamp_block("scripts/analyze_stability.py")}
**Interpretation lives in `analysis/STABILITY_INTERPRETATION.md`**
(hand-written, not touched by this script) — this file is the regenerable
raw-tables companion; re-run this script freely after new data lands. Any
number quoted from this file elsewhere (e.g. RQ5's disattenuation
correction) is only current as of the commit above, not frozen.

Args: --results-dir {args.results_dir}  --out {args.out}  --min-instantiations {args.min_instantiations}
Canonical models only ({len(CANONICAL_MODELS)}); excluded non-canonical
model_label(s): {excluded if excluded else "(none present)"}

## StableMut@K (mean Mut@K across instantiations, SD)

{stable_reportable.to_string(index=False)}

## StableMut@K by tier

{by_tier_reportable.to_string(index=False)}

## Pairwise Kendall tau between instantiation rankings (model-level Mut@K)

{pairwise.drop(columns=["p_value_holm"]).to_string(index=False)}

{n4_label} mean pairwise tau: {f"{mean_tau_n4:.3f}" if mean_tau_n4 is not None else "n/a"}
All-pairs mean pairwise tau (incl. instantiation 5): {f"{mean_tau_all:.3f}" if mean_tau_all is not None else "n/a"}

## Holm-Bonferroni within RQ4/H5 (PROJECT_BRIEF.md Sec 3.1)

Two SEPARATE corrections (not one 16-test family): the N=4 set (6 pairs
among instantiations 1-4, the headline scope) and the all-pairs set (10
pairs, including instantiation 5) are corrected independently, since they
are two different reported scopes, not one pooled family.

### N=4 set (6 pairs)

{pairwise_n4[["instantiation_a", "instantiation_b", "n_models", "tau", "p_value", "p_value_holm"]].to_string(index=False)}

Significant at raw p<0.05: {n4_sig_raw}/{len(pairwise_n4)}. Significant at Holm-adjusted p<0.05: **{n4_sig_holm}/{len(pairwise_n4)}**.

### All-pairs set (10 pairs, corrected separately from the N=4 set above)

{pairwise[["instantiation_a", "instantiation_b", "n_models", "tau", "p_value", "p_value_holm"]].to_string(index=False)}

Significant at raw p<0.05: {all_sig_raw}/{len(pairwise)}. Significant at Holm-adjusted p<0.05: **{all_sig_holm}/{len(pairwise)}**.
"""
    STABILITY_MD.write_text(provenance)
    print(f"\nWritten: {args.out}_stablemut.csv, {args.out}_stablemut_by_tier.csv, "
          f"{args.out}_kendall.csv, {STABILITY_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
