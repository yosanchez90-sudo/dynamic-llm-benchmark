"""L4-scan-001 - Guarded conditional nested scan with an outer fallthrough.

Tier L4: CC=8 (guard + for + if + nested-for + if/elif + outer-elif).
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, hi, lo):
    if not items:
        return 0
    hits = 0
    for x in items:
        if x > lo:
            for y in items:
                if x + y > hi:
                    hits += x
                elif x == y:
                    hits += 1
        elif x < lo:
            hits -= 1
    return hits


template = Template(
    template_id="L4-scan-001",
    declared_tier="L4",
    declared_ast_depth=5,
    expected_mutant_count=(27, 33),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "hits":    IdentifierBank(role="accumulator"),
        "x":       IdentifierBank(role="single_item"),
        "y":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "hi":      IntRange(lo=20, hi=45),
        "lo":      IntRange(lo=2, hi=12),
    },
    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    if not {items}:
        return 0
    {hits} = 0
    for {x} in {items}:
        if {x} > {lo}:
            for {y} in {items}:
                if {x} + {y} > {hi}:
                    {hits} += {x}
                elif {x} == {y}:
                    {hits} += 1
        elif {x} < {lo}:
            {hits} -= 1
    return {hits}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} a {metric_word}, pairing only {active_word} entries and {dock_act} the rest.",
        synonyms={
            "intro": ("Return", "Compute", "Produce", "Derive", "Build", "Evaluate"),
            "metric_word": ("score", "tally", "figure", "result", "reading"),
            "active_word": ("qualifying", "above-floor", "eligible", "passing", "live"),
            "dock_act": ("docking", "penalising", "discounting", "skipping", "dropping"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],            "hi": 30, "lo": 5},
        {"items": [12],          "hi": 30, "lo": 5},
        {"items": [3, 18, 25, 7], "hi": 30, "lo": 5},
    ),
)
