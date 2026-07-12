"""L3-sum-001 - Weighted sum over a sequence with a two-sided branch.

Tier L3: CC=4 (for + if/elif), loop over a sequence. Target mutant band 15-25.
Body pattern:
    acc = 0
    for x in items:
        if x > hi:   acc += x * weight
        elif x < lo: acc -= step
    return acc
Exercises ROR (two comparisons), BM (hi, lo), CR (init 0, weight, step),
AOR (x * weight), SDL (init + two augmented assigns) and RSM for the first time.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, hi, lo, weight, step):
    acc = 0
    for x in items:
        if x > hi:
            acc += x * weight
        elif x < lo:
            acc -= step
    return acc


template = Template(
    template_id="L3-sum-001",
    declared_tier="L3",
    declared_ast_depth=3,
    expected_mutant_count=(19, 25),   # measured 22; band = measured +/- 3   # provisional; set from measurement below

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "acc":     IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "hi":      IntRange(lo=15, hi=40),
        "lo":      IntRange(lo=2, hi=12),
        "weight":  IntRange(lo=2, hi=9),
        "step":    IntRange(lo=2, hi=9),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {acc} = 0
    for {x} in {items}:
        if {x} > {hi}:
            {acc} += {x} * {weight}
        elif {x} < {lo}:
            {acc} -= {step}
    return {acc}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} a {total_word} that {credits} {big_word} numbers and {debits} {small_word} ones.",
        synonyms={
            "intro": ("Return", "Compute", "Accumulate", "Produce", "Derive", "Build"),
            "total_word": ("total", "sum", "aggregate", "tally", "score"),
            "credits": ("rewards", "boosts", "scales up", "weights", "favours"),
            "big_word": ("high", "upper", "large", "over-ceiling", "top"),
            "debits": ("docks", "trims", "penalises", "reduces", "discounts"),
            "small_word": ("low", "under-floor", "minor", "bottom", "lesser"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],            "hi": 20, "lo": 5, "weight": 3, "step": 2},
        {"items": [25],          "hi": 20, "lo": 5, "weight": 3, "step": 2},
        {"items": [1, 8, 30, 50, -3, 22], "hi": 20, "lo": 5, "weight": 3, "step": 2},
    ),
)
