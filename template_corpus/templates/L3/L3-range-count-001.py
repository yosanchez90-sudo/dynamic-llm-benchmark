"""L3-range-count-001 - Count elements inside a band (conjunction condition).

Tier L3: CC=4 (for + if with BoolOp 'and'). Body pattern:
    count = 0
    for x in items:
        if x >= lo and x <= hi:
            count += 1
    return count
The corpus's dedicated L3 LOR (and) site.
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank,
)


def _oracle(items, lo, hi):
    count = 0
    for x in items:
        if x >= lo and x <= hi:
            count += 1
    return count


template = Template(
    template_id="L3-range-count-001",
    declared_tier="L3",
    declared_ast_depth=2,
    expected_mutant_count=(14, 20),   # measured 17; band = measured +/- 3

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L3"),
        "items":   IdentifierBank(role="sequence"),
        "count":   IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "lo":      IntRange(lo=2, hi=15),
        "hi":      IntRange(lo=25, hi=60),
    },

    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {count} = 0
    for {x} in {items}:
        if {x} >= {lo} and {x} <= {hi}:
            {count} += 1
    return {count}
""",

    oracle=_oracle,

    docstring_template=DocstringTemplate(
        template="{intro} {howmany} numbers {between_word} the lower and upper bounds.",
        synonyms={
            "intro": ("Return", "Report", "Produce", "Give", "Yield", "Find"),
            "howmany": ("how many", "the number of", "a count of", "the quantity of", "the tally of"),
            "between_word": ("between", "inside", "within", "amid", "spanning"),
        },
    ),

    smoke_test_inputs=(
        {"items": [],               "lo": 10, "hi": 40},
        {"items": [25],             "lo": 10, "hi": 40},
        {"items": [5, 20, 45, 33],  "lo": 10, "hi": 40},
    ),
)
