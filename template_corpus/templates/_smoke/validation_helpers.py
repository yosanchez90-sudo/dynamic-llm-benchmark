"""Shared guards for validation/audit/sweep scripts in this corpus.

Written after the 2026-08-03 validator sweep (analysis/VALIDATOR_SWEEP.md)
found the same failure shape in three places: validate.py's stale
TEMPLATES_ROOT silently validated zero templates while still printing
success; validate_cc.py printed a hardcoded "Total: 60, Failed: 0" instead
of a computed one; archive_diversity_audit.py's generated README hardcoded
its summary prose instead of recomputing it from the CSVs it had just
written. All three are "looked like it passed, wasn't actually checking
anything" -- the two helpers below make that class of bug impossible to
introduce silently: `assert_checked` fails loudly instead of letting an
empty population read as a clean pass, and `require_library` fails loudly
instead of silently substituting a weaker approximation (see CLAUDE.md's
"library fallbacks must raise, not approximate" rule, added for the same
reason after diversity_v2.py's sacrebleu-to-Jaccard fallback was found).
"""
from __future__ import annotations

import importlib
from types import ModuleType


def assert_checked(n: int, what: str) -> None:
    """Raise if a validation loop checked zero items.

    A validator that iterates zero times and reports "0 failed" is
    indistinguishable, from its own output alone, from one that checked
    everything and found no problems -- this is exactly the shape of the
    validate.py stale-path bug (2026-07-13, commit 2d5fc9d). Call this
    immediately after the count is known and before printing/using it.
    """
    if n == 0:
        raise AssertionError(
            f"validated ZERO items for {what!r} -- this is almost always a "
            f"stale path, an empty glob, or an over-strict filter, not a "
            f"genuinely empty population. Fix the population before trusting "
            f"any pass/fail count from this run."
        )


def require_library(module_name: str, purpose: str) -> ModuleType:
    """Import `module_name` or raise ImportError with a clear message.

    Use this instead of a silent `try: import X; except ImportError:
    HAVE_X = False` pattern that then falls back to a cruder approximation
    -- that pattern let every within-tier diversity run before 2026-07-14
    silently use a 4-gram Jaccard approximation instead of real BLEU-4
    (sacrebleu was never a declared dependency until commit d16f122), with
    only a `print()` line -- not an error, not a persisted field in the
    output JSON -- distinguishing which metric had actually run.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(
            f"{module_name} is required for {purpose} and is not installed. "
            f"Install it -- do not fall back to an approximation, per "
            f"CLAUDE.md's 'library fallbacks must raise, not approximate' rule."
        ) from e
