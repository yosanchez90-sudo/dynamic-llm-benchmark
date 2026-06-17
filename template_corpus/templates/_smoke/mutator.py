"""Mutation engine — 7 SAC operators, public API: generate_mutants(source_str).

Upgraded from Phase 2 prototype (counted sites, returned AST nodes / marker
tuples) to a production-ready implementation that returns runnable source
strings for every mutant.

Three categories of change vs the prototype:
  1. _apply() now returns ast.unparse(mutated_tree) — a source string — so AOR,
     ROR, LOR(bool), CR, BM automatically produce runnable mutants.
  2. _sdl() and _rsm() were stubs returning ("SDL", node) / ("RSM", node) marker
     tuples.  Both are now real implementations that produce source strings.
  3. _lor() not-removal was a counting stub.  It now uses a NodeTransformer to
     actually replace `not x` with `x` in the tree copy.

Public API:
  generate_mutants(source: str) -> list[Mutant]
      Each Mutant has .source (valid Python string) and .operator (one of the
      seven SAC operator names).  Raises if source does not parse.

  count_mutants(source: str) -> dict
      Backward-compatible wrapper used by mutation_sweep.py.
"""
import ast
import copy
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_smoke"))

from engine import instantiate, load_template  # noqa: E402


@dataclass
class Mutant:
    """One runnable mutant: a source string and the operator that produced it."""
    source: str
    operator: str


# ---- helpers ----

def _node_in_boundary_context(node, parents):
    """Is this ast.Constant in a range arg, subscript, or Compare operand?"""
    if not isinstance(node, ast.Constant) or not isinstance(node.value, int):
        return False
    if not parents:
        return False
    parent = parents[-1]
    if isinstance(parent, ast.Call):
        if isinstance(parent.func, ast.Name) and parent.func.id == "range":
            return True
    if isinstance(parent, (ast.Subscript, ast.Slice, ast.Compare)):
        return True
    return False


def _walk_with_parents(tree):
    """Yield (node, parent_chain) for every node in the tree."""
    def _walk(node, parents):
        yield node, parents
        for child in ast.iter_child_nodes(node):
            yield from _walk(child, parents + [node])
    yield from _walk(tree, [])


def _apply(tree, target_node, mutate_fn) -> str:
    """Deep-copy tree, find target_node by position, apply mutate_fn, return source.

    The returned string is always valid Python because the only change is the
    single in-place mutation; ast.unparse() handles re-serialisation.
    """
    new_tree = copy.deepcopy(tree)
    for n in ast.walk(new_tree):
        if (type(n) is type(target_node)
                and getattr(n, "lineno", -1) == getattr(target_node, "lineno", -2)
                and getattr(n, "col_offset", -1) == getattr(target_node, "col_offset", -2)):
            mutate_fn(n)
            break
    ast.fix_missing_locations(new_tree)
    return ast.unparse(new_tree)


# ---- operator implementations ----

def _aor(tree) -> list[Mutant]:
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
    mutants = []
    for node, _ in _walk_with_parents(tree):
        if isinstance(node, ast.BinOp) and type(node.op) in repl:
            for r in repl[type(node.op)]:
                src = _apply(tree, node, lambda nn, R=r: setattr(nn, "op", R()))
                mutants.append(Mutant(src, "AOR"))
    return mutants


def _ror(tree) -> list[Mutant]:
    """Relational Operator Replacement."""
    repl = {
        ast.Lt:    [ast.LtE, ast.Gt, ast.Eq],
        ast.LtE:   [ast.Lt,  ast.GtE, ast.NotEq],
        ast.Gt:    [ast.GtE, ast.Lt, ast.Eq],
        ast.GtE:   [ast.Gt,  ast.LtE, ast.NotEq],
        ast.Eq:    [ast.NotEq],
        ast.NotEq: [ast.Eq],
    }
    mutants = []
    for node, _ in _walk_with_parents(tree):
        if isinstance(node, ast.Compare):
            for idx, op in enumerate(node.ops):
                if type(op) in repl:
                    for r in repl[type(op)]:
                        src = _apply(tree, node,
                                     lambda nn, I=idx, R=r: nn.ops.__setitem__(I, R()))
                        mutants.append(Mutant(src, "ROR"))
    return mutants


def _lor(tree) -> list[Mutant]:
    """Logical Operator Replacement.

    Two sub-cases:
      bool-swap: and <-> or  (handled by _apply like AOR/ROR)
      not-removal: `not x` -> `x`  (requires replacing a node with its child,
                  so uses a NodeTransformer rather than _apply)
    """
    mutants = []
    for node, _ in _walk_with_parents(tree):
        if isinstance(node, ast.BoolOp):
            new_op = ast.Or if isinstance(node.op, ast.And) else ast.And
            src = _apply(tree, node, lambda nn, O=new_op: setattr(nn, "op", O()))
            mutants.append(Mutant(src, "LOR"))

        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            target_line = getattr(node, "lineno", -1)
            target_col = getattr(node, "col_offset", -1)

            class _NotRemover(ast.NodeTransformer):
                def __init__(self):
                    self.applied = False

                def visit_UnaryOp(self, n):
                    self.generic_visit(n)
                    if (not self.applied
                            and isinstance(n.op, ast.Not)
                            and getattr(n, "lineno", -1) == target_line
                            and getattr(n, "col_offset", -1) == target_col):
                        self.applied = True
                        return n.operand
                    return n

            remover = _NotRemover()
            new_tree = remover.visit(copy.deepcopy(tree))
            if remover.applied:
                ast.fix_missing_locations(new_tree)
                mutants.append(Mutant(ast.unparse(new_tree), "LOR"))

    return mutants


def _cr(tree, boundary_node_ids: set) -> list[Mutant]:
    """Constant Replacement (excludes boundary sites handled by BM)."""
    mutants = []
    for node, _ in _walk_with_parents(tree):
        if not isinstance(node, ast.Constant) or id(node) in boundary_node_ids:
            continue
        v = node.value
        if isinstance(v, bool):
            src = _apply(tree, node, lambda nn, V=not v: setattr(nn, "value", V))
            mutants.append(Mutant(src, "CR"))
        elif isinstance(v, int):
            for new in {0, 1, -v if v != 0 else 1}:
                if new != v:
                    src = _apply(tree, node, lambda nn, V=new: setattr(nn, "value", V))
                    mutants.append(Mutant(src, "CR"))
        elif isinstance(v, float):
            for new in {0.0, 1.0}:
                if new != v:
                    src = _apply(tree, node, lambda nn, V=new: setattr(nn, "value", V))
                    mutants.append(Mutant(src, "CR"))
    return mutants


def _bm(tree) -> tuple[list[Mutant], set]:
    """Boundary Mutation — int literals in boundary contexts only.

    Returns (mutants, boundary_node_ids) so _cr can exclude those sites.
    """
    mutants = []
    boundary_ids: set = set()
    for node, parents in _walk_with_parents(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, int):
            continue
        if _node_in_boundary_context(node, parents):
            boundary_ids.add(id(node))
            for delta in (+1, -1):
                new_val = node.value + delta
                src = _apply(tree, node, lambda nn, V=new_val: setattr(nn, "value", V))
                mutants.append(Mutant(src, "BM"))
    return mutants, boundary_ids


def _sdl(tree) -> list[Mutant]:
    """Statement Deletion — remove one safe statement, leaving valid Python.

    Safe statements: assignments (Assign, AugAssign, AnnAssign) and expression
    statements whose value is a Call.  Return statements are excluded because
    deleting the only return would break the function contract.

    If deletion would leave an empty block, a `pass` statement is inserted.
    """
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
    if fn is None:
        return []

    # Collect (lineno, col_offset) of each deletable statement
    sites = []
    for stmt in ast.walk(fn):
        if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            sites.append((getattr(stmt, "lineno", -1), getattr(stmt, "col_offset", -1)))
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            sites.append((getattr(stmt, "lineno", -1), getattr(stmt, "col_offset", -1)))

    mutants = []
    for target_line, target_col in sites:
        new_tree = copy.deepcopy(tree)
        deleted = [False]

        def _del_from(stmts: list) -> list:
            if deleted[0]:
                return stmts
            for i, s in enumerate(stmts):
                if (getattr(s, "lineno", -1) == target_line
                        and getattr(s, "col_offset", -1) == target_col):
                    remaining = stmts[:i] + stmts[i + 1:]
                    if not remaining:
                        placeholder = ast.Pass()
                        ast.fix_missing_locations(placeholder)
                        remaining = [placeholder]
                    deleted[0] = True
                    return remaining
            return stmts

        for node in ast.walk(new_tree):
            for attr in ("body", "orelse", "finalbody", "handlers"):
                stmts = getattr(node, attr, None)
                if isinstance(stmts, list):
                    setattr(node, attr, _del_from(stmts))

        if deleted[0]:
            ast.fix_missing_locations(new_tree)
            mutants.append(Mutant(ast.unparse(new_tree), "SDL"))

    return mutants


def _rsm(tree) -> list[Mutant]:
    """Return-Statement Mutation — replace each return value with None."""
    sites = []
    for node, _ in _walk_with_parents(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            sites.append((getattr(node, "lineno", -1), getattr(node, "col_offset", -1)))

    mutants = []
    for target_line, target_col in sites:
        new_tree = copy.deepcopy(tree)
        for node in ast.walk(new_tree):
            if (isinstance(node, ast.Return)
                    and getattr(node, "lineno", -1) == target_line
                    and getattr(node, "col_offset", -1) == target_col
                    and node.value is not None):
                node.value = ast.Constant(value=None)
                ast.fix_missing_locations(new_tree)
                break
        mutants.append(Mutant(ast.unparse(new_tree), "RSM"))

    return mutants


# ---- public API ----

def generate_mutants(source: str) -> list[Mutant]:
    """Generate all candidate mutants for a source string.

    Every returned Mutant has:
      .source   — a complete, valid Python source string (ast.parse() will not raise)
      .operator — one of: AOR, ROR, LOR, CR, BM, SDL, RSM

    Raises SyntaxError if `source` does not parse.
    """
    tree = ast.parse(source)
    bm_mutants, boundary_ids = _bm(tree)

    mutants: list[Mutant] = []
    mutants.extend(_aor(tree))
    mutants.extend(_ror(tree))
    mutants.extend(_lor(tree))
    mutants.extend(_cr(tree, boundary_ids))
    mutants.extend(bm_mutants)
    mutants.extend(_sdl(tree))
    mutants.extend(_rsm(tree))
    return mutants


def count_mutants(source: str) -> dict:
    """Count candidate mutants by operator.  Backward-compatible with mutation_sweep.py."""
    counts = {op: 0 for op in ("AOR", "ROR", "LOR", "CR", "BM", "SDL", "RSM")}
    for m in generate_mutants(source):
        counts[m.operator] += 1
    counts["TOTAL"] = sum(v for k, v in counts.items() if k != "TOTAL")
    return counts


if __name__ == "__main__":
    t = load_template(ROOT / "L2" / "L2-classifier-001.py")
    r = instantiate(t, 42)
    print(r["source"])
    muts = generate_mutants(r["source"])
    print(f"\n{len(muts)} mutants:")
    for op in ("AOR", "ROR", "LOR", "CR", "BM", "SDL", "RSM"):
        n = sum(1 for m in muts if m.operator == op)
        print(f"  {op}: {n}")
    print("\nVerifying all mutants parse...")
    for m in muts:
        ast.parse(m.source)
    print("All parse cleanly.")
    print("\nFirst AOR mutant source:")
    first_aor = next((m for m in muts if m.operator == "AOR"), None)
    if first_aor:
        print(first_aor.source)
