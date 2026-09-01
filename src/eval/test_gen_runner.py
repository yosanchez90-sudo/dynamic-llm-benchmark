"""Test-generation runner: ties model + loader + harness together.

PARALLELISM ARCHITECTURE
------------------------
Level 1 (within a problem): multiprocessing.Pool in test_gen_scorer.py covers
the ~20-30 mutants per problem. Pool size = mutation_workers in config, which
MUST equal --cpus-per-task in the SLURM script, don't oversubscribe.

Level 2 (across problems): SLURM array jobs via scripts/slurm/run_mutation_array.slurm.
The 1,500 problems are split into N shards; each array task handles one shard
and writes its own JSONL. Merging is trivial (glob + concat).

Shard slicing uses stride (problems[shard_id::n_shards]) to balance load across
shards: this interleaves L1 and L2 problems so each shard has a representative
mix instead of one shard getting all L1 (fast) and another all L2 (slower).

INFERENCE VS SCORING SEPARATION (local models)
----------------------------------------------
For open-source models on GPU: run inference in a single GPU job, then score
(CPU-bound) in a separate array job. This separates the GPU bottleneck from the
massively-parallel CPU work and avoids 30 array tasks each claiming a GPU.
The precomputed-mutants design (open question #1) makes this split natural.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.data import test_gen, ult_plt
from src.eval.test_gen_problem import TestGenRecord, compute_model_label
from src.eval.test_gen_scorer import extract_test_file, sanitize_test_file, score_problem
from src.logging_utils import append_jsonl
from src.models.base import GenerationConfig
from src.models.factory import build_model

load_dotenv()


def _tier_signature(config: dict[str, Any]) -> str:
    """Short tag identifying which tiers a Dynamic config targets (e.g.
    "L1L2", "L3L4", "L1L2L3L4"), empty for ULT/PLT, which have no `tiers`
    key and are always tier="L4" by construction (src/data/ult_plt.py).

    Load-bearing for _find_resume_file / output-filename uniqueness: two
    Dynamic configs for the SAME (model, instantiation) but DIFFERENT tier
    sets (e.g. L1L2 vs L3L4, the standard tier-group split for this project)
    used to be indistinguishable to the resume matcher, which keyed only on
    (model, benchmark, instantiation), see the 2026-07-26 race audit
    (CONVENTIONS.md) for the real duplicate/conflicting rows this caused when two
    such configs' jobs had overlapping runtimes.
    """
    tiers = config.get("tiers")
    if not tiers:
        return ""
    return "".join(tiers)


def _find_resume_file(
    out_dir: Path,
    safe_model: str,
    benchmark: str,
    prompting_condition: str,
    instantiation_id: str,
    n_shards: int,
    shard_id: int,
    tier_sig: str = "",
) -> tuple[Path | None, set[tuple[str, int]]]:
    """Return (existing_jsonl_path, already_done_pairs) if a partial run exists.

    "already done" means a (template_id, instance_seed) pair that already has
    a record in the file.  The caller filters these out of the problem list and
    appends to the same file so the completed run is a single contiguous JSONL.

    `tier_sig` (see _tier_signature) narrows the glob to files from a config
    targeting the SAME tier set, required so two Dynamic configs for the
    same (model, instantiation) but different tiers (e.g. L1L2 vs L3L4) never
    match each other's resume file.
    """
    tier_part = f"__tiers{tier_sig}" if tier_sig else ""
    if n_shards > 1:
        pattern = (
            f"{safe_model}__{benchmark}__{prompting_condition}"
            f"__inst{instantiation_id}{tier_part}__shard{shard_id}of{n_shards}_*.jsonl"
        )
    else:
        pattern = (
            f"{safe_model}__{benchmark}__{prompting_condition}"
            f"__inst{instantiation_id}{tier_part}_*.jsonl"
        )

    candidates = sorted(out_dir.glob(pattern))
    if not candidates:
        return None, set()

    # Pick the most recently modified file (in case of multiple partial runs).
    resume_path = max(candidates, key=lambda p: p.stat().st_mtime)
    done: set[tuple[str, int]] = set()
    with resume_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                done.add((rec["template_id"], int(rec["instance_seed"])))
            except Exception:
                pass
    return resume_path, done


def _load_problems(config: dict[str, Any]) -> list:
    """Dispatch to the Dynamic loader or the ULT/PLT static-benchmark loader
    based on config["benchmark"]. ULT/PLT are always tier="L4" (CC>=8) and
    have no instantiations. They take either a pinned manifest subsample
    (production: the same fixed problem set every model shares, see
    data/raw/ult_plt/subsample_manifest.json) or an ad hoc max_n/sample_seed
    draw (dry runs / exploration), never both.

    config["model"]["supports_system_role"] (default True) controls whether
    the system instruction is sent as its own role="system" message or
    folded into the first user turn, for models whose chat_template
    rejects role="system" outright (found 2026-07-28,
    StarCoder2-15B-Instruct-v0.1). Read from the model block, not
    special-cased by model identity anywhere in this function.
    """
    supports_system_role = config["model"].get("supports_system_role", True)
    if config["benchmark"] in ("ult", "plt"):
        if "subsample_tag" in config:
            return ult_plt.load_manifest_subset(
                config["benchmark"], config["subsample_tag"],
                prompting_condition=config["prompting_condition"],
                supports_system_role=supports_system_role,
            )
        return ult_plt.load(
            config["benchmark"],
            prompting_condition=config["prompting_condition"],
            max_n=config.get("max_n"),
            sample_seed=config.get("sample_seed", 0),
            supports_system_role=supports_system_role,
        )
    only_instances = config.get("only_instances")
    return test_gen.load(
        instantiation_id=config["instantiation_id"],
        instantiation_seed=config["instantiation_seed"],
        instance_seeds=tuple(config.get("instance_seeds", (101, 102, 103, 104, 105))),
        tiers=tuple(config.get("tiers", ("L1", "L2"))),
        prompting_condition=config["prompting_condition"],
        only_instances=frozenset((t, s) for t, s in only_instances) if only_instances else None,
        supports_system_role=supports_system_role,
    )


def run_test_gen_experiment(config: dict[str, Any]) -> Path:
    """Run one test-generation config end-to-end. Returns the JSONL path."""
    model = build_model(config["model"])
    gen_cfg = GenerationConfig(**config["generation"])

    K = config.get("K", 1)
    n_workers = config.get("mutation_workers", 4)
    mutant_timeout = config.get("mutant_timeout_seconds", 30)

    problems = _load_problems(config)

    # Level 2 parallelism: slice this task's shard of the problem list.
    # Strided slicing balances the workload. Each shard gets a mix of tiers.
    n_shards = config.get("n_shards", 1)
    shard_id = config.get("shard_id", 0)
    if n_shards > 1:
        problems = problems[shard_id::n_shards]

    # Optional tier prioritisation (added 2026-08-05 for the Gemini Pro daily
    # crawl, generic/reusable beyond that use case): a stable sort so
    # problems whose tier is in config["tier_priority"] come first, without
    # disturbing relative order otherwise. No-op (default) when absent, so
    # every existing config's behaviour is unchanged.
    tier_priority = config.get("tier_priority")
    if tier_priority:
        priority_rank = {t: i for i, t in enumerate(tier_priority)}
        problems = sorted(problems, key=lambda p: priority_rank.get(p.tier, len(tier_priority)))

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    adapter_path = config["model"].get("adapter_path")
    # Fine-tuned models share the same base model id. The adapter tag in
    # safe_model keeps their output files from colliding with baseline runs
    # or each other; compute_model_label() is also what gets stamped into
    # each record's model_label field below, so filename and field agree.
    safe_model = compute_model_label(config["model"]["id"], adapter_path)
    out_dir = Path(config["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resume detection: if a partial run exists for this exact experiment,
    # reuse its file and skip already-completed problems. tier_sig prevents
    # matching a DIFFERENT tier-group's file for the same (model, instantiation),
    # see _tier_signature / the 2026-07-26 race audit.
    tier_sig = _tier_signature(config)
    tier_part = f"__tiers{tier_sig}" if tier_sig else ""
    resume_path, done_pairs = _find_resume_file(
        out_dir, safe_model,
        config["benchmark"], config["prompting_condition"],
        config["instantiation_id"], n_shards, shard_id, tier_sig,
    )

    if resume_path and done_pairs:
        out_path = resume_path
        problems = [p for p in problems
                    if (p.template_id, p.instance_seed) not in done_pairs]
        print(f"Resuming: {out_path.name}")
        print(f"  Skipping {len(done_pairs)} already-completed problems.")
    else:
        if n_shards > 1:
            out_path = out_dir / (
                f"{safe_model}__{config['benchmark']}__"
                f"{config['prompting_condition']}__inst{config['instantiation_id']}{tier_part}__"
                f"shard{shard_id}of{n_shards}__{run_ts}.jsonl"
            )
        else:
            out_path = out_dir / (
                f"{safe_model}__{config['benchmark']}__"
                f"{config['prompting_condition']}__inst{config['instantiation_id']}{tier_part}__{run_ts}.jsonl"
            )

    print(f"Output: {out_path}")
    shard_info = f" (shard {shard_id}/{n_shards})" if n_shards > 1 else ""
    print(f"{len(problems)} problems remaining{shard_info} | K={K} | workers={n_workers}\n")

    # Optional per-run request cap (added 2026-08-05 for the Gemini Pro daily
    # crawl, generic/reusable): stop cleanly after this many NEW requests in
    # THIS call, leaving the rest for a future resumed run. Already-done
    # problems (filtered out above by the resume logic) never count against
    # this. No-op (default) when absent.
    max_requests = config.get("max_requests")
    if max_requests is not None and len(problems) > max_requests:
        print(f"max_requests={max_requests}: capping this run to the first "
              f"{max_requests} of {len(problems)} remaining problems.\n")
        problems = problems[:max_requests]

    total_cost = 0.0
    for i, prob in enumerate(problems, 1):
        t0 = time.monotonic()
        model_out = model.generate(prob.messages, gen_cfg)
        latency = time.monotonic() - t0

        test_file = extract_test_file(model_out.response)
        test_file, repairs = sanitize_test_file(test_file, prob.fn_name)
        result = score_problem(
            fn_source=prob.source,
            fn_name=prob.fn_name,
            test_source=test_file,
            mutants=prob.mutants,
            timeout=mutant_timeout,
            n_workers=n_workers,
        )

        record = TestGenRecord(
            model=model_out.model_id,
            instantiation_id=prob.instantiation_id,
            template_id=prob.template_id,
            instance_seed=prob.instance_seed,
            tier=prob.tier,
            K=K,
            prompting_condition=prob.prompting_condition,
            benchmark=prob.benchmark,
            exec_rate=1.0 if result.exec_ok else 0.0,
            statement_coverage=result.statement_coverage,
            branch_coverage=result.branch_coverage,
            mutation_score=result.mutation_score,
            mutants_total=result.mutants_total,
            mutants_killed=result.mutants_killed,
            mutants_dropped_for_import_failure=result.mutants_dropped,
            generation_latency_seconds=latency,
            model_revision=model_out.model_revision,
            provider=model_out.provider,
            prompt_hash=model_out.prompt_hash,
            response=model_out.response,
            extracted_test_file=test_file,
            generation_config=model_out.generation_config,
            cost_usd=model_out.cost_usd,
            timestamp=model_out.timestamp,
            runtime_info=model_out.runtime_info,
            baseline_passed=result.baseline_passed,
            notes="; ".join(filter(None, [result.notes] + repairs)),
            model_label=safe_model,
            adapter_path=model_out.adapter_path,
            adapter_hash=model_out.adapter_hash,
        )
        append_jsonl(record, out_path)

        ms = f"{result.mutation_score:.2f}" if result.mutation_score is not None else "n/a"
        print(f"  [{i}/{len(problems)}] {prob.template_id} seed={prob.instance_seed} "
              f"exec={'Y' if result.exec_ok else 'N'} Mut@K={ms}")
        if model_out.cost_usd:
            total_cost += model_out.cost_usd

    if total_cost:
        print(f"\nTotal API cost: ${total_cost:.4f}")
    return out_path
