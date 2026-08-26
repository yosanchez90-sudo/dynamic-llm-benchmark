"""Pin the canonical CC-stratified ULT/PLT subsamples: core_400 + qwen_1000.

Writes data/raw/ult_plt/subsample_manifest.json with two nested tags:

  core_400   400-ULT + 400-PLT (excl. ULT overlap), CC-stratified, seed=42.
             The UNIVERSAL paired set: every closed-source model (Claude
             Sonnet/Haiku, Gemini Pro/Flash, GPT-5/-5-mini) AND Qwen's first
             pass all evaluate exactly this set, so per-problem paired
             comparisons (H1 Wilcoxon, RQ4 Kendall tau) are computed over
             identical problems across all 9 models.

  qwen_1000  1000-ULT + 1000-PLT, CC-stratified, seed=42, a STRICT SUPERSET
             of core_400 (verified programmatically below, not assumed) --
             i.e. qwen_1000 = core_400 + 600 additional stratified problems
             per benchmark. Qwen-only; serves the within-L4 CC-gradient
             analysis (H4b), which benefits from more open-source data than
             the closed-source-matched core_400 provides. The `qwen_1000
             minus core_400` extension (600/bench) is DEFERRED behind the
             P4 coverage-fill critical path (see PROVENANCE.md).

Design decisions, and why the brief's "full set for local open-source" is
NOT what's implemented (see PROVENANCE.md for the full writeup):
  (a) every cross-model statistical test is already capped at core_400
      (closed-source models cannot exceed N=400/bench), so full-set Qwen
      data would be inadmissible for the headline cross-model comparisons
      anyway;
  (b) N=400 paired gives SE ~ 0.025 on mutation-score metrics, adequate
      for the expected contamination-inflation deltas;
  (c) local GPU budget is queue-bound (shared a100/a100mig/v100 partitions,
      3-day wall-clock cap per job), and is reserved for the P4 coverage
      critical path first;
  (d) qwen_1000 covers the one analysis (H4b, within-L4 CC gradient) that
      genuinely benefits from more open-source-only data, without paying
      the ~500 GPU-hour full-set cost projected in scripts/estimate_cost.py
      -style analysis (all three Qwen sizes individually exceed the
      project's 12h per-submission approval threshold on the full set).

Containment (core_400 subset-of qwen_1000) is guaranteed BY CONSTRUCTION,
not by relying on incidental RNG-nesting behaviour of repeated
_stratified_sample calls: qwen_1000 is built by force-including every
core_400 record, then CC-stratified-sampling the required extra count from
the remaining pool. The result is asserted (not just constructed) before
anything is written.

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
from src.data.ult_plt import _iter_records, _target_function_node, CC_MIN, _stratified_sample  # noqa: E402

SAMPLE_SEED = 42
BAND_EDGES = [8, 10, 12, 16, 10_000]  # CC>=8 by construction; open-ended top band
BAND_LABELS = ["CC8-9", "CC10-11", "CC12-15", "CC16+"]

TAGS = {"core_400": 400, "qwen_1000": 1000}

MANIFEST_PATH = ROOT / "data" / "raw" / "ult_plt" / "subsample_manifest.json"


def _band(cc: int) -> str:
    for lo, hi, label in zip(BAND_EDGES, BAND_EDGES[1:], BAND_LABELS):
        if lo <= cc < hi:
            return label
    return BAND_LABELS[-1]


def _candidates(benchmark: str) -> list[dict]:
    """Mirrors ult_plt.load()'s internal filtering exactly (CC>=8, PLT excl.
    ULT overlap) so every tag is drawn from the identical pool.
    """
    exclude_overlap = benchmark == "plt"
    ult_ids: set[str] = set()
    if exclude_overlap:
        ult_ids = {r["task_id"] for r in _iter_records("ult")}

    out = []
    for r in _iter_records(benchmark):
        if exclude_overlap and r["task_id"] in ult_ids:
            continue
        fn = _target_function_node(r["code"], r["func_name"])
        if fn is None:
            continue
        cc = compute_cc(fn)
        if cc < CC_MIN:
            continue
        out.append({**r, "_cc": cc})
    return out


def _stratified_with_required(
    records: list[dict], required_ids: set[str], max_n: int, sample_seed: int, n_bands: int = 4
) -> list[dict]:
    """CC-stratified sample of size max_n that is GUARANTEED to contain every
    id in required_ids (by construction: required records are force-included,
    then the remainder is topped up via the existing tested stratified
    sampler on the leftover pool).
    """
    required = [r for r in records if r["task_id"] in required_ids]
    assert len(required) == len(required_ids), (
        "required_ids not fully present in candidate pool — data drift, STOP"
    )
    if max_n <= len(required):
        return required[:max_n]
    remainder_pool = [r for r in records if r["task_id"] not in required_ids]
    extra = _stratified_sample(remainder_pool, max_n - len(required), sample_seed, n_bands)
    return required + extra


def _build_benchmark(benchmark: str) -> dict[str, dict]:
    candidates = _candidates(benchmark)
    prefix = benchmark.upper()

    core = _stratified_sample(candidates, TAGS["core_400"], SAMPLE_SEED)
    core_ids = {r["task_id"] for r in core}

    qwen = _stratified_with_required(candidates, core_ids, TAGS["qwen_1000"], SAMPLE_SEED)
    qwen_ids = {r["task_id"] for r in qwen}

    # Containment: verified, not assumed.
    assert core_ids.issubset(qwen_ids), (
        f"{benchmark}: core_400 is NOT a subset of qwen_1000 — containment "
        "guarantee violated. STOP, do not write manifest."
    )

    def _block(records: list[dict], requested: int) -> dict:
        problems = []
        for r in records:
            problems.append({
                "template_id": f"{prefix}-{r['task_id']}",
                "task_id": r["task_id"],
                "fn_name": r["func_name"],
                "cc": r["_cc"],
                "band": _band(r["_cc"]),
            })
        band_counts = Counter(p["band"] for p in problems)
        return {
            "benchmark": benchmark,
            "n_requested": requested,
            "n_actual": len(problems),
            "sample_seed": SAMPLE_SEED,
            "band_edges_cc": BAND_EDGES[:-1] + ["+"],
            "band_labels": BAND_LABELS,
            "band_counts": {label: band_counts.get(label, 0) for label in BAND_LABELS},
            "problems": problems,
        }

    return {
        "core_400": _block(core, TAGS["core_400"]),
        "qwen_1000": _block(qwen, TAGS["qwen_1000"]),
    }


def main() -> None:
    ult_blocks = _build_benchmark("ult")
    plt_blocks = _build_benchmark("plt")

    # Determinism check: rerun core_400 build and compare id sets.
    ult_core_again = {r["task_id"] for r in _stratified_sample(_candidates("ult"), TAGS["core_400"], SAMPLE_SEED)}
    assert ult_core_again == {p["task_id"] for p in ult_blocks["core_400"]["problems"]}, (
        "ULT core_400 is not deterministic under a fixed seed — STOP."
    )

    for tag in TAGS:
        overlap = ({p["task_id"] for p in ult_blocks[tag]["problems"]}
                   & {p["task_id"] for p in plt_blocks[tag]["problems"]})
        assert not overlap, f"{tag}: ULT/PLT subsamples must not share task_ids, found {overlap}"

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/generate_ult_plt_subsample.py",
        "purpose": (
            "Nested canonical subsamples. core_400: universal fixed set for "
            "EVERY model (closed-source + Qwen first pass) -- all cross-model "
            "paired comparisons (H1 Wilcoxon, RQ4 Kendall tau) are restricted "
            "to this set. qwen_1000: Qwen-only CC-stratified superset of "
            "core_400 (containment verified programmatically, see this "
            "script's assertions) for the within-L4 CC-gradient analysis "
            "(H4b); the qwen_1000-minus-core_400 extension is deferred behind "
            "the P4 coverage-fill critical path. See PROVENANCE.md for full "
            "rationale."
        ),
        "cc_recomputed_note": (
            "All `cc` values are this project's own AST-based compute_cc() on "
            "the target function only, NOT the vendored ULT/PLT "
            "cyclomatic_complexity field (see PROVENANCE.md)."
        ),
        "core_400": {"ult": ult_blocks["core_400"], "plt": plt_blocks["core_400"]},
        "qwen_1000": {"ult": ult_blocks["qwen_1000"], "plt": plt_blocks["qwen_1000"]},
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))

    print(f"Wrote {MANIFEST_PATH}\n")
    for tag in TAGS:
        for benchmark, blocks in (("ULT", ult_blocks), ("PLT", plt_blocks)):
            b = blocks[tag]
            print(f"{tag} / {benchmark}: n={b['n_actual']} (requested {b['n_requested']}), seed={b['sample_seed']}")
            for label in BAND_LABELS:
                print(f"  {label:<10} {b['band_counts'][label]}")
        print()

    for benchmark in ("ult", "plt"):
        blocks = ult_blocks if benchmark == "ult" else plt_blocks
        core_ids = {p["task_id"] for p in blocks["core_400"]["problems"]}
        qwen_ids = {p["task_id"] for p in blocks["qwen_1000"]["problems"]}
        print(f"{benchmark.upper()}: core_400 subset-of qwen_1000 = {core_ids.issubset(qwen_ids)} "
              f"({len(core_ids)} subset of {len(qwen_ids)})")


if __name__ == "__main__":
    main()
