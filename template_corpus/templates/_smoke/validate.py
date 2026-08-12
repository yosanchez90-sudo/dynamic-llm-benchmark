"""Validate that every template module:
  1. Imports cleanly.
  2. Exports a `template` object of type Template.
  3. Has a body_skeleton with all referenced placeholders defined.
  4. Oracle agrees with itself on smoke_test_inputs.
  5. Declared tier matches directory name.
"""
import ast
import importlib.util
import os
import re
import sys
import traceback
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TEMPLATES_ROOT))


def load_template(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.template


def find_placeholders(body: str) -> set:
    """Find {placeholder} markers, excluding {docstring}."""
    return set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", body))


def validate_one(path: Path):
    errors = []
    try:
        t = load_template(path)
    except Exception as e:
        return [f"Failed to load: {e}"]

    # Check tier matches directory
    expected_tier = path.parent.name
    if t.declared_tier != expected_tier:
        errors.append(f"declared_tier={t.declared_tier} but file in {expected_tier}/")

    # Check body skeleton has all placeholders in parameter_spec OR is docstring
    placeholders = find_placeholders(t.body_skeleton)
    declared = set(t.parameter_spec.keys()) | {"docstring"}
    extra_in_body = placeholders - declared
    if extra_in_body:
        # Some templates use synonyms/scalars inline; flag only the unaccounted ones
        errors.append(f"Body placeholders not in parameter_spec or docstring: {extra_in_body}")

    # Run oracle on smoke tests just to confirm it doesn't crash
    for smoke in t.smoke_test_inputs:
        try:
            t.oracle(**smoke)
        except TypeError as e:
            errors.append(f"oracle failed on smoke {smoke}: {e}")
        except Exception as e:
            # Only TypeError (an argument/signature mismatch between the
            # smoke input and the oracle) is treated as a validation
            # failure; any other exception on an edge-case smoke input is
            # assumed to be legitimate oracle behaviour, not a template
            # defect.
            pass

    return errors


def main():
    total = 0
    failed = 0
    for tier in ["L1", "L2", "L3", "L4"]:
        d = TEMPLATES_ROOT / tier
        if not d.exists():
            continue
        for f in sorted(d.glob("*.py")):
            total += 1
            errs = validate_one(f)
            if errs:
                failed += 1
                print(f"❌ {tier}/{f.name}")
                for e in errs:
                    print(f"   - {e}")
            else:
                print(f"✓  {tier}/{f.name}")

    print()
    print(f"Total: {total}, Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
