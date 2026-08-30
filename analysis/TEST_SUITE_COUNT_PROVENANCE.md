# Test suite count — provenance

Generated: 2026-08-29T23:46:58.116148+00:00
Git commit: 9cdef55
Script: scripts/count_test_suite.py

`pytest --collect-only -q` against `testpaths = ["tests"]`
(pyproject.toml): **152 tests collected**.

Collection only, no test executed, no pass/fail claim here. For the
executed-and-passing count, run `pytest -q` directly (README.md's
"Running the tests" section has the CPU-only vs GPU-node split via the
`torch` marker).
