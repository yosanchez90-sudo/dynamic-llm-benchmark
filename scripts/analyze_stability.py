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

from src.Analysis.loader import load_records  # noqa: E402
from src.Analysis.provenance import stamp_block  # noqa: E402
from src.Analysis.stability import (  # noqa: E402
    mean_pairwise_tau, pairwise_kendall_tau, stable_mut_at_k,
)


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
    mean_tau = mean_pairwise_tau(pairwise)
    print(f"\nMean pairwise tau: {mean_tau:.3f}" if mean_tau is not None else "\nMean pairwise tau: n/a")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    stable.to_csv(f"{args.out}_stablemut.csv", index=False)
    by_tier.to_csv(f"{args.out}_stablemut_by_tier.csv", index=False)
    pairwise.to_csv(f"{args.out}_kendall.csv", index=False)

    provenance = f"""# StableMut@K + pairwise Kendall tau (RQ4.1) — raw tables

{stamp_block("scripts/analyze_stability.py")}
Args: --results-dir {args.results_dir}  --out {args.out}  --min-instantiations {args.min_instantiations}

## StableMut@K (mean Mut@K across instantiations, SD)

{stable_reportable.to_string(index=False)}

## StableMut@K by tier

{by_tier_reportable.to_string(index=False)}

## Pairwise Kendall tau between instantiation rankings (model-level Mut@K)

{pairwise.to_string(index=False)}

Mean pairwise tau: {f"{mean_tau:.3f}" if mean_tau is not None else "n/a"}
"""
    Path(f"{args.out}_PROVENANCE.md").write_text(provenance)
    print(f"\nWritten: {args.out}_stablemut.csv, {args.out}_stablemut_by_tier.csv, "
          f"{args.out}_kendall.csv, {args.out}_PROVENANCE.md")


if __name__ == "__main__":
    main()
