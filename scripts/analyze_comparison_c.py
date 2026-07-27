"""Comparison C — the canonical 2x3 DiD analysis, per
analysis/COMPARISON_C_ANALYSIS_PLAN.md (pre-registered before this script's
first run). Assembles PRE (base Qwen-1.5B) and POST (ULT-trained LoRA
adapter, 30 epochs) problem-level rows for:

  seen_ult      -- 112 core_400 ULT problems with a verified training pair
  unseen_ult    -- 288 core_400 ULT problems without one
  plt           -- 400 core_400 PLT problems (excl. ULT overlap)
  dynamic_l4    -- Dynamic tier=L4, inst1-3 (CC-matched control; PRE has
                   baseline_pass_rate=0.000 -- floor-limited, see
                   ANALYSIS_PLAN.md's tier amendment)
  dynamic_l1l3  -- Dynamic tiers L1-L3 pooled, inst1-3 (headroom control)

Primary metric: baseline_pass_rate (the plan's recommended primary, since
Mut@K is undefined for nearly all seen-ULT PRE rows). Mut@K reported
alongside with explicit n where defined.

Outputs:
  analysis/comparison_c_did.csv        -- DiD vs both control arms (L4, L1-L3)
  analysis/comparison_c_gradient.csv   -- 4-level (+ L1-L3 arm) raw gain table
  analysis/COMPARISON_C_PROVENANCE.md  -- full writeup with interpretation

Usage: python scripts/analyze_comparison_c.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.Analysis.loader import load_records
from src.Contamination.did import compute_did, did_table

BASE_LABEL = "Qwen__Qwen2.5-Coder-1.5B-Instruct"
POST_LABEL = "Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep"
DYNAMIC_INSTANTIATIONS = {"1", "2", "3"}
SEEN_MANIFEST = ROOT / "data" / "raw" / "ult_plt" / "comparison_c_seen_manifest.json"

PRE_ULT_FILE = "data/results/ult/Qwen__Qwen2.5-Coder-1.5B-Instruct__ult__zero_shot__instcore_400__20260713T123923.jsonl"
POST_ULT_FILE = "data/results/ult/Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep__ult__zero_shot__instcore_400__20260726T142439.jsonl"
PRE_PLT_FILE = "data/results/plt/Qwen__Qwen2.5-Coder-1.5B-Instruct__plt__zero_shot__instcore_400__20260713T123854.jsonl"
POST_PLT_FILE = "data/results/plt/Qwen__Qwen2.5-Coder-1.5B-Instruct__ft_qwen1_5b_lora_ult_30ep__plt__zero_shot__instcore_400__20260726T224725.jsonl"


def _load_jsonl(path: str) -> pd.DataFrame:
    rows = [json.loads(l) for l in Path(ROOT / path).read_text().splitlines() if l.strip()]
    return pd.DataFrame(rows)


def _tag_ult(df: pd.DataFrame, seen_ids: set[str]) -> pd.DataFrame:
    df = df.copy()
    task_id = df["template_id"].str.split("-", n=1).str[1]
    df["benchmark"] = np.where(task_id.isin(seen_ids), "seen_ult", "unseen_ult")
    df["baseline_pass"] = df["baseline_passed"].astype(float)
    return df


def _tag_plt(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["benchmark"] = "plt"
    df["baseline_pass"] = df["baseline_passed"].astype(float)
    return df


def _load_dynamic(model_label: str) -> pd.DataFrame:
    df = load_records("data/results/dynamic", benchmark="dynamic")
    df = df[(df["model_label"] == model_label) &
            (df["instantiation_id"].isin(DYNAMIC_INSTANTIATIONS))].copy()
    df["benchmark"] = np.where(df["tier"] == "L4", "dynamic_l4", "dynamic_l1l3")
    df = df[df["tier"].isin(["L1", "L2", "L3", "L4"])]
    df["baseline_pass"] = df["baseline_passed"].astype(float)
    return df


def _mut_summary(df: pd.DataFrame, label: str) -> dict:
    scored = df.dropna(subset=["mutation_score"])
    return {
        "benchmark": label, "n_total": len(df), "n_mut_defined": len(scored),
        "mut_at_k": float(scored["mutation_score"].mean()) if len(scored) else None,
    }


def main() -> None:
    seen_manifest = json.loads(SEEN_MANIFEST.read_text())
    seen_ids = {p["task_id"] for p in seen_manifest["problems"] if p["seen_in_training"]}
    print(f"Seen ids: {len(seen_ids)}")

    pre_ult = _tag_ult(_load_jsonl(PRE_ULT_FILE), seen_ids)
    post_ult = _tag_ult(_load_jsonl(POST_ULT_FILE), seen_ids)
    pre_plt = _tag_plt(_load_jsonl(PRE_PLT_FILE))
    post_plt = _tag_plt(_load_jsonl(POST_PLT_FILE))
    pre_dyn = _load_dynamic(BASE_LABEL)
    post_dyn = _load_dynamic(POST_LABEL)

    pre = pd.concat([pre_ult, pre_plt, pre_dyn], ignore_index=True)
    post = pd.concat([post_ult, post_plt, post_dyn], ignore_index=True)

    print("\nPRE  rows by benchmark:\n", pre["benchmark"].value_counts())
    print("\nPOST rows by benchmark:\n", post["benchmark"].value_counts())

    # --- Primary DiD: vs Dynamic-L4 (CC-matched, floor-limited) -------------
    results_l4 = compute_did(pre, post, metric="baseline_pass",
                              treatment_benchmarks=("seen_ult", "unseen_ult", "plt"),
                              control_benchmark="dynamic_l4")
    table_l4 = did_table(results_l4)
    table_l4["control"] = "dynamic_l4"

    # --- Robustness DiD: vs Dynamic-L1-L3 pooled (headroom) -----------------
    results_l1l3 = compute_did(pre, post, metric="baseline_pass",
                                treatment_benchmarks=("seen_ult", "unseen_ult", "plt"),
                                control_benchmark="dynamic_l1l3")
    table_l1l3 = did_table(results_l1l3)
    table_l1l3["control"] = "dynamic_l1l3"

    did_out = pd.concat([table_l4, table_l1l3], ignore_index=True)
    did_out.to_csv(ROOT / "analysis" / "comparison_c_did.csv", index=False)
    print("\n=== DiD table ===")
    print(did_out.to_string(index=False))

    # --- 4-level (+L1-L3) gradient: raw gain per arm, no control subtraction
    gradient_rows = []
    for label in ["seen_ult", "unseen_ult", "plt", "dynamic_l4", "dynamic_l1l3"]:
        pre_vals = pre.loc[pre["benchmark"] == label, "baseline_pass"].dropna().to_numpy()
        post_vals = post.loc[post["benchmark"] == label, "baseline_pass"].dropna().to_numpy()
        if len(pre_vals) == 0 or len(post_vals) == 0:
            continue
        rng = np.random.default_rng(0)
        boots = np.empty(2000)
        for i in range(2000):
            s1 = pre_vals[rng.integers(0, len(pre_vals), len(pre_vals))].mean()
            s2 = post_vals[rng.integers(0, len(post_vals), len(post_vals))].mean()
            boots[i] = s2 - s1
        lo, hi = np.percentile(boots, [2.5, 97.5])
        gradient_rows.append({
            "benchmark": label, "n_pre": len(pre_vals), "n_post": len(post_vals),
            "pre_mean": float(pre_vals.mean()), "post_mean": float(post_vals.mean()),
            "gain": float(post_vals.mean() - pre_vals.mean()),
            "gain_ci_lo": float(lo), "gain_ci_hi": float(hi),
        })
    gradient = pd.DataFrame(gradient_rows)
    gradient.to_csv(ROOT / "analysis" / "comparison_c_gradient.csv", index=False)
    print("\n=== Gradient table (raw gain, no control subtraction) ===")
    print(gradient.to_string(index=False))

    # --- Mut@K, secondary, n made explicit -----------------------------------
    mut_rows = []
    for df, side in [(pre, "pre"), (post, "post")]:
        for label in ["seen_ult", "unseen_ult", "plt", "dynamic_l4", "dynamic_l1l3"]:
            sub = df[df["benchmark"] == label]
            if sub.empty:
                continue
            s = _mut_summary(sub, label)
            s["side"] = side
            mut_rows.append(s)
    mut_df = pd.DataFrame(mut_rows)
    mut_df.to_csv(ROOT / "analysis" / "comparison_c_mutk.csv", index=False)
    print("\n=== Mut@K (secondary, n explicit) ===")
    print(mut_df.to_string(index=False))

    provenance = f"""# Comparison C — canonical 2x3 DiD results

Generated: {datetime.now(timezone.utc).isoformat()}
Script: scripts/analyze_comparison_c.py

Per analysis/COMPARISON_C_ANALYSIS_PLAN.md (pre-registered 2026-07-26,
amended same day for Dynamic-arm tier composition, both before this script's
first run). Primary metric: baseline_pass_rate. Mut@K reported alongside,
secondary (see PRE-data-sparsity note in the analysis plan).

## Sources

- PRE ULT/PLT/Dynamic: base Qwen-1.5B, already-landed (2026-07-13/06-09).
- POST ULT: {Path(POST_ULT_FILE).name} (Stage 3a).
- POST PLT: {Path(POST_PLT_FILE).name} (Stage 3b).
- POST Dynamic: 6 files, inst1-3 x {{L1L2,L3L4}} (Stage 3b).
- Seen/unseen split: data/raw/ult_plt/comparison_c_seen_manifest.json (frozen).

## Primary DiD (vs Dynamic-L4, CC-matched control)

{table_l4.to_string(index=False)}

## Robustness DiD (vs Dynamic-L1-L3 pooled, headroom control)

{table_l1l3.to_string(index=False)}

## Four-level gradient (raw gain, no control subtraction)

{gradient.to_string(index=False)}

## Mut@K (secondary; n_mut_defined shows how much of n_total this covers)

{mut_df.to_string(index=False)}
"""
    (ROOT / "analysis" / "COMPARISON_C_PROVENANCE.md").write_text(provenance)
    print(f"\nWritten: analysis/comparison_c_did.csv, analysis/comparison_c_gradient.csv, "
          f"analysis/comparison_c_mutk.csv, analysis/COMPARISON_C_PROVENANCE.md")


if __name__ == "__main__":
    main()
