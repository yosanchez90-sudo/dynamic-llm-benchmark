"""Pin the canonical CC-stratified ULT/PLT subsample for closed-source models.

Writes data/raw/ult_plt/subsample_manifest.json: one fixed list of task_ids
per benchmark (ULT, PLT-excl-ULT-overlap), used by EVERY closed-source model
(Claude Sonnet/Haiku, Gemini Pro/Flash, GPT-5/-5-mini) so that per-problem
paired comparisons (H1 Wilcoxon, RQ4 Kendall tau) are computed over identical
problem sets across models. Local Qwen (1.5B/7B/32B) uses the full effective
set instead (see PROJECT_BRIEF.md Sec 9) and is not affected by this manifest.

Design (see PROJECT_BRIEF.md Sec 9 for the "300-500, CC-stratified" spec):
  - N=400 per benchmark: midpoint of the [300,500] spec range, chosen so it
    divides evenly across 4 CC-quartile bands (100/band target).
  - Reuses src/data/ult_plt.py's existing, tested `load(max_n=..., sample_seed=...)`
    path (quantile CC-banding via `_stratified_sample`) rather than
    reimplementing stratification — this is the same code the eval harness
    will call, so the manifest and the actual eval input are guaranteed
    consistent.
  - seed=42: this project's standing convention for reproducibility seeds
    (see e.g. configs/*.yaml `decoding.seed: 42`).
  - "Matched CC" strata: verified empirically (not assumed) that ULT and PLT
    (both CC-filtered to this project's CC_MIN=8, PLT excl. ULT overlap)
    have near-identical quartile CC edges post-filter ([8,10,12,16,max] for
    both) -- see the printed band table below for the realized counts. This
    is what makes ULT-subsample vs PLT-subsample a fair "matched CC"
    comparison for Comparison B, without needing custom shared-bin-edge code.
  - Determinism check: load() is called twice per benchmark and the
    resulting template_id sets are asserted identical before writing anything.

Note on the vendored `cyclomatic_complexity` field: ULT/PLT's raw JSON
carries the paper authors' own CC number, which this project does NOT use
(see data/raw/ult_plt/PROVENANCE.md and
tests/test_ult_plt_loader.py::test_cc_lookup_matches_loaded_tier_filter) --
CC is always recomputed here via this project's own AST-based compute_cc()
on the target function only. All CC values in this script/manifest are that
recomputed value, not the vendored field.

Usage:
    python scripts/generate_ult_plt_subsample.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "template_corpus" / "templates" / "_smoke"))

from validate_cc import compute_cc  # noqa: E402
from src.data import ult_plt  # noqa: E402

N_PER_BENCHMARK = 400
SAMPLE_SEED = 42
N_BANDS = 4
BAND_EDGES = [8, 10, 12, 16, 10_000]  # CC>=8 by construction; open-ended top band
BAND_LABELS = ["CC8-9", "CC10-11", "CC12-15", "CC16+"]

MANIFEST_PATH = ROOT / "data" / "raw" / "ult_plt" / "subsample_manifest.json"


def _band(cc: int) -> str:
    for lo, hi, label in zip(BAND_EDGES, BAND_EDGES[1:], BAND_LABELS):
        if lo <= cc < hi:
            return label
    return BAND_LABELS[-1]


def _build(benchmark: str) -> dict:
    # Determinism check: two independent calls must agree exactly.
    first = ult_plt.load(benchmark, max_n=N_PER_BENCHMARK, sample_seed=SAMPLE_SEED)
    second = ult_plt.load(benchmark, max_n=N_PER_BENCHMARK, sample_seed=SAMPLE_SEED)
    ids_first = [p.template_id for p in first]
    ids_second = [p.template_id for p in second]
    assert ids_first == ids_second, (
        f"{benchmark}: load() is not deterministic under a fixed seed — "
        "cannot pin a canonical subsample. STOP."
    )

    problems = []
    for p in first:
        tree_src = p.source
        fn = next(
            (n for n in __import__("ast").parse(tree_src).body
             if isinstance(n, __import__("ast").FunctionDef) and n.name == p.fn_name),
            None,
        )
        cc = compute_cc(fn) if fn is not None else None
        problems.append({
            "template_id": p.template_id,
            "task_id": p.template_id.split("-", 1)[1],
            "fn_name": p.fn_name,
            "cc": cc,
            "band": _band(cc) if cc is not None else None,
        })

    band_counts = Counter(pr["band"] for pr in problems)
    return {
        "benchmark": benchmark,
        "n_requested": N_PER_BENCHMARK,
        "n_actual": len(problems),
        "sample_seed": SAMPLE_SEED,
        "band_edges_cc": BAND_EDGES[:-1] + ["+"],
        "band_labels": BAND_LABELS,
        "band_counts": {label: band_counts.get(label, 0) for label in BAND_LABELS},
        "problems": problems,
    }


def main() -> None:
    ult_block = _build("ult")
    plt_block = _build("plt")  # exclude_ult_overlap=True is load()'s default

    overlap = {p["task_id"] for p in ult_block["problems"]} & {
        p["task_id"] for p in plt_block["problems"]
    }
    assert not overlap, f"ULT/PLT subsamples must not share task_ids, found {overlap}"

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/generate_ult_plt_subsample.py",
        "purpose": (
            "Canonical CC-stratified evaluation subsample for closed-source "
            "models (Claude Sonnet/Haiku, Gemini Pro/Flash, GPT-5/-5-mini). "
            "The SAME subsample must be used for every closed-source model "
            "so per-problem paired comparisons (H1 Wilcoxon, RQ4 Kendall tau) "
            "are computed over identical problem sets. Local Qwen "
            "(1.5B/7B/32B) uses the full effective set instead, per "
            "PROJECT_BRIEF.md Sec 9, and does not consume this manifest."
        ),
        "cc_recomputed_note": (
            "All `cc` values are this project's own AST-based compute_cc() on "
            "the target function only, NOT the vendored ULT/PLT "
            "cyclomatic_complexity field (see PROVENANCE.md)."
        ),
        "ult": ult_block,
        "plt": plt_block,
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))

    print(f"Wrote {MANIFEST_PATH}")
    for block in (ult_block, plt_block):
        print(f"\n{block['benchmark'].upper()}: n={block['n_actual']} "
              f"(requested {block['n_requested']}), seed={block['sample_seed']}")
        for label in BAND_LABELS:
            print(f"  {label:<10} {block['band_counts'][label]}")


if __name__ == "__main__":
    main()
