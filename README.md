# Memorisation-Robust Benchmarking of LLM Test Generation

**A Dynamic, Template-Based Benchmark with Complexity-Tiered Mutation Analysis.**
ECS8056 MSc AI Themed Research Project, Yohan Sneider Sanchez Vega (40492566),
Queen's University Belfast. Supervisor: Pinzhen Chen.

Static benchmarks for evaluating LLM test generation become contaminated once
published: their content leaks into future training data, scraped from the
web or absorbed via API use during evaluation. This project builds a
dynamic, template-based benchmark. Sixty hand-authored templates across four
cyclomatic-complexity tiers generate fresh, seeded problem instances at
evaluation time, scored by mutation testing.

Nine models across four providers are evaluated against this benchmark and
against a static comparator (ULT, and its leaked twin PLT). Evaluation
includes an observational and a causal (fine-tuning) contamination
comparison, plus a construct-validity check against an external
code-generation proxy (BigCodeBench).

The project's outputs are the paper (`paper/paper.pdf`), the ECS8056
supporting report (`paper/supporting_report/`), and the slide deck. The
compiled paper, the report and the deck are all build products and are
gitignored, so a fresh clone contains their sources, not the files
themselves.

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
`.env`. Fill in the API keys for whichever providers you need
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `HF_TOKEN`). `.env`
is gitignored and was never committed. Set `HF_HOME` to a scratch path before
downloading any HuggingFace model.

## Running the tests

```bash
uv run pytest
```

`pyproject.toml` sets `testpaths = ["tests"]`, so a bare `pytest` run picks up
every test in `tests/` (currently 152 collected). Each test's docstring names
the bug or regression it guards and the module it targets. None of the 152
require a GPU or real CUDA hardware.

### Running the tests without a GPU

No test in this suite touches `torch.cuda` or loads a real model, so none of
the 152 need GPU hardware. Three files, 16 tests total (`tests/test_local_model.py`,
`tests/test_gen_runner_resume.py`, `tests/test_runner_benchmark_dispatch.py`),
import modules that import `torch` transitively. They need `torch` to be
importable. CPU-only is enough. They're marked with a custom `torch` pytest
marker (registered in `pyproject.toml`'s `[tool.pytest.ini_options]`) so they
can be split out:

```bash
uv run pytest -m "not torch"   # 136 tests, works even if torch can't import
uv run pytest -m "torch"       # the other 16
uv run pytest                  # all 152, needs a working torch import
```

If `pytest` fails with `RuntimeError: Unable to find torch_shm_manager` (or
any other broken-torch-import error), that's a corrupted local `.venv`. A
fresh `uv sync` does not reproduce it: installing the same pinned wheel
(`torch==2.5.1+cu121`) into a throwaway venv left `torch/bin/torch_shm_manager`
present and `import torch` clean. Fix it with a targeted reinstall:

```bash
uv sync --reinstall-package torch
```

A full `uv sync` would also prune any installed-but-undeclared package.

**Do not run a bare `uv sync` to "fix" the environment.** Every dependency
imported by this project's code must be declared in `pyproject.toml`. Check
with `uv sync --dry-run`. If it would uninstall a package you know is in
use, that package is undeclared. Add it with `uv add
"package==<currently-installed version>"`. A bare `uv sync` removes anything
installed-but-undeclared and can break a script that depended on it.

## Regenerating results, figures, and tables

`scripts/build_thesis_assets.py` is the single entry point for everything
downstream of the raw result files in `data/results/` (gitignored): every
comparison table, correlation, stability statistic, figure, and the paper's
numeric macros, in one registered pipeline of no-argument, safe-to-rerun
steps.

```bash
uv run python scripts/build_thesis_assets.py            # run every registered step
uv run python scripts/build_thesis_assets.py --list      # show registered steps
uv run python scripts/build_thesis_assets.py --only rq5 comparison_c   # run a subset
```

The final registered step is `check_doc_citations.py`, a gate that scans
`analysis/*.md` and `paper/sections/*.tex` for hand-typed numbers and checks
each one against this live output. It fails the build on any number that no
longer matches what the pipeline currently produces. Fix the number, or if
it's superseded or external (a paper's reported figure, a leaderboard
score), mark it with an inline `<!-- cite:historical -->` /
`<!-- cite:external -->` comment or an entry in
`analysis/CITATION_ALLOWLIST.md`.

To build the paper after the assets above are current:

```bash
cd paper && make
```

`paper/Makefile` regenerates `values.tex`/`references.bib`/`table1.tex` from
the current `analysis/` output before every compile, so the PDF is never
stale relative to the data behind it.

## The live demonstration

`demo/` holds a short, self-contained walkthrough of the benchmark's central
claim, in three parts: does the mechanism work, what does it buy you, and can
you trust the numbers. It makes no model API calls — every test suite is a
file on disk, written by hand in advance — so it runs in seconds and is
reproducible offline.

```bash
source .venv/bin/activate     # the scripts import the real scorer
./demo/run_demo.sh            # press Enter between steps
```

### Reproducing it, step by step

The demo's three hand-written suites are not arbitrary: each one is built to
produce a specific verdict against a specific instance. This is the order to
rebuild them in, whether you are reconstructing the demo or retargeting it at
a different template. Run everything from the repository root.

**1. Choose a template and two seeds.** Look at what they actually produce
before committing:

```bash
python demo/show_instance.py --template L2-clamp-001 --seed 1101
python demo/show_instance.py --template L2-clamp-001 --seed 4207 --no-mutants
```

Pick seeds that differ in *both* the function name and the clamp constant —
that pairing is what makes the memorisation point land. Reject a seed that
repeats a name already in use.

**2. Read the mutants before writing any test.** The base suite has to leave a
*catchable* mutant alive deliberately, so you must know which one is catchable:

```bash
python demo/show_instance.py --template L2-clamp-001 --seed 1101 --show-mutant 7
```

Do this per mutant, or script it — execute every mutant against candidate
inputs and record which inputs separate it from the original. Do not infer
this by reading the code: an *equivalent* mutant looks catchable until you run
it, and this template has two.

**3. Write the base suite** (`demo/suite_seed_1101.py`) against seed 1101's
generated function, deliberately omitting the one input that would kill your
chosen survivor. Here that input is 67 and the survivor is mutant M7.

**4. Write the killer** (`demo/suite_seed_1101_plus.py`): a copy of the base
suite plus that single assertion. Keep both docstrings identical, or the diff
shown during the demo becomes a wall of prose instead of one test.

**5. Write the import-repaired variant**
(`demo/suite_seed_1101_import_fixed.py`): the base suite with the function
name changed to the second seed's, at *every* call site — Python has no
partial import, so renaming only the import line raises `NameError` and you
get the wrong failure.

**6. Verify all four verdicts before rehearsing:**

```bash
python demo/score_suite.py --template L2-clamp-001 --seed 1101 --suite demo/suite_seed_1101.py       # 7/10
python demo/score_suite.py --template L2-clamp-001 --seed 1101 --suite demo/suite_seed_1101_plus.py  # 8/10
python demo/score_suite.py --template L2-clamp-001 --seed 4207 --suite demo/suite_seed_1101.py       # exec gate FAIL
python demo/score_suite.py --template L2-clamp-001 --seed 4207 --suite demo/suite_seed_1101_import_fixed.py   # baseline gate FAIL
```

**7. Measure the whole-set claim rather than asserting it:**

```bash
python demo/compare_instantiations.py     # 300 problems per version, expect 0 shared
```

It derives its instance seeds with the production formula, importing
`INSTANCE_BASE_SEEDS` from `scripts/generate_instantiation_manifest.py`, so it
demonstrates the path the pipeline actually takes.

**8. Pick and test the citation-gate anchor.** `run_demo.sh` ends by tampering
with a number and watching `check_doc_citations.py` refuse to build. The gate
detects *stale* numbers — values matching nothing the pipeline currently
produces — so an invented number often still passes by coincidentally matching
some other live value. Confirm your chosen anchor actually fails before you
rely on it:

```bash
sed -i "s/n_models=9: exec_rate/n_models=11: exec_rate/" analysis/RQ5_INTERPRETATION.md
uv run python scripts/check_doc_citations.py --only rq5_interpretation   # must report GATE: FAIL
git checkout -- analysis/RQ5_INTERPRETATION.md
```

If it reports PASS, choose a different anchor. Integer counts such as
`n_models` work because only ten distinct values exist live; most p-values and
correlations do not.

**9. Run it end to end** before rehearsing with narration:

```bash
yes "" | ./demo/run_demo.sh | less
```

`run_demo.sh` guards this last step: it refuses to edit the cited document if
it has uncommitted changes, and restores it on exit or interrupt.

## Where things live

| Directory | What it is | Paper section |
|---|---|---|
| `template_corpus/` | The 60-template grammar (`templates/L1`–`L4`), its validation/diversity smoke tests (`templates/_smoke/`), and the parameter-domain spec (`templates/spec/`) | Methods §III-A/B (template grammar, seeded instantiation) |
| `src/` | Library code: model wrappers (`src/models/`), the eval/scoring harness (`src/eval/`), benchmark loaders (`src/data/`), and the analysis/comparison/DiD statistics (`src/Analysis/`, `src/Contamination/`) | Methods §III-C–E (mutation operators, models, fine-tuning) |
| `configs/` | One YAML per experiment run (model × benchmark × tier-split × instantiation), consumed by `scripts/run_eval.py` via `scripts/slurm/` | — (experiment configuration, not cited) |
| `scripts/` | Every pipeline entrypoint, table/figure builder, and one-off diagnostic, indexed by role in `scripts/README.md` | — |
| `scripts/slurm/` | SLURM job scripts, one per `scripts/*.py` pipeline entrypoint | — |
| `data/` | Raw and generated results (gitignored) | — |
| `analysis/` | Every interpretation document, auto-generated provenance table, and figure behind the paper's results, indexed in `analysis/INDEX.md` (`analysis/README.md` is a contamination notice, not the index) | Results §IV, Discussion §V |
| `docs/` | `Approved_Hypotheses.md` (the six governing hypotheses, verbatim) and `Research_questions.xlsx`/`RESEARCH_QUESTIONS.md` (the RQ/hypothesis tracking workbook and its auto-generated markdown mirror) | Introduction §I (RQ1–RQ5), the hypothesis table in Results §IV |
| `paper/` | The paper source (`paper.tex`, `sections/`) and the ECS8056 supporting report (`supporting_report/`). The compiled PDF, the report's `.docx` and the slide deck are gitignored build products | — (the deliverables) |
| `tests/` | The pytest suite | — |

`PROJECT_BRIEF.md` (repo root) is the canonical statement of the project's
plan and scope: objectives, research questions, the six-phase roadmap, and a
full deviations log. `CONVENTIONS.md` (repo root) is the operational reference:
environment specifics, hard rules the codebase follows, and a detailed
incident history of every measurement bug found and fixed.

## Data

`data/` is entirely gitignored except a handful of force-added provenance
documents (`data/raw/ult_plt/PROVENANCE.md` and its manifests). Raw model
outputs, batch files, and fine-tuning checkpoints are large and not meant to
travel with the repository. **A clean clone of this repository does not
contain any result data.** To reproduce a result from scratch, the evaluation
pipeline (`scripts/run_eval.py` and friends, submitted via `scripts/slurm/`)
has to be run against a configured provider first, which needs real API keys
and, for the open-source models, GPU time on a SLURM cluster. `analysis/` and
`paper/` are tracked normally and reflect the results of a completed run.
`scripts/build_thesis_assets.py` regenerates every table and figure in them
from whatever is currently in `data/results/`, but does not create that
data.

## Cluster-specific notes

### gnureadline

Kelvin2's `python3/3.10.5/gcc-9.3.0` was compiled without `libreadline`
support, so the standard library `readline` module is missing. We add
`gnureadline` to provide a drop-in replacement. It's required by
`inspect_ai` and useful for any package that needs terminal line editing.

## figures

paper/ holds the LaTeX sources and the asset pipeline, and the build_thesis_assets.py regenerates every table and figure from current results
