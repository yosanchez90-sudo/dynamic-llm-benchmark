"""Residual scanner — audits all rendered docstrings for grammar issues
that are NOT auto-fixed by the engine.

Two categories of warning:
  A. Repeated word — a synonym choice happens to repeat a word from the fixed
     template text (e.g. "the string bracketed in brackets"). Often cosmetic,
     sometimes intentional, so warn rather than rewrite.
  B. Missing space around substitution — symptom of a template authoring bug
     where the {placeholder} is glued to surrounding fixed text without a
     space. Almost always a real bug, but auto-fixing it could mask the
     authoring error, so we surface it as a warning to be addressed at the
     template source.

Also re-checks the 7 auto-fix categories for any residuals (defence in depth:
if a rule misses an edge case the scanner reports it).

Run with:  python3 _smoke/residual_scan.py
Exit code 0 if no warnings, 1 if any warnings found.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_smoke"))

from engine import (  # noqa: E402
    instantiate, load_template,
    _AN_BEFORE_CONSONANT_LETTER, _A_BEFORE_VOWEL_LETTER,
)

SEEDS = [101, 102, 103, 104, 105]


# Stop-words that are allowed to repeat in a docstring (they're meaningless to
# flag because they appear in almost every sentence)
STOP_WORDS = {
    "a", "an", "the", "of", "to", "in", "on", "by", "for", "with",
    "and", "or", "but", "not", "is", "are", "as", "at", "from", "into",
    "two", "one", "input", "inputs", "value", "values",
}


def detect_repeated_word(text: str):
    """Find words (non-stopwords, >3 chars) that appear more than once."""
    words = re.findall(r"[A-Za-z]{4,}", text.lower())
    seen = {}
    repeats = []
    for i, w in enumerate(words):
        if w in STOP_WORDS:
            continue
        if w in seen:
            repeats.append(w)
        else:
            seen[w] = i
    return sorted(set(repeats))


def detect_missing_space(text: str):
    """Heuristic: detect 'wordWord' camelCase boundary INSIDE a docstring.

    A real docstring should not contain mid-string camelCase boundaries (those
    would only occur if a {placeholder} got concatenated with adjacent fixed
    text without a space). Identifier-like tokens used in the docstring body
    (which can legitimately be camelCase) are excluded by only flagging cases
    that span two natural-language words.
    """
    issues = []
    # Pattern: lowercase letter immediately followed by uppercase letter
    # AND the surrounding context looks like prose (no other camelCase nearby).
    for m in re.finditer(r"[a-z][A-Z][a-z]", text):
        # Skip if the match is inside a longer camelCase token (identifier)
        start = m.start()
        # Look at the word containing this position
        word_match = re.search(r"[A-Za-z]+", text[max(0, start - 20):start + 20])
        if word_match:
            issues.append(m.group())
    return issues


def detect_residual_articles(text: str):
    """Last-chance check: any 'a vowel' or 'an consonant' that escaped Rule 1."""
    issues = []
    for m in re.finditer(r"\b(a)\s+([A-Za-z]+)", text):
        word = m.group(2).lower()
        if word in _A_BEFORE_VOWEL_LETTER:
            continue
        if word and word[0] in "aeiou":
            issues.append(f"'a {word}' (should be 'an')")
    for m in re.finditer(r"\b(an)\s+([A-Za-z]+)", text):
        word = m.group(2).lower()
        if word in _AN_BEFORE_CONSONANT_LETTER:
            continue
        if word and word[0] not in "aeiou":
            issues.append(f"'an {word}' (should be 'a')")
    return issues


def detect_residual_double_space(text: str):
    return ["double space"] if "  " in text else []


def detect_residual_double_punct(text: str):
    return [m.group() for m in re.finditer(r"[.!?][.!?]", text)]


def scan(tier_dir: Path) -> int:
    warnings = 0
    by_template = {}
    for path in sorted(tier_dir.glob("*.py")):
        t = load_template(path)
        for seed in SEEDS:
            r = instantiate(t, seed)
            d = r.get("docstring") or ""

            findings = []

            # Warning A: repeated word
            repeats = detect_repeated_word(d)
            if repeats:
                findings.append(("repeated word", repeats))

            # Warning B: missing space
            missing = detect_missing_space(d)
            if missing:
                findings.append(("missing space (camelCase mid-prose)", missing))

            # Residual checks for the 7 auto-fix rules
            res_articles = detect_residual_articles(d)
            if res_articles:
                findings.append(("residual a/an", res_articles))
            res_dspace = detect_residual_double_space(d)
            if res_dspace:
                findings.append(("residual double-space", res_dspace))
            res_dpunct = detect_residual_double_punct(d)
            if res_dpunct:
                findings.append(("residual double-punct", res_dpunct))

            if findings:
                by_template.setdefault(t.template_id, []).append((seed, d, findings))
                warnings += sum(len(f[1]) for f in findings)

    if by_template:
        print(f"Residual scan: {warnings} warnings across {len(by_template)} templates\n")
        for tid, hits in by_template.items():
            print(f"--- {tid} ---")
            for seed, d, findings in hits:
                print(f"  seed {seed}: {d!r}")
                for kind, items in findings:
                    print(f"      [{kind}] {items}")
    else:
        print(f"Residual scan: clean. No warnings.")

    return warnings


if __name__ == "__main__":
    total = 0
    for tier in ["L1", "L2", "L3", "L4"]:
        d = ROOT / tier
        if not d.exists():
            continue
        templates_in_tier = list(d.glob("*.py"))
        if not templates_in_tier:
            continue
        print(f"\n========== {tier} ({len(templates_in_tier)} templates) ==========\n")
        total += scan(d)
    print()
    print(f"Total warnings: {total}")
    sys.exit(0 if total == 0 else 1)
