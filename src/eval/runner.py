"""Run one experimental configuration end-to-end."""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.data import mini_coding
from src.eval.scoring import extract_code, run_tests
from src.logging_utils import append_jsonl
from src.models.local import GenerationConfig, LocalModel


# Registry: dataset name → loader function. Add new datasets here.
DATASETS = {
    "mini_coding": mini_coding.load,
}


def run_experiment(config: dict[str, Any]) -> Path:
    """Run one config end-to-end, write JSONL, return the output path."""

    # --- 1. Resolve dataset ----------------------------------------
    dataset_name = config["dataset"]
    if dataset_name not in DATASETS:
        raise ValueError(
            f"Unknown dataset: {dataset_name}. "
            f"Known: {list(DATASETS)}"
        )
    problems = DATASETS[dataset_name]()

    # --- 2. Load model ---------------------------------------------
    import torch
    dtype_map = {"bfloat16": torch.bfloat16, "float16": torch.float16,
                 "float32": torch.float32}
    model = LocalModel(
        model_id=config["model"]["id"],
        revision=config["model"].get("revision"),
        dtype=dtype_map[config["model"]["dtype"]],
    )

    # --- 3. Decoding config ----------------------------------------
    gen_cfg = GenerationConfig(**config["generation"])

    # --- 4. Output path --------------------------------------------
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    safe_model = config["model"]["id"].replace("/", "__")
    output_dir = Path(config["output_dir"])
    output_path = (
        output_dir
        / f"{safe_model}__seed{gen_cfg.seed}__{run_ts}.jsonl"
    )

    print(f"Output: {output_path}")
    print(f"Running {len(problems)} problems...\n")

    # --- 5. Loop over problems -------------------------------------
    n_passed = 0
    for problem in problems:
        messages = [{"role": "user", "content": problem.prompt}]
        model_out = model.generate(messages, gen_cfg)

        extracted = extract_code(model_out.response)
        test_result = run_tests(extracted, problem.test_code)

        # Build the record: model output + scoring + config link
        record = asdict(model_out)
        record["problem_id"] = problem.problem_id
        record["extracted_code"] = extracted
        record["test_passed"] = test_result.passed
        record["test_error"] = test_result.error
        record["config_name"] = config["name"]
        record["dataset"] = dataset_name

        append_jsonl(record, output_path)

        status = "PASS" if test_result.passed else "FAIL"
        print(f"  [{status}] {problem.problem_id}")
        if not test_result.passed:
            print(f"        {test_result.error.splitlines()[-1] if test_result.error else ''}")

        n_passed += int(test_result.passed)

    print(f"\nFinal: {n_passed}/{len(problems)} passed")
    return output_path