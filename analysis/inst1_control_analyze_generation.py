"""Analysis for the inst1-control investigation addendum. Reads the raw
per-problem generation dump from analysis/inst1_control_generate_epoch30.py
(epoch-30 inst1-adapter, greedy, inst1+inst2+inst3, 150 problems each) and:

  1. For instantiation 1 (seen) only: joins each generated problem back to
     its target in the inst1 training JSONL by (template_id, instance_seed)
     -- not every problem has a target, since inst1's training filter kept
     only exec_ok examples (see analysis/inst1_control_memorization_ceiling.py).
     Reports % token-identical (using the actual model tokenizer -- exact
     token-ID-sequence equality, not string equality) and mean normalised
     character-level edit distance (Levenshtein / max(len_a, len_b)),
     compared on the SAME field the training pipeline itself uses as the
     target: extracted_test_file.strip() (scripts/prepare_finetune_data.py
     line ~103), not the sanitized/scored version.
  2. Paired McNemar (exact, sign-test-based -- robust at n=150 and small
     discordant counts, no scipy/chi-square-approximation dependency) on
     baseline_passed, instantiation 1 (seen) vs instantiation 2 (unseen)
     and vs instantiation 3 (unseen) separately, paired by
     (template_id, instance_seed) -- the same template+instance slot is
     instantiated differently (different concrete values) across inst1/2/3,
     which is exactly the seen-vs-unseen contrast this pairs.

Usage:
    python analysis/inst1_control_analyze_generation.py \\
        --generation-file analysis/derived/inst1_control_epoch30_generation_qwen1_5b.jsonl \\
        --train-file data/finetune/train_qwen1_5b_inst1.jsonl \\
        --tokenizer-id Qwen/Qwen2.5-Coder-1.5B-Instruct \\
        --tokenizer-revision 2e1fd397ee46e1388853d2af2c993145b0f1098a \\
        --out-prefix analysis/derived/inst1_control_epoch30_qwen1_5b
"""
from __future__ import annotations

import argparse
import csv
import json
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def char_edit_distance(a: str, b: str) -> int:
    """Standard Levenshtein distance, O(len(a)*len(b)) DP."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[lb]


def normalized_edit_distance(a: str, b: str) -> float:
    denom = max(len(a), len(b), 1)
    return char_edit_distance(a, b) / denom


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact (sign-test-based) McNemar p-value on the discordant
    pair counts b (seen-pass/unseen-fail) and c (seen-fail/unseen-pass).
    No chi-square/continuity-correction approximation, no scipy dependency
    -- robust for the small discordant counts expected here.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cum = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * cum)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--generation-file", type=Path, required=True)
    parser.add_argument("--train-file", type=Path, required=True)
    parser.add_argument("--tokenizer-id", required=True)
    parser.add_argument("--tokenizer-revision", required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    args = parser.parse_args()

    gen_rows = load_jsonl(args.generation_file)
    train_rows = load_jsonl(args.train_file)
    print(f"generation file: {args.generation_file} ({len(gen_rows)} rows)")
    print(f"train file: {args.train_file} ({len(train_rows)} rows)")

    train_targets = {
        (t["template_id"], t["instance_seed"]): t["messages"][2]["content"].strip()
        for t in train_rows
    }

    # ── part 1: seen (inst1) vs training targets ────────────────────────────
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        args.tokenizer_id, revision=args.tokenizer_revision, local_files_only=True
    )

    seen_rows = [r for r in gen_rows if r["instantiation"] == 1]
    comparison_rows = []
    for r in seen_rows:
        key = (r["template_id"], r["instance_seed"])
        target = train_targets.get(key)
        gen_text = r["extracted_test_file"].strip()
        if target is None:
            comparison_rows.append({**r, "has_target": False, "token_identical": None,
                                     "normalized_edit_distance": None})
            continue
        tok_gen = tokenizer.encode(gen_text)
        tok_target = tokenizer.encode(target)
        identical = tok_gen == tok_target
        ned = normalized_edit_distance(gen_text, target)
        comparison_rows.append({**r, "has_target": True, "token_identical": identical,
                                 "normalized_edit_distance": round(ned, 4)})

    matched = [r for r in comparison_rows if r["has_target"]]
    n_matched = len(matched)
    n_identical = sum(1 for r in matched if r["token_identical"])
    mean_ned = sum(r["normalized_edit_distance"] for r in matched) / n_matched if n_matched else float("nan")

    print(f"\n=== Part 1: seen (inst1) vs training target ===")
    print(f"  matched to a training target: {n_matched}/{len(seen_rows)}")
    print(f"  token-identical: {n_identical}/{n_matched} ({100 * n_identical / n_matched:.1f}%)")
    print(f"  mean normalized edit distance: {mean_ned:.4f}")

    comparison_out = args.out_prefix.parent / f"{args.out_prefix.name}_vs_training_target.csv"
    comparison_out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["template_id", "instance_seed", "tier", "has_target", "token_identical",
                  "normalized_edit_distance", "exec_ok", "baseline_passed"]
    with comparison_out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in comparison_rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    print(f"  wrote {comparison_out}")

    # ── part 2: paired McNemar, seen vs unseen ──────────────────────────────
    # Pairing key: (template_id, instance_seed % 1000). instance_seed is
    # instantiation-prefixed by test_gen.load() -- inst1 uses 1101-1105,
    # inst2 2101-2105, inst3 3101-3105 for the "same" base seeds 101-105 --
    # so the raw instance_seed never matches across instantiations even
    # though it's the same template+base-seed slot instantiated 3 ways.
    # Verified empirically before relying on it: template_id sets are
    # identical across instantiations, and instance_seed % 1000 recovers a
    # common 101-105 base seed in every instantiation.
    by_inst_key: dict[int, dict[tuple, dict]] = {1: {}, 2: {}, 3: {}}
    for r in gen_rows:
        by_inst_key[r["instantiation"]][(r["template_id"], r["instance_seed"] % 1000)] = r

    print(f"\n=== Part 2: paired McNemar (baseline_passed), seen vs unseen ===")
    mcnemar_rows = []
    for unseen_inst in (2, 3):
        common_keys = sorted(set(by_inst_key[1]) & set(by_inst_key[unseen_inst]))
        b = c = both_pass = both_fail = 0  # b: seen pass/unseen fail; c: seen fail/unseen pass
        for key in common_keys:
            seen_pass = by_inst_key[1][key]["baseline_passed"]
            unseen_pass = by_inst_key[unseen_inst][key]["baseline_passed"]
            if seen_pass and not unseen_pass:
                b += 1
            elif not seen_pass and unseen_pass:
                c += 1
            elif seen_pass and unseen_pass:
                both_pass += 1
            else:
                both_fail += 1
        p = mcnemar_exact(b, c)
        print(f"  inst1 vs inst{unseen_inst}: n_paired={len(common_keys)}  "
              f"both_pass={both_pass} both_fail={both_fail} "
              f"seen_only={b} unseen_only={c}  McNemar exact p={p:.4g}")
        mcnemar_rows.append({
            "seen": 1, "unseen": unseen_inst, "n_paired": len(common_keys),
            "both_pass": both_pass, "both_fail": both_fail,
            "seen_pass_unseen_fail": b, "seen_fail_unseen_pass": c,
            "mcnemar_p_exact": round(p, 6),
        })

    mcnemar_out = args.out_prefix.parent / f"{args.out_prefix.name}_mcnemar.csv"
    with mcnemar_out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(mcnemar_rows[0].keys()))
        w.writeheader()
        w.writerows(mcnemar_rows)
    print(f"  wrote {mcnemar_out}")


if __name__ == "__main__":
    main()
