"""Mutation engine prototype for Phase 2 mutation-density sanity check.

Implements the 7 SAC operators from Phase 1 Spec Part C as AST rewriters.
Single-edit per mutant, with BM/CR context precedence.

This is a Phase 2 *prototype* only — production version goes in Phase 3.
We need it now to confirm that each template's expected_mutant_count band
is realistic.
"""
import ast
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_smoke"))

from engine import instantiate, load_template  # noqa: E402


# ---- helpers ----
def _node_in_boundary_context(node, parents):
    """Is this ast.Constant in a range arg, subscript, or Compare operand?"""
    if not isinstance(node, ast.Constant) or not isinstance(node.value, int):
        return False
    if len(parents) < 1:
        return False
    parent = parents[-1]
    # range() call
    if isinstance(parent, ast.Call):
        if isinstance(parent.func, ast.Name) and parent.func.id == "range":
            return True
    # subscript
    if isinstance(parent, ast.Subscript):
        return True
    if isinstance(parent, ast.Slice):
        return True
    # compare operand
    if isinstance(parent, ast.Compare):
        return True
    return False


def _walk_with_parents(tree):
    """Yield (node, parent_chain) for every node."""
    def _walk(node, parents):
        yield node, parents
        for child in ast.iter_child_nodes(node):
            yield from _walk(child, parents + [node])
    yield from _walk(tree, [])


# ---- operator implementations ----

def _aor(tree):
    """Arithmetic Operator Replacement."""
    repl = {
        ast.Add:      [ast.Sub],
        ast.Sub:      [ast.Add],
        ast.Mult:     [ast.Div],
        ast.Div:      [ast.Mult],
        ast.FloorDiv: [ast.Div, ast.Mult],
        ast.Mod:      [ast.Mult],
        ast.Pow:      [ast.Mult],
    }
    sites = []
    for node, _ in _walk_with_parents(tree):
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in repl:
                for r in repl[op_type]:
                    sites.append((node, r))
    return [_apply(tree, n, lambda nn, R=r: setattr(nn, "op", R())) for n, r in sites]


def _ror(tree):
    """Relational Operator Replacement."""
    repl = {
        ast.Lt:    [ast.LtE, ast.Gt, ast.Eq],
        ast.LtE:   [ast.Lt,  ast.GtE, ast.NotEq],
        ast.Gt:    [ast.GtE, ast.Lt, ast.Eq],
        ast.GtE:   [ast.Gt,  ast.LtE, ast.NotEq],
        ast.Eq:    [ast.NotEq],
        ast.NotEq: [ast.Eq],
    }
    sites = []
    for node, _ in _walk_with_parents(tree):
        if isinstance(node, ast.Compare):
            for idx, op in enumerate(node.ops):
                op_type = type(op)
                if op_type in repl:
                    for r in repl[op_type]:
                        sites.append((node, idx, r))
    return [_apply(tree, n, lambda nn, I=i, R=r: nn.ops.__setitem__(I, R())) for n, i, r in sites]


def _lor(tree):
    """Logical Operator Replacement."""
    sites = []
    for node, _ in _walk_with_parents(tree):
        if isinstance(node, ast.BoolOp):
            sites.append(("bool", node))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            sites.append(("not", node))
    out = []
    for kind, n in sites:
        if kind == "bool":
            new_op = ast.Or if isinstance(n.op, ast.And) else ast.And
            out.append(_apply(tree, n, lambda nn, O=new_op: setattr(nn, "op", O())))
        else:
            # replace `not x` with `x` -> requires parent edit; simulate by counting
            out.append(("LOR-not", "remove-not", n))
    return out


def _cr(tree, boundary_nodes):
    """Constant Replacement (excludes boundary sites)."""
    sites = []
    for node, parents in _walk_with_parents(tree):
        if not isinstance(node, ast.Constant):
            continue
        if id(node) in boundary_nodes:
            continue
        v = node.value
        if isinstance(v, bool):
            sites.append((node, not v))
        elif isinstance(v, int):
            for new in {0, 1, -v if v != 0 else 1}:
                if new != v:
                    sites.append((node, new))
        elif isinstance(v, float):
            for new in {0.0, 1.0}:
                if new != v:
                    sites.append((node, new))
    return [_apply(tree, n, lambda nn, V=val: setattr(nn, "value", V)) for n, val in sites]


def _bm(tree):
    """Boundary Mutation — int literals in boundary contexts only.

    Returns (mutants, boundary_node_ids) so CR can exclude them.
    """
    sites = []
    boundary_ids = set()
    for node, parents in _walk_with_parents(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, int):
            continue
        if _node_in_boundary_context(node, parents):
            boundary_ids.add(id(node))
            sites.append((node, node.value + 1))
            sites.append((node, node.value - 1))
    return [_apply(tree, n, lambda nn, V=v: setattr(nn, "value", V)) for n, v in sites], boundary_ids


def _sdl(tree):
    """Statement Deletion of safe statements."""
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    sites = []
    for stmt in ast.walk(fn):
        if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            sites.append(stmt)
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            sites.append(stmt)
    return [("SDL", s) for s in sites]


def _rsm(tree):
    """Return-Statement Mutation."""
    sites = []
    for node, _ in _walk_with_parents(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            sites.append(node)
    return [("RSM", r) for r in sites]


def _apply(tree, target_node, mutate_fn):
    """Apply a single mutation by deep-copying the tree and mutating the matching node."""
    new_tree = copy.deepcopy(tree)
    # Find the same node in the copy by position
    for n in ast.walk(new_tree):
        if (type(n) == type(target_node)
            and getattr(n, "lineno", -1) == getattr(target_node, "lineno", -2)
            and getattr(n, "col_offset", -1) == getattr(target_node, "col_offset", -2)):
            mutate_fn(n)
            break
    return new_tree


# ---- top-level counter ----
def count_mutants(source: str) -> dict:
    """Count candidate mutants produced by all 7 operators, with BM/CR precedence."""
    tree = ast.parse(source)
    bm_mutants, boundary_ids = _bm(tree)
    counts = {
        "AOR": len(_aor(tree)),
        "ROR": len(_ror(tree)),
        "LOR": len(_lor(tree)),
        "CR":  len(_cr(tree, boundary_ids)),
        "BM":  len(bm_mutants),
        "SDL": len(_sdl(tree)),
        "RSM": len(_rsm(tree)),
    }
    counts["TOTAL"] = sum(v for k, v in counts.items() if k != "TOTAL")
    return counts


if __name__ == "__main__":
    # Demo on one template instance
    t = load_template(ROOT / "L2" / "L2-classifier-001.py")
    r = instantiate(t, 42)
    print(r["source"])
    print("Mutant counts:", count_mutants(r["source"]))
