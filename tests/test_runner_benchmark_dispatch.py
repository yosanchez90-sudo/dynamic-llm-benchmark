"""_load_problems() dispatch: Dynamic loader vs ULT/PLT static-benchmark
loader, selected by config["benchmark"]. Regression guard for the bug this
was fixing — run_test_gen_experiment used to call test_gen.load()
unconditionally, so benchmark="ult"/"plt" configs silently ran the Dynamic
benchmark instead of ULT/PLT.
"""
from __future__ import annotations

from src.eval import test_gen_runner


def test_dynamic_benchmark_calls_test_gen_load(monkeypatch):
    calls = []
    monkeypatch.setattr(
        test_gen_runner.test_gen, "load",
        lambda **kw: calls.append(("test_gen", kw)) or ["problem"],
    )
    monkeypatch.setattr(
        test_gen_runner.ult_plt, "load",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    config = {
        "benchmark": "dynamic",
        "instantiation_id": "1",
        "instantiation_seed": 1,
        "prompting_condition": "zero_shot",
    }
    result = test_gen_runner._load_problems(config)
    assert result == ["problem"]
    assert calls[0][0] == "test_gen"


def test_ult_benchmark_calls_ult_plt_load_not_test_gen(monkeypatch):
    monkeypatch.setattr(
        test_gen_runner.test_gen, "load",
        lambda **kw: (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    calls = []
    monkeypatch.setattr(
        test_gen_runner.ult_plt, "load",
        lambda benchmark, **kw: calls.append((benchmark, kw)) or ["ult_problem"],
    )
    config = {"benchmark": "ult", "prompting_condition": "zero_shot", "max_n": 5, "sample_seed": 7}
    result = test_gen_runner._load_problems(config)
    assert result == ["ult_problem"]
    assert calls[0] == ("ult", {"prompting_condition": "zero_shot", "max_n": 5, "sample_seed": 7})


def test_plt_with_subsample_tag_calls_load_manifest_subset(monkeypatch):
    calls = []
    monkeypatch.setattr(
        test_gen_runner.ult_plt, "load_manifest_subset",
        lambda benchmark, tag, **kw: calls.append((benchmark, tag, kw)) or ["core_problem"],
    )
    monkeypatch.setattr(
        test_gen_runner.ult_plt, "load",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("should use manifest subset, not a fresh draw")),
    )
    config = {"benchmark": "plt", "prompting_condition": "zero_shot", "subsample_tag": "core_400"}
    result = test_gen_runner._load_problems(config)
    assert result == ["core_problem"]
    assert calls[0] == ("plt", "core_400", {"prompting_condition": "zero_shot"})
