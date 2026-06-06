"""L1-format-002 - Format an integer label by joining a prefix and a padded counter.

Tier L1: CC=1, AST depth 0. Target mutant band 5-10; measured: 5.
Pattern: prefix + str(n).zfill(c)  -> AOR=1, CR=3, RSM=1 (total 5).
"""
from spec import (
    Template, DocstringTemplate, IntRange,
    IdentifierBank, StringChoice,
)


template = Template(
    template_id="L1-format-002",
    declared_tier="L1",
    declared_ast_depth=0,
    expected_mutant_count=(2, 8),

    parameter_spec={
        "fn_name": IdentifierBank(role="function_L1"),
        "n":       IdentifierBank(role="single_item"),
        "prefix":  StringChoice(values=("doc_", "rec_", "item_", "node_")),
        "width":   IntRange(lo=4, hi=8),
    },

    body_skeleton="""
def {fn_name}({n}):
    \"\"\"{docstring}\"\"\"
    return "{prefix}" + str({n}).zfill({width})
""",

    oracle=lambda n, prefix, width: prefix + str(n).zfill(width),

    docstring_template=DocstringTemplate(
        template="{intro} a fixed-width identifier {label_word} from prefix and counter.",
        synonyms={
            "intro": ("Return", "Build", "Compose", "Construct", "Form", "Assemble", "Produce"),
            "label_word": ("label", "string", "tag", "name", "token", "key"),
        },
    ),

    smoke_test_inputs=(
        {"n": 42,   "prefix": "doc_",  "width": 5},
        {"n": 0,    "prefix": "rec_",  "width": 6},
        {"n": 9999, "prefix": "node_", "width": 8},
    ),
)
