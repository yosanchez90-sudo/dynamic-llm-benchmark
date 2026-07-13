"""ULT / PLT dataset loader — the static benchmarks for Comparison A
(Dynamic vs ULT) and Comparison B (ULT vs PLT).

See data/raw/ult_plt/PROVENANCE.md for source, licensing, and the full
reasoning behind every decision baked into this module. Summary:

  - ULT (UnLeakedTestBench) is CC>=10 exclusively — there are zero L1/L2/L3
    -equivalent problems in it. Every problem this loader produces is tagged
    tier="L4" regardless of benchmark, matching this project's own CC>=8
    band. PLT records with CC<8 are dropped so ULT and PLT stay comparable
    on the same tier.
  - ULT's task_ids are a 100% subset of PLT's. load(benchmark="plt") drops
    that overlap by default so Comparison B isn't circular.
  - Ground-truth tests (`tests` / `test_input` / `test_list` fields in the
    raw data) are never read. Exec@K/Cov/Mut@K only need `code` (the
    reference implementation) plus this project's own mutation engine,
    exactly like the Dynamic benchmark — no external reference suite needed.
  - `code` blobs sometimes include helper classes/functions the target
    function depends on; mutation is scoped to just the named function via
    generate_mutants(..., scope_fn_name=...) so helper code is never mutated
    (see the mutator.py scope_fn_name parameter).
"""
from __future__ import annotations

import ast
import json
import random
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _ROOT / "data" / "raw" / "ult_plt"

sys.path.insert(0, str(_ROOT / "template_corpus" / "templates" / "_smoke"))
from validate_cc import compute_cc  # noqa: E402  (AST-based CC, same rule as template validation)

from src.data.test_gen import _build_messages  # noqa: E402  (identical prompting to Dynamic)
from src.eval.mutation_adapter import generate_mutants  # noqa: E402
from src.eval.test_gen_problem import TestGenProblem  # noqa: E402

CC_MIN = 8   # this project's own L4 threshold — see PROVENANCE.md
TIER = "L4"


def _target_function_node(code: str, func_name: str) -> ast.FunctionDef | None:
    tree = ast.parse(code)
    return next((n for n in tree.body
                 if isinstance(n, ast.FunctionDef) and n.name == func_name), None)


def _raw_path(benchmark: str) -> Path:
    return _DATA_DIR / f"{benchmark.upper()}.jsonl"


def _iter_records(benchmark: str):
    path = _raw_path(benchmark)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — see data/raw/ult_plt/PROVENANCE.md for how to vendor it."
        )
    yield from json.loads(path.read_text())


def cc_lookup(benchmark: str) -> dict[str, int]:
    """{template_id: cyclomatic_complexity} for every problem load() could
    produce for `benchmark`, computed on the target function only (not the
    whole code blob) — matches how tier assignment/CC filtering work. Use
    this to sub-stratify ULT/PLT by CC in analysis code, the same way
    Dynamic sources are reconstructed on demand rather than stored on the
    tidy record (see scripts/results_to_excel.py's _build_source_map).
    """
    prefix = benchmark.upper()
    out: dict[str, int] = {}
    for r in _iter_records(benchmark):
        fn = _target_function_node(r["code"], r["func_name"])
        if fn is None:
            continue
        out[f"{prefix}-{r['task_id']}"] = compute_cc(fn)
    return out


def _stratified_sample(records: list[dict], max_n: int, sample_seed: int, n_bands: int = 4) -> list[dict]:
    """CC-stratified sample: quantile-bin by `_cc`, draw evenly from each
    band, cap at max_n. Matches PROJECT_BRIEF.md §9's "CC-stratified 300-500
    subsample for closed-source APIs" design. Approximate, not exact — the
    result may be a few records short of max_n on very small pools.
    """
    ccs = pd.Series([r["_cc"] for r in records])
    n_bands = max(1, min(n_bands, ccs.nunique()))
    bands = pd.qcut(ccs, q=n_bands, duplicates="drop")

    rng = random.Random(sample_seed)
    per_band = -(-max_n // bands.nunique())  # ceiling division
    picked: list[dict] = []
    for band_value in bands.unique():
        idx = [i for i, b in enumerate(bands) if b == band_value]
        rng.shuffle(idx)
        picked.extend(records[i] for i in idx[:per_band])
    rng.shuffle(picked)
    return picked[:max_n]


def load(
    benchmark: str,
    prompting_condition: str = "zero_shot",
    max_n: int | None = None,
    sample_seed: int = 0,
    exclude_ult_overlap: bool = True,
    task_ids: set[str] | None = None,
) -> list[TestGenProblem]:
    """Load ULT or PLT as a flat list of TestGenProblem, ready for the same
    model harness / scorer as the Dynamic benchmark.

    benchmark: "ult" or "plt".
    max_n: if given, draw a CC-stratified subsample of roughly this size
        (see PROJECT_BRIEF.md §9 — "300-500 subsample for closed-source
        APIs, full set for local open-source"). None loads everything that
        passes the CC / overlap filters. Ignored if `task_ids` is given.
    exclude_ult_overlap: for benchmark="plt", drop task_ids that also
        appear in ULT (ULT's ids are a 100% subset of PLT's) so Comparison B
        isn't circular. Ignored for benchmark="ult".
    task_ids: if given, restrict to exactly these task_ids (post CC/overlap
        filtering) instead of drawing a fresh sample — this is how a pinned
        manifest (e.g. data/raw/ult_plt/subsample_manifest.json, see
        load_manifest_subset()) is honoured exactly, rather than re-derived
        via max_n/sample_seed each run. Raises if any requested id is not in
        the filtered candidate pool (signals data drift — don't guess).
    """
    benchmark = benchmark.lower()
    if benchmark not in ("ult", "plt"):
        raise ValueError(f"benchmark must be 'ult' or 'plt', got {benchmark!r}")

    ult_task_ids: set[str] = set()
    if benchmark == "plt" and exclude_ult_overlap:
        ult_task_ids = {r["task_id"] for r in _iter_records("ult")}

    candidates: list[dict] = []
    for r in _iter_records(benchmark):
        if benchmark == "plt" and r["task_id"] in ult_task_ids:
            continue
        fn = _target_function_node(r["code"], r["func_name"])
        if fn is None:
            continue
        cc = compute_cc(fn)
        if cc < CC_MIN:
            continue
        candidates.append({**r, "_cc": cc})

    if task_ids is not None:
        pool_ids = {c["task_id"] for c in candidates}
        missing = task_ids - pool_ids
        if missing:
            raise ValueError(
                f"{benchmark}: {len(missing)} pinned task_id(s) not found in the "
                f"current CC/overlap-filtered candidate pool (data drift?): "
                f"{sorted(missing)[:10]}"
            )
        candidates = [c for c in candidates if c["task_id"] in task_ids]
    elif max_n is not None and max_n < len(candidates):
        candidates = _stratified_sample(candidates, max_n, sample_seed)

    prefix = benchmark.upper()
    problems: list[TestGenProblem] = []
    for r in candidates:
        source = r["code"]
        problems.append(TestGenProblem(
            template_id=f"{prefix}-{r['task_id']}",
            tier=TIER,
            instance_seed=int(r["task_id"]),
            instantiation_id="1",
            benchmark=benchmark,
            prompting_condition=prompting_condition,
            fn_name=r["func_name"],
            source=source,
            docstring=r["prompt"],
            mutants=generate_mutants(source, scope_fn_name=r["func_name"]),
            oracle=None,
            messages=_build_messages(source, prompting_condition),
        ))
    return problems


_MANIFEST_PATH = _DATA_DIR / "subsample_manifest.json"


def load_manifest_subset(
    benchmark: str,
    tag: str,
    prompting_condition: str = "zero_shot",
    manifest_path: Path | None = None,
) -> list[TestGenProblem]:
    """Load exactly the pinned task_ids for `tag` (e.g. "core_400", "qwen_1000")
    from data/raw/ult_plt/subsample_manifest.json — the canonical, fixed
    subsample every closed-source model (and Qwen's core_400 run) must share
    so per-problem paired comparisons are computed over identical problem
    sets. See scripts/generate_ult_plt_subsample.py for how the manifest is
    built and PROVENANCE.md for the nested core_400/qwen_1000 rationale.
    """
    path = manifest_path or _MANIFEST_PATH
    manifest = json.loads(path.read_text())
    block = manifest[tag][benchmark.lower()]
    ids = {p["task_id"] for p in block["problems"]}
    return load(benchmark, prompting_condition=prompting_condition, task_ids=ids)
