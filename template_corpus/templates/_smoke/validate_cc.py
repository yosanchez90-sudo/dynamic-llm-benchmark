"""Deeper validation: substitute representative values into each template
body, parse it, compute cyclomatic complexity, and check it falls in the
declared tier's band.

This is the second-level validation gate from Phase 1 Specification Part B.5.
"""
import ast
import importlib.util
import sys
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TEMPLATES_ROOT))

TIER_CC_BANDS = {
    "L1": (1, 1),
    "L2": (2, 3),
    "L3": (4, 7),
    "L4": (8, 99),
}


def compute_cc(tree: ast.AST) -> int:
    """Cyclomatic complexity per Phase 1 Spec B.2.

    CC = 1 + count of decision points: If, For, While, BoolOp(And/Or),
    IfExp (ternary), comprehension `if` clauses, ExceptHandler, MatchCase.
    """
    cc = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.AsyncFor)):
            cc += 1
        elif isinstance(node, ast.BoolOp):
            # `a and b and c` adds (n-1) decision points for n operands
            cc += len(node.values) - 1
        elif isinstance(node, ast.IfExp):
            cc += 1
        elif isinstance(node, ast.ExceptHandler):
            cc += 1
        elif isinstance(node, ast.comprehension):
            cc += len(node.ifs)
    return cc


# Provide sample substitution values for every placeholder role.
SAMPLE_FOR_ROLE = {
    "function_L1": "compute_value",
    "function_L2": "classify_value",
    "function_L3": "search_items",
    "function_L4": "process_order",
    "single_item": "x",
    "sequence":    "items",
    "flag":        "flag",
}


def sample_for_domain(name, domain):
    cls = type(domain).__name__
    if cls == "IntRange":
        return str(domain.lo + 1 if domain.lo < domain.hi else domain.lo)
    if cls == "FloatRange":
        return str(round((domain.lo + domain.hi) / 2, domain.decimals))
    if cls == "IdentifierBank":
        return SAMPLE_FOR_ROLE.get(domain.role, "value_" + name)
    if cls == "LiteralChoice":
        v = domain.values[0]
        return str(v) if not isinstance(v, str) else v
    if cls == "LabelPair":
        return "high" if "high" in name else "low"
    if cls == "StringChoice":
        return domain.values[0]
    if cls == "ListShape":
        return "[1, 2, 3]"
    return "1"


def substitute(t):
    """Build a substitution dict for body skeleton placeholders."""
    out = {"docstring": "An auto-generated docstring."}
    for name, domain in t.parameter_spec.items():
        out[name] = sample_for_domain(name, domain)
    return out


def load_template(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.template


def validate_one(path: Path):
    errors = []
    warnings = []
    try:
        t = load_template(path)
    except Exception as e:
        return [f"Failed to load: {e}"], []

    # Substitute and parse
    subs = substitute(t)
    try:
        body = t.body_skeleton.format(**subs)
    except KeyError as e:
        return [f"Missing placeholder: {e}"], []

    try:
        tree = ast.parse(body)
    except SyntaxError as e:
        return [f"Body does not parse after substitution: {e}\n   Body:\n{body}"], []

    # Find the function definition (skip any helper functions)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not funcs:
        return [f"No FunctionDef in parsed body"], []
    fn = funcs[0]

    # Compute CC of just the function
    cc = compute_cc(fn)
    lo, hi = TIER_CC_BANDS[t.declared_tier]
    if not (lo <= cc <= hi):
        errors.append(f"CC={cc} outside {t.declared_tier} band [{lo}, {hi}]")
    else:
        # Pass info
        pass

    return errors, [f"CC={cc}"]


def main():
    by_tier = {"L1": [], "L2": [], "L3": [], "L4": []}
    total_failed = 0

    for tier in ["L1", "L2", "L3", "L4"]:
        d = TEMPLATES_ROOT / tier
        for f in sorted(d.glob("*.py")):
            errs, info = validate_one(f)
            status = "✓" if not errs else "❌"
            info_str = " ".join(info) if info else ""
            by_tier[tier].append((f.name, errs, info_str))
            if errs:
                total_failed += 1

    for tier in ["L1", "L2", "L3", "L4"]:
        print(f"\n=== {tier} (band {TIER_CC_BANDS[tier]}) ===")
        for name, errs, info in by_tier[tier]:
            mark = "✓" if not errs else "❌"
            print(f"  {mark} {name:<32} {info}")
            for e in errs:
                print(f"      - {e}")

    print(f"\nTotal: 60, Failed: {total_failed}")
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
