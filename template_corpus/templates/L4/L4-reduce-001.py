"""L4-reduce-001 - Build a filtered list, mid-body guard, then reduce it.

Tier L4: CC=8 (for + if/elif + guard-if + for + if/elif). The guard sits
between the two loops, an L4-distinctive control shape.
"""
from spec import Template, DocstringTemplate, IntRange, IdentifierBank


def _oracle(items, lo, hi, base):
    kept = []
    for x in items:
        if x > lo:
            kept.append(x)
        elif x < 0:
            kept.append(0)
    if not kept:
        return base
    total = 0
    for k in kept:
        if k > hi:
            total += k
        elif k == lo:
            total -= 1
    return total


template = Template(
    template_id="L4-reduce-001",
    declared_tier="L4",
    declared_ast_depth=3,
    expected_mutant_count=(31, 37),
    parameter_spec={
        "fn_name": IdentifierBank(role="function_L4"),
        "items":   IdentifierBank(role="sequence"),
        "kept":    IdentifierBank(role="accumulator"),
        "total":   IdentifierBank(role="accumulator", avoid_collision_with=("kept",)),
        "x":       IdentifierBank(role="single_item"),
        "k":       IdentifierBank(role="single_item", avoid_collision_with=("x",)),
        "lo":      IntRange(lo=5, hi=15),
        "hi":      IntRange(lo=25, hi=50),
        "base":    IntRange(lo=2, hi=9),
    },
    body_skeleton="""
def {fn_name}({items}):
    \"\"\"{docstring}\"\"\"
    {kept} = []
    for {x} in {items}:
        if {x} > {lo}:
            {kept}.append({x})
        elif {x} < 0:
            {kept}.append(0)
    if not {kept}:
        return {base}
    {total} = 0
    for {k} in {kept}:
        if {k} > {hi}:
            {total} += {k}
        elif {k} == {lo}:
            {total} -= 1
    return {total}
""",
    oracle=_oracle,
    docstring_template=DocstringTemplate(
        template="{intro} the {survivor_word} entries, then {sum_act} the largest, or a {fallback_word} code.",
        synonyms={
            "intro": ("Filter", "Keep", "Retain", "Select", "Screen", "Sift"),
            "survivor_word": ("surviving", "retained", "kept", "remaining", "passing"),
            "sum_act": ("total", "bank", "accrue", "gather", "add up"),
            "fallback_word": ("fallback", "default", "spare", "reserve", "guard"),
        },
    ),
    smoke_test_inputs=(
        {"items": [],              "lo": 10, "hi": 30, "base": 4},
        {"items": [25],            "lo": 10, "hi": 30, "base": 4},
        {"items": [3, 35, -2, 12], "lo": 10, "hi": 30, "base": 4},
    ),
)
