"""Single-command registry for regenerating this project's thesis-facing
analysis tables and figures. Each entry is a no-argument script that reads
whatever result files currently exist on disk and (re)writes its own
analysis/*.csv, analysis/*.md, and/or analysis/figures/* outputs. All of
these are regenerable (see each script's own docstring for its specific
"safe to re-run any time" note) and gitignored except the provenance/
interpretation .md files. One entry (research_questions_md) instead
mirrors docs/Research_questions.xlsx to docs/RESEARCH_QUESTIONS.md, same
no-argument/reads-current-disk-state/safe-to-rerun shape, different output
directory since it tracks a hand-maintained reference doc, not a
generated analysis table.

Excludes scripts that take required CLI arguments and are
invoked once per condition, not once per thesis asset (e.g.
scripts/plot_epoch_perf.py, one call per fine-tune condition;
scripts/build_ult_training_pairs.py / build_onset_curve_manifest.py /
build_comparison_c_seen_manifest.py, one-off data-preparation steps that
freeze a manifest, not regenerate a thesis table/figure). Those
stay manual, invoked directly per their own usage docstring.

Usage:
    python scripts/build_thesis_assets.py            # run every registered step
    python scripts/build_thesis_assets.py --only rq5 comparison_c   # run a subset
    python scripts/build_thesis_assets.py --list      # show registered steps
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

# (key, script path, description), run in this order; later steps don't
# depend on earlier ones completing successfully, each runs regardless.
STEPS: list[tuple[str, str, str]] = [
    ("comparison_ab", "scripts/build_comparison_tables.py",
     "Comparison A (Dynamic-L4 vs ULT) + Comparison B (ULT vs PLT)"),
    ("stability", "scripts/analyze_stability.py",
     "StableMut@K + pairwise Kendall tau (RQ4.1)"),
    ("finetune_endpoint", "scripts/build_finetune_endpoint_table.py",
     "Supplementary study endpoint table (greedy + R=3 sampling)"),
    ("finetune_decline", "scripts/build_finetune_decline_table.py",
     "Supplementary study held-out exec_rate decline table (epoch 0 vs 30)"),
    ("comparison_c", "scripts/analyze_comparison_c.py",
     "Comparison C canonical 2x3 DiD + gradient + Mut@K tables"),
    ("comparison_c_figure", "scripts/plot_comparison_c_onset_curve.py",
     "Comparison C onset-curve figure (baseline-pass + verbatim-match)"),
    ("rq5", "scripts/analyze_rq5.py",
     "RQ5/H6 model-ranking table + cross-benchmark correlations"),
    ("rq5_figure", "scripts/plot_rq5_correlation.py",
     "RQ5 correlation scatter figure(s)"),
    ("rq5_diagnostics", "scripts/analyze_rq5_diagnostics.py",
     "RQ5 post-hoc diagnostics (tier-matching, discrimination, conditioning, attenuation)"),
    ("rq5_cross_family", "scripts/analyze_rq5_cross_family.py",
     "RQ5 cross-family extension: canonical-only vs +4-family correlations"),
    ("rq5_cross_family_figure", "scripts/plot_rq5_cross_family_correlation.py",
     "RQ5 cross-family correlation scatter figure(s)"),
    ("rq5_sanitizer_sensitivity", "scripts/analyze_rq5_sanitizer_sensitivity.py",
     "RQ5 sanitizer-repair sensitivity (per-model repair fraction, with/without repaired rows)"),
    ("h3_tier_gradient", "scripts/analyze_h3_tier_gradient.py",
     "H3/RQ2 tier gradient: per-model + pooled Spearman rho, Holm-corrected"),
    ("h3_tier_effect_figure", "scripts/plot_h3_tier_effect.py",
     "H3 tier-effect figure: conditional Mut@K by tier, one line per canonical model"),
    ("h5_stability_figure", "scripts/plot_h5_stability.py",
     "H5 stability figure: StableMut@K mean +/- SD per canonical model"),
    ("ranking_matrix", "scripts/build_ranking_matrix.py",
     "Metric-agnostic ranking matrix: exec_rate/baseline_pass_rate/Mut@K/coverage-adjusted side by side"),
    ("ranking_matrix_heatmap_figure", "scripts/plot_ranking_matrix_heatmap.py",
     "Ranking matrix heatmap figure (Kendall tau by metric x benchmark pair, Holm-marked)"),
    ("noise_floor_figure", "scripts/plot_noise_floor.py",
     "Noise floor by metric and Dynamic tier figure"),
    ("collapse_vs_survival_figure", "scripts/plot_collapse_vs_survival.py",
     "Collapse vs survival figure (raw vs coverage-adjusted Mut@K at n=3 vs n=7)"),
    ("flow_diagram_figure", "scripts/plot_flow_diagram.py",
     "End-to-end pipeline flow diagram (template to hypothesis test), for the "
     "supporting report and slide deck -- structural, not data-derived"),
    ("contamination_loop_figure", "scripts/plot_contamination_loop.py",
     "Three-step contamination-loop diagram, for the slide deck -- structural, not data-derived"),
    ("execution_evidence_figure", "scripts/plot_execution_evidence.py",
     "Real, live-captured execution evidence (test suite, citation gate, SLURM job "
     "accounting) for the supporting report -- structural, not data-derived"),
    ("research_questions_md", "scripts/build_research_questions_md.py",
     "docs/RESEARCH_QUESTIONS.md: diffable markdown mirror of docs/Research_questions.xlsx"),
    ("paper_bib", "scripts/build_paper_bib.py",
     "paper/references.bib: generated from paper/references.yaml"),
    ("paper_table1", "scripts/build_paper_table1.py",
     "paper/table1.tex: compact hypothesis/prediction/verdict table, read live from docs/Research_questions.xlsx"),
    ("paper_results_table", "scripts/build_paper_results_table.py",
     "paper/table_results.tex: main descriptive results table (9 models x DyMuT/ULT), read live from analysis/ranking_matrix_scores.csv"),
    ("test_suite_count", "scripts/count_test_suite.py",
     "analysis/test_suite_count.csv: live `pytest --collect-only` count, "
     "so the supporting report's \"N tests\" claim can't silently drift"),
    ("paper_values", "scripts/build_paper_values.py",
     "paper/values.tex: every quantitative value the paper cites, as LaTeX "
     "macros read live from analysis/*.csv"),
    ("supporting_report_docx", "scripts/build_supporting_report_docx.py",
     "paper/supporting_report/SUPPORTING_REPORT.docx: formatted from the "
     "citation-gated markdown source, paper/supporting_report/REPORT.md"),
    ("slides_pptx", "scripts/build_slides.py",
     "paper/slides/SLIDES.pptx: the sixteen-slide ECS8056 presentation deck"),
    ("check_doc_citations", "scripts/check_doc_citations.py",
     "GATE: scan hand-written analysis/*.md docs for numeric claims that no "
     "longer match any live provenance source. Fails the build (nonzero "
     "exit) on any unsuppressed mismatch -- legitimate historical/external/"
     "verified-current values must carry a cite: marker or an "
     "analysis/CITATION_ALLOWLIST.md entry, not be silently ignored. Will "
     "also scan paper/ sources once that directory holds prose, not just "
     "references.yaml."),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", metavar="KEY",
                         help="Run only these step keys (see --list).")
    parser.add_argument("--list", action="store_true", help="List registered steps and exit.")
    args = parser.parse_args()

    if args.list:
        for key, script, desc in STEPS:
            print(f"  {key:20s} {script:45s} {desc}")
        return

    selected = STEPS
    if args.only:
        wanted = set(args.only)
        unknown = wanted - {k for k, _, _ in STEPS}
        if unknown:
            raise SystemExit(f"Unknown step key(s): {sorted(unknown)} -- see --list")
        selected = [s for s in STEPS if s[0] in wanted]

    results = []
    for key, script, desc in selected:
        print(f"\n{'='*70}\n{key}: {desc}\n{'='*70}")
        proc = subprocess.run([PYTHON, script], cwd=ROOT)
        results.append((key, proc.returncode))
        status = "OK" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
        print(f"--- {key}: {status} ---")

    print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
    for key, rc in results:
        print(f"  {key:20s} {'OK' if rc == 0 else f'FAILED (exit {rc})'}")

    citation_result = next(((k, rc) for k, rc in results if k == "check_doc_citations"), None)
    if citation_result is not None:
        key, rc = citation_result
        gate = "PASS" if rc == 0 else "FAIL -- unsuppressed citation mismatch(es), see output above"
        print(f"\nCITATION GATE: {gate}")

    if any(rc != 0 for _, rc in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
