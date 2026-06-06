"""Instantiation engine v1 (Phase 2 sub-stage 2.4.b).

Given a Template and a seed, deterministically produce one concrete instance:
  1. Sample each parameter from its domain (seeded RNG).
  2. Build the substitution map.
  3. Render the body skeleton with the substitutions.
  4. Parse the result, compute CC, compare against tier band.
  5. Run smoke tests if requested.
"""
import ast
import random
import re
import keyword
import builtins as _builtins
import importlib.util
import sys
from pathlib import Path

# ---- import spec module from sibling directory ----
TEMPLATES_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TEMPLATES_ROOT))
from spec import (  # noqa: E402
    Template, DocstringTemplate, IntRange, FloatRange,
    IdentifierBank, LiteralChoice, LabelPair, ListShape, StringChoice,
)


# ---- reference identifier banks (Spec A.6) ----
IDENTIFIER_BANKS = {
    "function_L1":    ["compute_value", "transform", "format_value", "encode_input", "normalise_input"],
    "function_L2":    ["classify_input", "categorise_value", "validate_input", "check_value", "bucket_value"],
    "function_L3":    ["find_match", "count_items", "sum_values", "parse_input", "scan_sequence"],
    "function_L4":    ["process_order", "evaluate_state", "resolve_request", "orchestrate", "dispatch_event"],
    "counter":        ["i", "j", "k", "n", "count", "idx"],
    "accumulator":    ["total", "sum_", "result", "acc", "agg"],
    "index":          ["pos", "position", "idx", "offset"],
    "sequence":       ["items", "values", "elements", "data", "entries"],
    "single_item":    ["x", "val", "item", "elem", "sample"],
    "flag":           ["flag", "mode", "enabled", "active"],
}

LABEL_PAIR_GROUPS = {
    "magnitude":   [("high", "low"), ("large", "small"), ("heavy", "light")],
    "temperature": [("hot", "cold"), ("warm", "cool")],
    "position":    [("above", "below"), ("top", "bottom")],
    "validity":    [("valid", "invalid"), ("allowed", "denied")],
}

TIER_CC_BANDS = {"L1": (1, 1), "L2": (2, 3), "L3": (4, 7), "L4": (8, 99)}


# ---- CC computation (Spec B.2) ----
def compute_cc(tree: ast.AST) -> int:
    cc = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.AsyncFor)):
            cc += 1
        elif isinstance(node, ast.BoolOp):
            cc += len(node.values) - 1
        elif isinstance(node, ast.IfExp):
            cc += 1
        elif isinstance(node, ast.ExceptHandler):
            cc += 1
        elif isinstance(node, ast.comprehension):
            cc += len(node.ifs)
    return cc


def compute_ast_depth(fn: ast.FunctionDef) -> int:
    """Maximum nesting depth of compound statements inside the function body."""
    COMPOUND = (ast.If, ast.For, ast.While, ast.Try, ast.With,
                ast.AsyncFor, ast.AsyncWith)

    def _walk(node, depth):
        max_d = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, COMPOUND):
                max_d = max(max_d, _walk(child, depth + 1))
            else:
                max_d = max(max_d, _walk(child, depth))
        return max_d

    return _walk(fn, 0)


# ---- sampler ----
def _sample_domain(rng: random.Random, name: str, domain, already: dict):
    cls = type(domain).__name__
    if cls == "IntRange":
        # Uniform sampling within step
        n_steps = (domain.hi - domain.lo) // domain.step
        return domain.lo + rng.randint(0, n_steps) * domain.step
    if cls == "FloatRange":
        v = rng.uniform(domain.lo, domain.hi)
        return round(v, domain.decimals)
    if cls == "IdentifierBank":
        bank = IDENTIFIER_BANKS[domain.role]
        # avoid collision with named placeholders
        forbidden = {already.get(other) for other in domain.avoid_collision_with}
        forbidden |= set(keyword.kwlist) | set(dir(_builtins))
        candidates = [c for c in bank if c not in forbidden]
        return rng.choice(candidates) if candidates else rng.choice(bank)
    if cls == "LiteralChoice":
        if domain.weights:
            return rng.choices(domain.values, weights=domain.weights, k=1)[0]
        return rng.choice(domain.values)
    if cls == "LabelPair":
        pair = rng.choice(LABEL_PAIR_GROUPS[domain.group])
        # convention: any placeholder named "high_*" or "low_*" picks the appropriate side
        if name.startswith("high"):
            return pair[0]
        if name.startswith("low"):
            return pair[1]
        return pair[0]
    if cls == "StringChoice":
        return rng.choice(domain.values)
    if cls == "ListShape":
        ln = rng.randint(*domain.length_range)
        if ln == 0 and not domain.allow_empty:
            ln = 1
        return [_sample_domain(rng, name, domain.element_domain, already) for _ in range(ln)]
    raise TypeError(f"Unknown domain: {cls}")


# ---- grammar auto-fix for rendered docstrings ----
# The engine applies a small set of deterministic, idempotent post-substitution
# fix-ups to rendered docstrings. Each rule targets one class of error that
# arises from interactions between fixed template text and random synonym
# choices. Rules are ordered so later rules see the output of earlier ones.
import re as _re

# ---- Rule 1: a/an article agreement ----
# Phonetic-exception lists kept small because the docstring vocabulary is
# restricted to common English.
_AN_BEFORE_CONSONANT_LETTER = {
    "honest", "honour", "honest", "honourable", "hour", "heir",
}
_A_BEFORE_VOWEL_LETTER = {
    "unit", "universal", "university", "user", "useful", "useless",
    "one", "once", "useable", "usable", "euro", "european",
}


def _needs_an(word: str) -> bool:
    """Return True if `word` should be preceded by 'an' rather than 'a'."""
    if not word:
        return False
    w = word.lower().lstrip("\"'(`[")
    if not w:
        return False
    if w in _AN_BEFORE_CONSONANT_LETTER:
        return True
    if w in _A_BEFORE_VOWEL_LETTER:
        return False
    return w[0] in "aeiou"


_ARTICLE_PATTERN = _re.compile(r"\b(a|an|A|An)(\s+)([A-Za-z][A-Za-z\-']*)")


def _fix_articles(text: str) -> str:
    """Rule 1: a/an article agreement with phonetic-sound rule."""
    def repl(m):
        _, sep, next_word = m.group(1), m.group(2), m.group(3)
        is_capital = m.group(1)[0].isupper()
        target = "an" if _needs_an(next_word) else "a"
        if is_capital:
            target = target.capitalize()
        return f"{target}{sep}{next_word}"
    return _ARTICLE_PATTERN.sub(repl, text)


# ---- Rule 2: double-article collapse ----
# Catches "a a value" / "an a value" / "a an value" caused by an entry in a
# synonym bank already containing an article. Collapses to a single article
# (then Rule 1 re-applies to pick a/an correctly).
_DOUBLE_ARTICLE = _re.compile(r"\b([Aa]n?|[Aa])\s+([Aa]n?|[Aa])\s+", _re.IGNORECASE)


def _fix_double_articles(text: str) -> str:
    """Rule 2: collapse 'a a' / 'a an' / 'an a' / 'an an' sequences."""
    def repl(m):
        # Keep the second article (the one closer to the noun), preserve case
        # of the first one to stay sentence-initial-friendly.
        first_is_capital = m.group(1)[0].isupper()
        second = m.group(2).lower()
        if first_is_capital:
            second = second.capitalize()
        return f"{second} "
    return _DOUBLE_ARTICLE.sub(repl, text)


# ---- Rule 3: double-pluralisation (CATCH-AND-WARN ONLY) ----
# Reliable auto-fix for double-pluralisation requires a dictionary to
# distinguish "boxeses" (redundant) from a hypothetical legitimate plural that
# happens to end the same way. The pattern below catches the common cases that
# arise from "{noun}es" appended to a noun bank where the noun already ends in
# a sibilant or is already plural. We auto-fix the SAFE subset (ending in
# -seses, -xeses, -zeses, -sheses, -cheses) and leave ambiguous cases to the
# residual scan in test_residual.py.
_SAFE_DOUBLE_PLURAL = _re.compile(
    r"\b([A-Za-z]+?)(s|x|z|sh|ch)eses\b",
    _re.IGNORECASE,
)


def _fix_double_plurals(text: str) -> str:
    """Rule 3: catch the unambiguous -seses/-xeses/-zeses/-sheses/-cheses cases.

    These come from a singular noun ending in a sibilant (box, class, dash,
    match, buzz) being made plural twice: 'box' + 'es' + 'es' -> 'boxeses'.
    Fix: strip the redundant trailing 'es'.
    """
    return _SAFE_DOUBLE_PLURAL.sub(r"\1\2es", text)


# ---- Rule 4: redundant period/double-punctuation ----
# Catches "...by an offset.." or "?." caused by a synonym that already ends
# with terminal punctuation followed by template-fixed punctuation.
_DUP_PUNCT = _re.compile(r"([.!?])([.!?])+")


def _fix_double_punctuation(text: str) -> str:
    """Rule 4: collapse '..' '!!' '?.' etc. to a single terminal mark.

    Preserves the FIRST punctuation mark (typically what the synonym intended)
    rather than the second.
    """
    return _DUP_PUNCT.sub(r"\1", text)


# ---- Rule 5: double spaces ----
_DOUBLE_SPACE = _re.compile(r" {2,}")


def _fix_double_spaces(text: str) -> str:
    """Rule 5: collapse runs of multiple spaces to a single space."""
    return _DOUBLE_SPACE.sub(" ", text)


# ---- Rule 6: space-before-punctuation ----
# Catches " ." or " ," that can arise from "{slot}." where slot rendered empty.
_SPACE_BEFORE_PUNCT = _re.compile(r"\s+([.,;:!?])")


def _fix_space_before_punctuation(text: str) -> str:
    """Rule 6: remove whitespace before sentence-terminal/internal punctuation."""
    return _SPACE_BEFORE_PUNCT.sub(r"\1", text)


# ---- Rule 7: sentence-initial capitalisation ----
def _fix_sentence_initial_capital(text: str) -> str:
    """Rule 7: ensure the first letter of the (stripped) docstring is uppercase.

    Only acts on the very first alphabetic character to avoid disrupting
    intentionally lower-cased words (like identifiers, code references)
    elsewhere in the docstring.
    """
    stripped = text.lstrip()
    if not stripped or not stripped[0].isalpha() or stripped[0].isupper():
        return text
    lead_ws = text[:len(text) - len(stripped)]
    return f"{lead_ws}{stripped[0].upper()}{stripped[1:]}"


def _grammar_fix(text: str) -> str:
    """Apply all post-substitution grammar fixes in a stable order.

    Order matters:
      1. Collapse double articles first (so Rule 2 then Rule 1 picks a/an
         correctly on the remaining single article).
      2. Apply a/an rule.
      3. Plural / spacing / punctuation fixes commute.
      4. Capitalise sentence-initial last so any earlier rewrite is included.
    """
    text = _fix_double_articles(text)
    text = _fix_articles(text)
    text = _fix_double_plurals(text)
    text = _fix_double_punctuation(text)
    text = _fix_space_before_punctuation(text)
    text = _fix_double_spaces(text)
    text = _fix_sentence_initial_capital(text)
    return text


# ---- instantiate ----
def instantiate(template: Template, seed: int) -> dict:
    """Produce one instance from a template + seed.

    Returns a dict with: source, params, cc, ast_depth, validation_errors.
    """
    rng = random.Random(seed)
    params = {}
    # iterate in declaration order so collision-avoid sees what was sampled
    for name, dom in template.parameter_spec.items():
        params[name] = _sample_domain(rng, name, dom, params)

    # Render docstring
    docstring = template.docstring_template.template
    for grp, opts in template.docstring_template.synonyms.items():
        docstring = docstring.replace("{" + grp + "}", rng.choice(opts), 1)
    # Some templates reference parameter placeholders inside the docstring
    for k, v in params.items():
        docstring = docstring.replace("{" + k + "}", str(v))
    # Post-substitution grammar fix (a/an article agreement and similar)
    docstring = _grammar_fix(docstring)

    subs = {**{k: str(v) for k, v in params.items()}, "docstring": docstring}
    try:
        source = template.body_skeleton.format(**subs)
    except KeyError as e:
        return {"source": None, "params": params, "validation_errors": [f"placeholder missing: {e}"]}

    # Validate V1, V2, V4
    errors = []
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"source": source, "params": params, "validation_errors": [f"parse failed: {e}"]}

    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not funcs:
        return {"source": source, "params": params, "validation_errors": ["no FunctionDef"]}
    fn = funcs[0]

    cc = compute_cc(fn)
    depth = compute_ast_depth(fn)

    lo, hi = TIER_CC_BANDS[template.declared_tier]
    if not (lo <= cc <= hi):
        errors.append(f"V1 fail: CC={cc} outside {template.declared_tier}={lo}..{hi}")

    if abs(depth - template.declared_ast_depth) > 1:
        errors.append(f"V2 fail: ast_depth={depth} vs declared={template.declared_ast_depth}")

    return {
        "source": source,
        "params": params,
        "docstring": docstring,
        "cc": cc,
        "ast_depth": depth,
        "validation_errors": errors,
    }


# ---- template loader ----
def load_template(path: Path) -> Template:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.template


if __name__ == "__main__":
    # quick demo
    t = load_template(TEMPLATES_ROOT / "L2" / "L2-classifier-001.py")
    for s in [42, 99, 7]:
        r = instantiate(t, s)
        print(f"=== seed {s} (CC={r['cc']}, depth={r['ast_depth']}, errors={r['validation_errors']}) ===")
        print(r["source"])
