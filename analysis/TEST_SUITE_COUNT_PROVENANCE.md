# Test suite count — provenance

Generated: 2026-08-26T08:06:19.264010+00:00
Git commit: 09eb1bf
Script: scripts/count_test_suite.py

`pytest --collect-only -q` against `testpaths = ["tests"]`
(pyproject.toml): **152 tests collected**.

Collection only, no test executed, no pass/fail claim here. For the
executed-and-passing count, run `pytest -q` directly (README.md's
"Running the tests" section has the CPU-only vs GPU-node split via the
`torch` marker).
