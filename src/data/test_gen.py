"""Test-generation dataset loader.

Turns the template corpus into TestGenProblem objects by:
  1. Loading each template (handles hyphenated filenames via importlib).
  2. Calling the engine's instantiate(template, seed) for each instance seed.
  3. Precomputing the mutant set ONCE per instance (same mutants reused
     across all models — faster and fairer comparison).
  4. Building the zero-shot or one-shot prompt the model receives.

Import paths for engine and spec use sys.path manipulation because
template_corpus/ is outside src/ — the engine is not a package. This is
intentional: the engine is a standalone research artefact with its own tests.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_TEMPLATE_ROOT = Path(__file__).resolve().parent.parent.parent / "template_corpus" / "templates"
sys.path.insert(0, str(_TEMPLATE_ROOT))
sys.path.insert(0, str(_TEMPLATE_ROOT / "_smoke"))

from engine import instantiate  # noqa: E402  (from template_corpus/_smoke/engine.py)
from spec import Template        # noqa: E402  (from template_corpus/spec/__init__.py)

from src.eval.mutation_adapter import generate_mutants
from src.eval.test_gen_problem import TestGenProblem

# The one-shot demonstration (spec §3.2.4). Must be authored and frozen before
# any cross-model comparison. Set to None to keep one-shot disabled.
try:
    from data.prompts.one_shot_demo import DEMONSTRATION  # type: ignore
except Exception:
    DEMONSTRATION = None


SYSTEM_INSTRUCTION = (
    "You are an expert Python developer writing a pytest test suite. "
    "You are given a Python function. "
    "Write a complete pytest test file that thoroughly tests this function, "
    "covering normal cases, edge cases, and boundary conditions. "
    "IMPORTANT: you must import the function under test with exactly "
    "`from under_test import <function_name>` — do NOT copy, redefine, or "
    "reimplement the function in your test file. "
    "Output only the test file, starting with the import statement."
)


def _load_template(path: Path) -> Template:
    """Load a template module by path (filenames contain hyphens → importlib)."""
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    for value in vars(module).values():
        if isinstance(value, Template):
            return value
    raise ValueError(f"No Template instance found in {path}")


def _build_messages(source: str, prompting_condition: str) -> list[dict[str, str]]:
    """Construct chat messages for one problem (spec §2.5.6)."""
    user = f"Function under test:\n\n```python\n{source}\n```\n\nWrite the pytest test file."
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    if prompting_condition == "one_shot":
        if DEMONSTRATION is None:
            raise RuntimeError(
                "one_shot requested but no DEMONSTRATION has been authored. "
                "See src/data/prompts/one_shot_demo.py."
            )
        messages.append({"role": "user", "content": DEMONSTRATION["function"]})
        messages.append({"role": "assistant", "content": DEMONSTRATION["test_file"]})
    messages.append({"role": "user", "content": user})
    return messages


def _extract_fn_name(source: str) -> str:
    import ast
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef):
            return node.name
    raise ValueError("No function definition found in instance source")


def load(
    instantiation_id: str,
    instantiation_seed: int,
    instance_seeds: tuple[int, ...] = (101, 102, 103, 104, 105),
    tiers: tuple[str, ...] = ("L1", "L2"),
    prompting_condition: str = "zero_shot",
) -> list[TestGenProblem]:
    """Generate one benchmark instantiation as a flat list of TestGenProblem.

    Per the spec: 15 templates/tier × 5 instance seeds = 75 problems per tier.
    `instantiation_seed` offsets the per-instance seeds so five distinct
    instantiations produce genuinely different instances (stability analysis).
    """
    problems: list[TestGenProblem] = []
    for tier in tiers:
        for tmpl_path in sorted((_TEMPLATE_ROOT / tier).glob(f"{tier}-*.py")):
            tmpl = _load_template(tmpl_path)
            for base_seed in instance_seeds:
                seed = instantiation_seed * 1000 + base_seed
                inst = instantiate(tmpl, seed)
                if inst.get("validation_errors"):
                    continue
                source = inst["source"]
                fn_name = _extract_fn_name(source)
                problems.append(TestGenProblem(
                    template_id=tmpl.template_id,
                    tier=tier,
                    instance_seed=seed,
                    instantiation_id=instantiation_id,
                    benchmark="dynamic",
                    prompting_condition=prompting_condition,
                    fn_name=fn_name,
                    source=source,
                    docstring=inst["docstring"],
                    mutants=generate_mutants(source),
                    oracle=getattr(tmpl, "oracle", None),
                    messages=_build_messages(source, prompting_condition),
                ))
    return problems
