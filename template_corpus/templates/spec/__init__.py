"""Phase 1 specification objects, imported by every template file.

This module is the single source of truth for the Template grammar
defined in the Phase 1 Specifications document, Part A. All 60 templates
declare an instance of Template (defined below) and the engine consumes
that instance to produce concrete benchmark problems at evaluation time.
"""

from dataclasses import dataclass, field
from typing import Callable, Any


# ============================================================
# Parameter-domain language (Spec A.3)
# ============================================================

@dataclass(frozen=True)
class IntRange:
    """Samples an integer from a closed interval, optionally with a step."""
    lo: int
    hi: int
    step: int = 1
    distribution: str = "uniform"   # "uniform" | "log_uniform"


@dataclass(frozen=True)
class FloatRange:
    """Samples a float from an interval, with optional rounding."""
    lo: float
    hi: float
    decimals: int = 2
    distribution: str = "uniform"


@dataclass(frozen=True)
class IdentifierBank:
    """Samples an identifier from a curated bank keyed by semantic role."""
    role: str
    avoid_collision_with: tuple = ()


@dataclass(frozen=True)
class LiteralChoice:
    """Samples one value from a fixed list."""
    values: tuple
    weights: tuple = None


@dataclass(frozen=True)
class LabelPair:
    """Samples a pair of mutually-exclusive labels from a curated group."""
    group: str


@dataclass(frozen=True)
class ListShape:
    """Samples a list of a given length range with elements from another domain."""
    length_range: tuple              # (min_len, max_len), inclusive
    element_domain: Any
    allow_empty: bool = False


@dataclass(frozen=True)
class StringChoice:
    """Samples one string from a choice set."""
    values: tuple


# ============================================================
# Docstring template (Spec A.5)
# ============================================================

@dataclass(frozen=True)
class DocstringTemplate:
    """Natural-language docstring with synonym groups for variation."""
    template: str
    synonyms: dict = field(default_factory=dict)


# ============================================================
# The Template object (Spec A.2)
# ============================================================

@dataclass(frozen=True)
class Template:
    """The complete specification of one benchmark template.

    Per Phase 1 specification A.2, every field is required.
    """
    template_id: str                 # e.g. "L2-classifier-001"
    declared_tier: str               # "L1" | "L2" | "L3" | "L4"
    declared_ast_depth: int          # expected nesting depth

    # Per-template stability band, NOT the tier-membership criterion.
    # Tier is defined by cyclomatic complexity alone (CC bands: L1=1, L2=2-3,
    # L3=4-7, L4≥8), enforced at instantiation time by the engine.
    #
    # This tuple is (measured - 3, measured + 3) where `measured` is the
    # author's spot-checked count on a representative instance. Its purpose is
    # a stability guard: it catches templates where mutant count varies wildly
    # across seeds (e.g. a parameter range that sometimes adds/removes a whole
    # operator's worth of sites). A few templates legitimately exceed the tier
    # target range for documented structural reasons (e.g. L2-range-001's
    # chained comparison generates extra ROR+BM sites); their higher band
    # reflects the actual measured count and is correct.
    expected_mutant_count: tuple     # (lo, hi): per-template stability band

    parameter_spec: dict             # name -> ParameterDomain
    body_skeleton: str               # source string with {placeholders}
    oracle: Callable                 # reference implementation
    docstring_template: DocstringTemplate

    smoke_test_inputs: tuple         # tuple of dicts of param values for oracle check
