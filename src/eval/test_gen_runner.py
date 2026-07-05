"""Test-generation runner: ties model + loader + harness together.

PARALLELISM ARCHITECTURE
------------------------
Level 1 (within a problem): multiprocessing.Pool in test_gen_scorer.py covers
the ~20-30 mutants per problem. Pool size = mutation_workers in config, which
MUST equal --cpus-per-task in the SLURM script — don't oversubscribe.

Level 2 (across problems): SLURM array jobs via scripts/slurm/run_mutation_array.slurm.
The 1,500 problems are split into N shards; each array task handles one shard
and writes its own JSONL. Merging is trivial (glob + concat).

Shard slicing uses stride (problems[shard_id::n_shards]) to balance load across
shards: this interleaves L1 and L2 problems so each shard has a representative
mix rather than one shard getting all L1 (fast) and another all L2 (slower).

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

from src.data import test_gen
from src.eval.test_gen_problem import TestGenRecord
from src.eval.test_gen_scorer import extract_test_file, sanitize_test_file, score_problem
from src.logging_utils import append_jsonl
from src.models.base import GenerationConfig
from src.models.factory import build_model

load_dotenv()


def _find_resume_file(
    out_dir: Path,
    safe_model: str,
    benchmark: str,
    prompting_condition: str,
    instantiation_id: str,
    n_shards: int,
    shard_id: int,
) -> tuple[Path | None, set[tuple[str, int]]]:
    """Return (existing_jsonl_path, already_done_pairs) if a partial run exists.

    "already done" means a (template_id, instance_seed) pair that already has
    a record in the file.  The caller filters these out of the problem list and
    appends to the same file so the completed run is a single contiguous JSONL.
    """
    if n_shards > 1:
        pattern = (
            f"{safe_model}__{benchmark}__{prompting_condition}"
            f"__inst{instantiation_id}__shard{shard_id}of{n_shards}_*.jsonl"
        )
    else:
        pattern = (
            f"{safe_model}__{benchmark}__{prompting_condition}"
            f"__inst{instantiation_id}_*.jsonl"
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


def run_test_gen_experiment(config: dict[str, Any]) -> Path:
    """Run one test-generation config end-to-end. Returns the JSONL path."""
    model = build_model(config["model"])
    gen_cfg = GenerationConfig(**config["generation"])

    K = config.get("K", 1)
    n_workers = config.get("mutation_workers", 4)
    mutant_timeout = config.get("mutant_timeout_seconds", 30)

    problems = test_gen.load(
        instantiation_id=config["instantiation_id"],
        instantiation_seed=config["instantiation_seed"],
        instance_seeds=tuple(config.get("instance_seeds", (101, 102, 103, 104, 105))),
        tiers=tuple(config.get("tiers", ("L1", "L2"))),
        prompting_condition=config["prompting_condition"],
    )

    # Level 2 parallelism: slice this task's shard of the problem list.
    # Strided slicing balances the workload — each shard gets a mix of tiers.
    n_shards = config.get("n_shards", 1)
    shard_id = config.get("shard_id", 0)
    if n_shards > 1:
        problems = problems[shard_id::n_shards]

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    safe_model = config["model"]["id"].replace("/", "__")
    # Fine-tuned models share the same base model id — append the adapter tag so
    # their output files don't collide with baseline runs or each other.
    adapter_path = config["model"].get("adapter_path")
    if adapter_path:
        adapter_tag = Path(adapter_path).parent.name   # e.g. "qwen7b_lora_inst1"
        safe_model = f"{safe_model}__ft_{adapter_tag}"
    out_dir = Path(config["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resume detection: if a partial run exists for this exact experiment,
    # reuse its file and skip already-completed problems.
    resume_path, done_pairs = _find_resume_file(
        out_dir, safe_model,
        config["benchmark"], config["prompting_condition"],
        config["instantiation_id"], n_shards, shard_id,
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
                f"{config['prompting_condition']}__inst{config['instantiation_id']}__"
                f"shard{shard_id}of{n_shards}__{run_ts}.jsonl"
            )
        else:
            out_path = out_dir / (
                f"{safe_model}__{config['benchmark']}__"
                f"{config['prompting_condition']}__inst{config['instantiation_id']}__{run_ts}.jsonl"
            )

    print(f"Output: {out_path}")
    shard_info = f" (shard {shard_id}/{n_shards})" if n_shards > 1 else ""
    print(f"{len(problems)} problems remaining{shard_info} | K={K} | workers={n_workers}\n")

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
