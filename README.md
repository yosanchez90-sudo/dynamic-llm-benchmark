# Memorisation-Robust Benchmarking of LLM Test Generation

**A Dynamic, Template-Based Benchmark with Complexity-Tiered Mutation Analysis.**
ECS8056 MSc AI Themed Research Project, Yohan Sneider Sanchez Vega (40492566),
Queen's University Belfast. Supervisor: Pinzhen Chen.

Static benchmarks for evaluating LLM test generation become contaminated once
published: their content leaks into future training data, directly (scraped
from the web) or indirectly (via API use during evaluation). This project
builds a dynamic, template-based benchmark instead — sixty hand-authored
templates across four cyclomatic-complexity tiers generate fresh, seeded
problem instances at evaluation time, scored by mutation testing rather than a
fixed reference suite. Nine models across four providers are evaluated against
this benchmark and against a static comparator (ULT, and its deliberately
leaked twin PLT), with both an observational and a causal (fine-tuning)
contamination comparison, plus a construct-validity check against an external
code-generation proxy (BigCodeBench).

The project's outputs are the paper (`paper/paper.pdf`), the ECS8056
supporting report (`paper/supporting_report/`), and the slide deck
(`paper/slides/`) — see [Where things live](#where-things-live) below for how
the rest of the repository maps to what's in them.

## Install

Requires Python 3.10 (pinned in `.python-version`; `pyproject.toml` sets
`requires-python = ">=3.10,<3.11"`) and [`uv`](https://docs.astral.sh/uv/) for
dependency management.

```bash
uv sync
```

This creates `.venv/` from `pyproject.toml`/`uv.lock`. On Kelvin2 (this
project's HPC cluster), source `scripts/activate.sh` first to load the
required Python/CUDA modules, then run `uv sync`. Copy `.env.example` to
`.env` and fill in the API keys for whichever providers you need
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `HF_TOKEN`) — `.env`
is gitignored and was never committed. Set `HF_HOME` to a scratch path before
downloading any HuggingFace model; see the Kelvin2 notes below.

## Running the tests

```bash
uv run pytest
```

`pyproject.toml` sets `testpaths = ["tests"]`, so a bare `pytest` run picks up
every test in `tests/` (currently 136 collected). Each test's docstring names
the specific bug or regression it guards and the module it targets.

## Regenerating results, figures, and tables

`scripts/build_thesis_assets.py` is the single entry point for everything
downstream of the raw result files in `data/results/` (gitignored, see
[Data](#data) below): every comparison table, correlation, stability
statistic, figure, and the paper's own numeric macros, in one registered
pipeline of no-argument, safe-to-rerun steps.

```bash
uv run python scripts/build_thesis_assets.py            # run every registered step
uv run python scripts/build_thesis_assets.py --list      # show registered steps
uv run python scripts/build_thesis_assets.py --only rq5 comparison_c   # run a subset
```

The final registered step is `check_doc_citations.py`, a gate that scans
`analysis/*.md` and `paper/sections/*.tex` for hand-typed numbers and checks
each one against this same live output — it fails the build (nonzero exit) on
any number that no longer matches anything the pipeline currently produces.
See `analysis/README.md` for what a mismatch means and how to resolve one.

To build the paper itself after the assets above are current:

```bash
cd paper && make
```

`paper/Makefile` regenerates `values.tex`/`references.bib`/`table1.tex` from
the current `analysis/` output before every compile, so the PDF is never
stale relative to the data behind it.

## Where things live

| Directory | What it is | Paper section |
|---|---|---|
| `template_corpus/` | The 60-template grammar (`templates/L1`–`L4`), its validation/diversity smoke tests (`templates/_smoke/`), and the parameter-domain spec (`templates/spec/`) | Methods §III-A/B (template grammar, seeded instantiation) |
| `src/` | Library code: model wrappers (`src/models/`), the eval/scoring harness (`src/eval/`), benchmark loaders (`src/data/`), and the analysis/comparison/DiD statistics (`src/Analysis/`, `src/Contamination/`) | Methods §III-C–E (mutation operators, models, fine-tuning) |
| `configs/` | One YAML per experiment run (model × benchmark × tier-split × instantiation), consumed by `scripts/run_eval.py` via `scripts/slurm/` | — (experiment configuration, not directly cited) |
| `scripts/` | Every pipeline entrypoint, table/figure builder, and one-off diagnostic — see `scripts/README.md` for the full index grouped by role | — |
| `scripts/slurm/` | SLURM job scripts, one per `scripts/*.py` pipeline entrypoint | — |
| `data/` | Raw and generated results (gitignored, see below) | — |
| `analysis/` | Every interpretation document, auto-generated provenance table, and figure behind the paper's results — see `analysis/README.md` for the full index | Results §IV, Discussion §V |
| `docs/` | `Approved_Hypotheses.md` (the six governing hypotheses, verbatim) and `Research_questions.xlsx`/`RESEARCH_QUESTIONS.md` (the RQ/hypothesis tracking workbook and its auto-generated markdown mirror) | Introduction §I (RQ1–RQ5), the hypothesis table in Results §IV |
| `paper/` | The paper itself (`paper.tex`/`paper.pdf`), the ECS8056 supporting report (`supporting_report/`), and the slide deck (`slides/`) | — (the deliverables) |
| `tests/` | The pytest suite | — |

`PROJECT_BRIEF.md` (repo root) is the canonical statement of the project's
plan and scope — objectives, research questions, the six-phase roadmap, and a
full deviations log. `CLAUDE.md` (repo root) is the operational reference:
environment specifics, hard rules the codebase follows, and a detailed
incident history of every measurement bug found and fixed (also reproduced as
a table in the supporting report). Start with `PROJECT_BRIEF.md` for *what*
and *why*; `CLAUDE.md` for *how* and *what's gone wrong before*.

## Data

`data/` is entirely gitignored except a handful of force-added provenance
documents (`data/raw/ult_plt/PROVENANCE.md` and its manifests) — raw model
outputs, batch files, and fine-tuning checkpoints are large and not meant to
travel with the repository. **A clean clone of this repository does not
contain any result data.** To reproduce a result from scratch, the evaluation
pipeline (`scripts/run_eval.py` and friends, submitted via `scripts/slurm/`)
has to be run against a configured provider first, which needs real API keys
and, for the open-source models, GPU time on a SLURM cluster. `analysis/` and
`paper/` are tracked normally and reflect the results of a completed run —
`scripts/build_thesis_assets.py` regenerates every table and figure in them
from whatever is currently in `data/results/`, but does not create that data
itself.

## Cluster-specific notes

### gnureadline

Kelvin2's `python3/3.10.5/gcc-9.3.0` was compiled without `libreadline`
support, so the standard library `readline` module is missing. We add
`gnureadline` to provide a drop-in replacement — required by `inspect_ai`
and useful for any package that needs terminal line editing.
