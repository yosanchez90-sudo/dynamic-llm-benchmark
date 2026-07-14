# Diversity flag-rule thresholds (locked policy)

Source: `template_corpus/templates/_smoke/diversity_v2.py` (verbatim policy comment).

- Code-level measures (identifier Jaccard, body-line Jaccard): flag at max-pair value > 0.80, always.
- Docstring-level measures (BLEU-4, embedding cosine): flag at max-pair value > 0.80 when the
  template's mean docstring length is >= 14 words, and > 0.95 when it is < 14 words.

Rationale: BLEU-4 and short-text embedding cosine have an inherent similarity floor for
docstrings under ~14 words (too few n-grams to discriminate paraphrase from duplicate).
The relaxed threshold below the cutoff prevents this measure-too-strict effect from
inflating the flag rate at L1, where docstrings are naturally short.

Aggregation: all-pairs mean + max across the 5 fixed instantiation seeds (101-105),
i.e. C(5,2) = 10 pairs per template. A template is flagged if *any* single pair on
*any* measure crosses its applicable threshold.

BLEU-4 backend: real `sacrebleu` (added as a project dependency this run — prior
runs before 2026-07-14 silently fell back to a 4-gram Jaccard approximation because
sacrebleu was not installed).

Embedding backend: TF-IDF cosine over docstring tokens — documented in diversity_v2.py
as the intentional Phase 2 validation stand-in for a production sentence-transformer
model; not a gap to close for this gate.
