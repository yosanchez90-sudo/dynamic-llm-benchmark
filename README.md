# Dissertation: Memorisation-Robust Benchmarking of LLM Test Generation: A Dynamic, Template-Based Benchmark with Complexity-Tiered Mutation Analysis

## Setup
See `docs/setup.md`.

## Reproducing experiments
See `docs/reproducibility.md`.

## Cluster-specific notes

### gnureadline
Kelvin2's `python3/3.10.5/gcc-9.3.0` was compiled without `libreadline`
support, so the standard library `readline` module is missing. We add
`gnureadline` to provide a drop-in replacement - required by `inspect_ai`
and useful for any package that needs terminal line editing.