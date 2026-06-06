"""Data structures for the test-generation task.

Two dataclasses:
  - TestGenProblem: one function-under-test the model must write tests for,
    plus everything the harness needs to score the response.
  - TestGenRecord: one row of the spec's tidy-data output schema (§3.1.2.3),
    written to JSONL. Carries provenance + the four metrics.

REPO TARGET: src/eval/test_gen_problem.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Mutant:
    """One semantic-altering mutant of a function-under-test.

    `source` is the COMPLETE mutated function source (ready to write to a
    module and import) — NOT a marker tuple. See mutation_adapter.py for how
    the seven SAC operators populate this.
    """
    operator: str          # "AOR" | "ROR" | "LOR" | "CR" | "BM" | "SDL" | "RSM"
    source: str            # full mutated function source
    description: str = ""  # e.g. "+ -> -" (for survival-mutant analysis later)


@dataclass
class TestGenProblem:
    """One problem: the model is shown `source` + `docstring` and must write
    a pytest suite. Everything else is for the harness and the tidy record.
    """
    # --- identity (populate the tidy-data identifier columns) ---
    template_id: str
    tier: str                       # "L1" | "L2" | "L3" | "L4"
    instance_seed: int
    instantiation_id: str           # which of the 5 benchmark instantiations
    benchmark: str                  # "dynamic" | "ult" | "plt"
    prompting_condition: str        # "zero_shot" | "one_shot"

    # --- the function under test ---
    fn_name: str                    # the def name the model's tests must import
    source: str                     # the instance source shown to the model
    docstring: str                  # the rendered docstring shown to the model

    # --- scoring material (NOT shown to the model) ---
    mutants: list[Mutant] = field(default_factory=list)
    oracle: Callable[..., Any] | None = None   # reference impl, for smoke checks

    # --- the prompt actually sent (built by the loader) ---
    messages: list[dict[str, str]] = field(default_factory=list)


@dataclass
class TestGenRecord:
    """One row of the spec's tidy dataset (§3.1.2.3). This is what gets
    written to JSONL — one record per (model, problem) evaluation.

    The column names match the spec EXACTLY so analysis code can rely on them.
    """
    # --- identifiers (spec §3.1.2.3) ---
    model: str
    instantiation_id: str
    template_id: str
    instance_seed: int
    tier: str
    K: int
    prompting_condition: str
    benchmark: str

    # --- outcomes (spec §3.1.2.3) ---
    exec_rate: float                       # Exec@K gate
    statement_coverage: float | None       # Cov-S@K
    branch_coverage: float | None          # Cov-B@K
    mutation_score: float | None           # Mut@K (headline)
    mutants_total: int
    mutants_killed: int
    mutants_dropped_for_import_failure: int
    generation_latency_seconds: float

    # --- provenance (carried from ModelOutput; not in the spec's column list
    #     but required by CLAUDE.md and good practice) ---
    model_revision: str = ""
    provider: str = ""
    prompt_hash: str = ""
    response: str = ""                      # raw model output (keep for analysis)
    extracted_test_file: str = ""           # what we actually ran
    generation_config: dict[str, Any] = field(default_factory=dict)
    cost_usd: float | None = None
    timestamp: str = ""
    runtime_info: dict[str, Any] = field(default_factory=dict)
    baseline_passed: bool | None = None     # did the suite pass on the ORIGINAL?
    notes: str = ""                         # free-text flags (e.g. exec failure)
