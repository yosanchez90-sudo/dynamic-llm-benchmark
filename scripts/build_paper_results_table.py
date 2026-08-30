"""Generate paper/table_results.tex: the main descriptive results table
(RUBRIC_ACTION_PLAN.md PA-1) -- how the nine canonical models actually
scored on DyMuT (pooled across tiers) and on ULT, side by side, before
any hypothesis test is applied to that data.

Read live from analysis/ranking_matrix_scores.csv (itself produced by
scripts/build_ranking_matrix.py), the same source Section 4's prose and
Figure 3 draw on, so this table can never drift from the hypothesis-test
tables that share its data.

Usage:
    python scripts/build_paper_results_table.py

Writes: paper/table_results.tex
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SCORES = ROOT / "analysis" / "ranking_matrix_scores.csv"
OUT_PATH = ROOT / "paper" / "table_results.tex"

THIN_THRESHOLD = 20

# Display order and short labels, matching Table I / the paper's own
# "Qwen 32B/7B/1.5B" naming for the local sweep.
MODEL_ORDER = [
    ("gpt-5-2025-08-07", "GPT-5"),
    ("gpt-5-mini-2025-08-07", "GPT-5-mini"),
    ("claude-sonnet-4-6", "Claude Sonnet 4.6"),
    ("claude-haiku-4-5-20251001", "Claude Haiku 4.5"),
    ("gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview"),
    ("gemini-3.1-flash-lite", "Gemini 3.1 Flash-Lite"),
    ("Qwen__Qwen2.5-Coder-32B-Instruct", "Qwen 32B"),
    ("Qwen__Qwen2.5-Coder-7B-Instruct", "Qwen 7B"),
    ("Qwen__Qwen2.5-Coder-1.5B-Instruct", "Qwen 1.5B"),
]


def _pct(x) -> str:
    return "--" if pd.isna(x) else f"{x * 100:.1f}"


FULL_ULT_N = 400  # core_400's full size; a model whose ULT n_total is below
                   # this is on an incomplete evaluation crawl, not a 400-row
                   # baseline like every other row (confirmed 2026-08-30 for
                   # Gemini 3.1 Pro Preview: 101/400, analysis/
                   # METRICS_AND_FINDINGS_EXPLAINED.md's Gemini-crawl tracking
                   # -- a pre-existing, already-documented data gap, not a
                   # pipeline bug; this table must disclose it, not paper over it).


def _row(df: pd.DataFrame, label: str, model_label: str, benchmark: str) -> dict:
    sub = df[(df["model_label"] == model_label) & (df["benchmark"] == benchmark)]
    if sub.empty:
        return {"exec": None, "bp": None, "cond": None, "cov": None, "n_def": None, "n_total": None}
    r = sub.iloc[0]
    return {
        "exec": r["exec_rate"], "bp": r["baseline_pass_rate"],
        "cond": r["conditional_mutk"], "cov": r["coverage_adjusted"],
        "n_def": None if pd.isna(r["n_defined_mutk"]) else int(r["n_defined_mutk"]),
        "n_total": None if pd.isna(r["n_total"]) else int(r["n_total"]),
    }


def main() -> None:
    df = pd.read_csv(SCORES)
    df = df[df["scope"] == "canonical"]

    rows_tex = []
    partial_ult_models: list[str] = []
    for model_label, short in MODEL_ORDER:
        dyn = _row(df, short, model_label, "dynamic_pooled")
        ult = _row(df, short, model_label, "ult_core400")
        dyn_thin = dyn["n_def"] is not None and dyn["n_def"] < THIN_THRESHOLD
        ult_thin = ult["n_def"] is not None and ult["n_def"] < THIN_THRESHOLD
        ult_partial = ult["n_total"] is not None and ult["n_total"] < FULL_ULT_N
        if ult_partial:
            partial_ult_models.append(f"{short} ({ult['n_total']}/{FULL_ULT_N})")
        ult_flag = "$^\\ddagger$" if ult_partial else ""
        dyn_cond = _pct(dyn["cond"]) + ("$^\\dagger$" if dyn_thin else "")
        ult_cond = _pct(ult["cond"]) + ("$^\\dagger$" if ult_thin else "") + ult_flag
        dyn_cov = _pct(dyn["cov"]) + ("$^\\dagger$" if dyn_thin else "")
        ult_cov = _pct(ult["cov"]) + ("$^\\dagger$" if ult_thin else "") + ult_flag
        rows_tex.append(
            f"{short} & {_pct(dyn['exec'])} & {_pct(dyn['bp'])} & {dyn_cond} & {dyn_cov} & {dyn['n_def']} "
            f"& {_pct(ult['exec'])}{ult_flag} & {_pct(ult['bp'])}{ult_flag} & {ult_cond} & {ult_cov} & {ult['n_def']} \\\\"
        )

    body = "\n".join(rows_tex)
    # DyMuT-side instantiation count: 300 problems/instantiation, so
    # n_total/300 recovers the count live rather than hand-typing "five
    # instantiations for seven models, four for both Gemini models"
    # (RUBRIC_ACTION_PLAN.md's own hardcoded phrasing would go stale the
    # moment a declined instantiation lands or a new one is added).
    dyn_insts = {}
    for model_label, short in MODEL_ORDER:
        dyn = _row(df, short, model_label, "dynamic_pooled")
        if dyn["n_total"] is not None:
            dyn_insts.setdefault(dyn["n_total"] // 300, []).append(short)
    inst_clause = "; ".join(
        f"{n} instantiation{'s' if n != 1 else ''} for {', '.join(models)}"
        for n, models in sorted(dyn_insts.items(), key=lambda kv: -len(kv[1]))
    )
    partial_ult_clause = (
        "; ".join(partial_ult_models) if partial_ult_models else "none"
    )
    # table (not table*), squeezed into a single IEEEtran column (2026-08-29
    # direction, same "wrap it, don't span both columns" call as Table I):
    # the Model column becomes a fixed-width p{} cell (long names like
    # "Gemini 3.1 Pro Preview" wrap to two lines) and the two widest column
    # headers (Cov.-adj., $n_{def}$) are two-line \shortstacks, since an
    # un-wrapped header is wider than every data value beneath it and would
    # otherwise be the thing forcing each data column wide.
    header_cov = "\\shortstack{Cov.-\\\\adj.}"
    header_ndef = "\\shortstack{$n_{\\text{def}}$}"
    tex = f"""% Auto-generated by scripts/build_paper_results_table.py -- DO NOT EDIT DIRECTLY.
% Main descriptive results table (RUBRIC_ACTION_PLAN.md PA-1): how the nine
% canonical models scored on DyMuT (pooled) and ULT, before any hypothesis
% test. Read live from analysis/ranking_matrix_scores.csv. table (single
% IEEEtran column, not table*): see script docstring -- Model is a p{{}}
% column so long names wrap instead of forcing the table wide.
\\begin{{table}}[t]
\\caption{{Results by model: DyMuT (pooled across tiers) and ULT (\\texttt{{core\\_400}}), all values \\%. Exec.\\ = exec\\_rate, BP = baseline\\_pass\\_rate, Mut@K = conditional mutation score, Cov.-adj.\\ = coverage-adjusted mutation score, $n_{{\\text{{def}}}}$ = problems with a Mut@K. $^\\dagger$ marks a thin cell ($n_{{\\text{{def}}}}<{THIN_THRESHOLD}$). DyMuT pools unequal N: {inst_clause}, an already-declined gap (Section~\\ref{{sec:results-h5}}). $^\\ddagger$ marks an incomplete ULT crawl, not the full \\texttt{{core\\_400}}: {partial_ult_clause}, a separate, pre-existing data gap unrelated to the DyMuT instantiation count above.}}
\\label{{tab:results}}
\\centering
\\scriptsize
\\setlength{{\\tabcolsep}}{{1.6pt}}
\\renewcommand{{\\arraystretch}}{{0.92}}
\\begin{{tabular}}{{@{{}}p{{0.62in}} rrrrr rrrrr@{{}}}}
\\toprule
& \\multicolumn{{5}}{{c}}{{DyMuT (pooled)}} & \\multicolumn{{5}}{{c}}{{ULT (\\texttt{{core\\_400}})}} \\\\
\\cmidrule(lr){{2-6}} \\cmidrule(lr){{7-11}}
Model & Exec. & BP & Mut@K & {header_cov} & {header_ndef} & Exec. & BP & Mut@K & {header_cov} & {header_ndef} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    OUT_PATH.write_text(tex)
    print(f"Wrote {OUT_PATH.relative_to(ROOT)} ({len(MODEL_ORDER)} rows)")


if __name__ == "__main__":
    main()
