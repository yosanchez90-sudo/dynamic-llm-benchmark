"""L1-string-002 - Compose a padded identifier string from prefix and number.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 5.
Pattern: prefix + str(n).zfill(c)  -> AOR=1, CR=3, RSM=1 (total 5).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank, StringChoice,
)


template = Template(
    template_id="L1-string-002",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(2, 8),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L1"),
        "n":       IdentifierBank(role="single_item"),
        "prefix":  StringChoice(values=("id_", "ord_", "item_", "row_")),
        "width":   IntRange(lo=3, hi=8),
    },

    body_skeleton="""
def {fn_name}({n}):
    \"\"\"{docstring}\"\"\"
    return "{prefix}" + str({n}).zfill({width})
""",

    oracle=lambda n, prefix, width: prefix + str(n).zfill(width),

    docstring_template=DocstringTemplate(
        template="{intro} an identifier by {action_word} a {padding_word} number to a prefix.",
        synonyms={
            "intro": ("Return", "Build", "Compose", "Construct", "Form", "Assemble"),
            "action_word": ("appending", "joining", "concatenating", "attaching", "prepending"),
            "padding_word": ("zero-padded", "fixed-width", "left-padded", "uniform-width", "leading-zero"),
        },
    ),

    smoke_test_inputs=(
        {"n": 1,    "prefix": "id_",  "width": 4},
        {"n": 0,    "prefix": "ord_", "width": 5},
        {"n": 999,  "prefix": "row_", "width": 6},
    ),
)
