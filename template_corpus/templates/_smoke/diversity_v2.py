"""Diversity sweep v2 - implements the new union-of-four diversity check from
the updated spec section 3.2.5.

Four measures per pair of instances:
  - BLEU-4 (real, via sacrebleu)
  - Embedding cosine of docstrings (TF-IDF stand-in here; production HPC run
    swaps to a small sentence-transformer model per the spec)
  - Identifier Jaccard
  - Body-line Jaccard

Aggregation per template: all-pairs mean (10 pairs) + all-pairs max for flagging.
Flag rule: max of any measure > 0.80.
"""
import ast
import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TEMPLATES_ROOT))
sys.path.insert(0, str(TEMPLATES_ROOT / "_smoke"))

from engine import instantiate, load_template  # noqa: E402

# ---- BLEU-4 ----
try:
    import sacrebleu
    HAVE_SACREBLEU = True
except ImportError:
    HAVE_SACREBLEU = False


def bleu4(a: str, b: str) -> float:
    """BLEU-4 score of a against b as the single reference, [0, 1]."""
    if not HAVE_SACREBLEU:
        return _bleu4_fallback(a, b)
    if not a.strip() or not b.strip():
        return 0.0
    score = sacrebleu.sentence_bleu(a, [b]).score / 100.0
    return float(score)


def _bleu4_fallback(a: str, b: str) -> float:
    wa = a.lower().split()
    wb = b.lower().split()
    if len(wa) < 4 or len(wb) < 4:
        sa, sb = set(wa), set(wb)
        return len(sa & sb) / max(1, len(sa | sb))
    grams_a = {tuple(wa[i:i + 4]) for i in range(len(wa) - 3)}
    grams_b = {tuple(wb[i:i + 4]) for i in range(len(wb) - 3)}
    return len(grams_a & grams_b) / max(1, len(grams_a | grams_b))


# ---- embedding cosine ----
# Production: a sentence-transformer model loaded once.
# Phase 2 validation here: TF-IDF cosine over docstring word tokens.
# The interface is the same so swapping is trivial.

_VOCAB_CACHE = None


def _docs_to_vocab(docs):
    vocab = set()
    for d in docs:
        vocab.update(_tokenise(d))
    return sorted(vocab)


def _tokenise(text: str):
    return re.findall(r"[A-Za-z]+", text.lower())


def _idf(docs):
    df = Counter()
    for d in docs:
        for w in set(_tokenise(d)):
            df[w] += 1
    n = len(docs)
    return {w: 1 + (n / (1 + c)) ** 0.5 for w, c in df.items()}


def _tfidf_vec(doc, idf):
    tf = Counter(_tokenise(doc))
    return {w: tf[w] * idf.get(w, 0.0) for w in tf}


def _cos(va, vb):
    keys = set(va) | set(vb)
    dot = sum(va.get(k, 0.0) * vb.get(k, 0.0) for k in keys)
    na = (sum(v * v for v in va.values())) ** 0.5
    nb = (sum(v * v for v in vb.values())) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def embed_cosine_batch(docstrings):
    """Compute pairwise cosine similarities across all docstrings.

    Returns a list of cosines, one per pair, in itertools.combinations order.
    Stand-in for production sentence-transformer embedding; deterministic.
    """
    idf = _idf(docstrings)
    vecs = [_tfidf_vec(d, idf) for d in docstrings]
    return [_cos(vecs[i], vecs[j]) for i, j in combinations(range(len(docstrings)), 2)]


# ---- Jaccard ----
def jaccard(sa: set, sb: set) -> float:
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(1, len(sa | sb))


def identifier_set(source: str):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.arg):
            out.add(node.arg)
        elif isinstance(node, ast.FunctionDef):
            out.add(node.name)
    return out


def body_line_set(source: str):
    return {
        ln.strip() for ln in source.splitlines()
        if ln.strip() and not ln.strip().startswith('"""')
    }


# ---- per-template aggregation ----
SEEDS = [101, 102, 103, 104, 105]

# Threshold policy (locked in conversation, < 14 words):
#   - Code-level measures (identifier Jaccard, body-line Jaccard) flag at > 0.80 always.
#   - Docstring-level measures (BLEU-4, embedding cosine) flag at > 0.80 when the
#     mean docstring length is >= 14 words, and at > 0.95 when it is < 14 words.
# Rationale: BLEU-4 and short-text embedding cosine have an inherent similarity
# floor for docstrings under ~14 words because the n-gram count is too small to
# discriminate paraphrases from duplicates. Relaxing the docstring threshold
# below this cutoff prevents the measure-too-strict effect from inflating the
# flag rate at L1, where docstrings are naturally short. Above the cutoff the
# strict 0.80 threshold applies as originally specified.
CODE_FLAG_THRESHOLD = 0.80
DOC_FLAG_THRESHOLD_LONG = 0.80   # applied when mean docstring words >= 14
DOC_FLAG_THRESHOLD_SHORT = 0.95  # applied when mean docstring words < 14
SHORT_DOC_CUTOFF_WORDS = 14


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z]+", text))


def diversity_for_template(template):
    instances = [instantiate(template, s) for s in SEEDS]
    docstrings = [i.get("docstring") or "" for i in instances]
    sources    = [i.get("source") or "" for i in instances]
    id_sets    = [identifier_set(s) for s in sources]
    body_sets  = [body_line_set(s) for s in sources]

    pair_indices = list(combinations(range(len(SEEDS)), 2))
    pair_seeds   = [(SEEDS[i], SEEDS[j]) for i, j in pair_indices]

    bleu_vals = [bleu4(docstrings[i], docstrings[j]) for i, j in pair_indices]
    cos_vals  = embed_cosine_batch(docstrings)
    id_vals   = [jaccard(id_sets[i], id_sets[j]) for i, j in pair_indices]
    body_vals = [jaccard(body_sets[i], body_sets[j]) for i, j in pair_indices]

    def stats(vals, seeds):
        max_val = max(vals)
        max_idx = vals.index(max_val)
        return {
            "mean": round(sum(vals) / len(vals), 3),
            "max":  round(max_val, 3),
            "max_pair": seeds[max_idx],
        }

    bleu = stats(bleu_vals, pair_seeds)
    cos  = stats(cos_vals, pair_seeds)
    idj  = stats(id_vals, pair_seeds)
    bod  = stats(body_vals, pair_seeds)

    # Length-aware threshold selection
    mean_doc_words = round(
        sum(_word_count(d) for d in docstrings) / len(docstrings), 1
    )
    is_short = mean_doc_words < SHORT_DOC_CUTOFF_WORDS
    doc_thresh = DOC_FLAG_THRESHOLD_SHORT if is_short else DOC_FLAG_THRESHOLD_LONG

    flagged = (bleu["max"] > doc_thresh
               or cos["max"]  > doc_thresh
               or idj["max"]  > CODE_FLAG_THRESHOLD
               or bod["max"]  > CODE_FLAG_THRESHOLD)

    flag_source = None
    if flagged:
        # Pick the single highest violator that exceeds its applicable threshold
        violators = []
        if bleu["max"] > doc_thresh:
            violators.append(("bleu4", bleu["max"]))
        if cos["max"] > doc_thresh:
            violators.append(("embed_cos", cos["max"]))
        if idj["max"] > CODE_FLAG_THRESHOLD:
            violators.append(("id_jaccard", idj["max"]))
        if bod["max"] > CODE_FLAG_THRESHOLD:
            violators.append(("body_jaccard", bod["max"]))
        flag_source = max(violators, key=lambda v: v[1])[0]

    return {
        "bleu4_mean":         bleu["mean"],
        "bleu4_max":          bleu["max"],
        "embed_cos_mean":     cos["mean"],
        "embed_cos_max":      cos["max"],
        "id_jaccard_mean":    idj["mean"],
        "id_jaccard_max":     idj["max"],
        "body_jaccard_mean":  bod["mean"],
        "body_jaccard_max":   bod["max"],
        "mean_doc_words":     mean_doc_words,
        "doc_threshold_applied": doc_thresh,
        "flagged":            flagged,
        "flag_source":        flag_source,
        "flagged_pair":       (bleu["max_pair"] if flag_source == "bleu4" else
                               cos["max_pair"]  if flag_source == "embed_cos" else
                               idj["max_pair"]  if flag_source == "id_jaccard" else
                               bod["max_pair"]  if flag_source == "body_jaccard" else
                               None),
    }


def main():
    print("Diversity sweep v2 (union of 4 measures, all-pairs aggregation)")
    print(f"BLEU-4 backend: {'sacrebleu' if HAVE_SACREBLEU else 'fallback (4-gram Jaccard)'}")
    print(f"Embedding backend: TF-IDF cosine stand-in (production HPC: sentence-transformers)")
    print(f"Flag rule: code measures > {CODE_FLAG_THRESHOLD}; "
          f"docstring measures > {DOC_FLAG_THRESHOLD_LONG} (>= {SHORT_DOC_CUTOFF_WORDS} words) "
          f"or > {DOC_FLAG_THRESHOLD_SHORT} (< {SHORT_DOC_CUTOFF_WORDS} words)")
    print()

    results = {}
    by_tier = {"L1": [], "L2": [], "L3": [], "L4": []}
    for tier in ["L1", "L2", "L3", "L4"]:
        tdir = ROOT / tier
        if not tdir.exists():
            continue
        for path in sorted(tdir.glob("*.py")):
            t = load_template(path)
            div = diversity_for_template(t)
            div["template_id"] = t.template_id
            div["tier"] = tier
            results[t.template_id] = div
            by_tier[tier].append(div)

    out = ROOT / "_smoke" / "diversity_v2.json"
    out.write_text(json.dumps(results, indent=2, default=str))

    print(f"{'Template':<25} {'Doc len':<9} {'Doc thr':<9} {'BLEU max':<10} {'Embed max':<11} {'ID max':<8} {'Body max':<10} {'Flagged?':<22}")
    print("-" * 115)
    for tier in ["L1", "L2", "L3", "L4"]:
        if not by_tier[tier]:
            continue
        for d in by_tier[tier]:
            flag = f"YES ({d['flag_source']})" if d["flagged"] else "no"
            print(f"{d['template_id']:<25} "
                  f"{d['mean_doc_words']:<9} "
                  f"{d['doc_threshold_applied']:<9} "
                  f"{d['bleu4_max']:<10} "
                  f"{d['embed_cos_max']:<11} "
                  f"{d['id_jaccard_max']:<8} "
                  f"{d['body_jaccard_max']:<10} "
                  f"{flag}")

    print()
    for tier in ["L1", "L2", "L3", "L4"]:
        recs = by_tier[tier]
        if not recs:
            continue
        flagged = sum(1 for r in recs if r["flagged"])
        print(f"{tier}: {len(recs)} templates, {flagged} flagged ({flagged}/{len(recs)})")
    print(f"\nReport written to {out}")


if __name__ == "__main__":
    main()
