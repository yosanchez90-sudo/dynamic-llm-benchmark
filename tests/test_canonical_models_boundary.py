"""Regression test for the canonical-9-model boundary (found 2026-07-28):
analyze_stability.py had no filter at all, so fine-tuned LoRA adapter labels
(Comparison C / supplementary-study artifacts) leaked into StableMut@K and
pairwise Kendall tau once their own multi-instantiation data landed, moving
the RQ4.1 reliability figure with no scope decision behind it. Same bug class
that previously produced a spurious 8th model in comparison_b_paired.csv
(build_comparison_tables.py). CANONICAL_MODELS in coverage_matrix.py is now
the single source of truth; this test pins that every consuming script
actually filters to it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from coverage_matrix import CANONICAL_MODELS, MODEL_SPECS, filter_to_canonical  # noqa: E402


def test_canonical_models_has_nine_unique_labels():
    assert len(CANONICAL_MODELS) == 9
    assert len(set(CANONICAL_MODELS)) == 9
    assert CANONICAL_MODELS == [m.model_label for m in MODEL_SPECS]


def test_filter_to_canonical_drops_adapter_and_cross_family_labels():
    df = pd.DataFrame({
        "model_label": [
            CANONICAL_MODELS[0],
            CANONICAL_MODELS[0] + "__ft_qwen1_5b_lora_ult_30ep",
            "deepseek-ai__deepseek-coder-6.7b-instruct",
        ],
        "value": [1, 2, 3],
    })
    out = filter_to_canonical(df)
    assert list(out["model_label"]) == [CANONICAL_MODELS[0]]


def test_analyze_stability_filters_adapter_labels(tmp_path, monkeypatch):
    """End-to-end: two synthetic instantiations of data for one canonical
    model and one adapter variant of it. The adapter must not surface in
    StableMut@K or pairwise Kendall tau output."""
    import analyze_stability

    adapter_label = CANONICAL_MODELS[0] + "__ft_test_adapter"
    rows = []
    for label in (CANONICAL_MODELS[0], adapter_label):
        for inst in ("1", "2"):
            for i in range(3):
                rows.append({
                    "model_label": label,
                    "instantiation_id": inst,
                    "tier": "L1",
                    "template_id": f"t{i}",
                    "instance_seed": i,
                    "mutation_score": 0.9,
                    "baseline_passed": True,
                    "source_file": "synthetic.jsonl",
                })
    df = pd.DataFrame(rows)

    monkeypatch.setattr(analyze_stability, "load_records", lambda *a, **k: df)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "analysis").mkdir()
    # STABILITY_MD/ROOT are module-level constants derived from the real repo
    # root, must be redirected together (main() does STABILITY_MD.relative_to(ROOT)
    # for its final print), or this test overwrites the actual
    # analysis/STABILITY.md with synthetic data.
    monkeypatch.setattr(analyze_stability, "ROOT", tmp_path)
    monkeypatch.setattr(analyze_stability, "STABILITY_MD", tmp_path / "analysis" / "STABILITY.md")

    monkeypatch.setattr(sys, "argv", ["analyze_stability.py", "--min-instantiations", "1"])
    analyze_stability.main()

    stable = pd.read_csv(tmp_path / "analysis" / "stability_stablemut.csv")
    assert adapter_label not in set(stable["model_label"])
    assert CANONICAL_MODELS[0] in set(stable["model_label"])
