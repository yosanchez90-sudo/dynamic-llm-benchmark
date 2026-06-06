"""L1-string-001 - Wrap a string in brackets and append a counter suffix.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 7.
Pattern: "[" + s + "]" + str(c)  -> AOR=3, CR=3, RSM=1 (total 7).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank, StringChoice,
)


template = Template(
    template_id="L1-string-001",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(4, 10),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L1"),
        "s":       IdentifierBank(role="single_item"),
        "left":    StringChoice(values=("[", "(", "{", "<")),
        "right":   StringChoice(values=("]", ")", "}", ">")),
        "counter": IntRange(lo=1, hi=99),
    },

    body_skeleton="""
def {fn_name}({s}):
    \"\"\"{docstring}\"\"\"
    return "{left}" + {s} + "{right}" + str({counter})
""",

    oracle=lambda s, left, right, counter: left + s + right + str(counter),

    docstring_template=DocstringTemplate(
        template="{intro} the string {wrap_verb} in brackets and {append_verb} a numeric suffix.",
        synonyms={
            "intro": ("Return", "Build", "Compose", "Construct", "Form", "Assemble"),
            "wrap_verb": ("wrapped", "enclosed", "framed", "surrounded", "encapsulated", "delimited"),
            "append_verb": ("with", "appended with", "followed by", "trailed by", "ending in"),
        },
    ),

    smoke_test_inputs=(
        {"s": "hi",   "left": "[", "right": "]", "counter": 1},
        {"s": "",     "left": "(", "right": ")", "counter": 99},
        {"s": "test", "left": "{", "right": "}", "counter": 42},
    ),
)
