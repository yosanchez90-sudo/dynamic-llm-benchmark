# Test suite count — provenance

Generated: 2026-08-25T06:32:27.827704+00:00
Git commit: bd24a5f
Script: scripts/count_test_suite.py

`pytest --collect-only -q` against `testpaths = ["tests"]`
(pyproject.toml): **152 tests collected**.

Collection only -- no test executed, no pass/fail claim here. For the
executed-and-passing count, run `pytest -q` directly (see README.md's
"Running the tests" section for the CPU-only vs GPU-node split via the
`torch` marker).
