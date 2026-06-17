"""Run one test-generation config from a YAML file.

All configs must set `task: test_generation`. Dispatches to:
  src/eval/test_gen_runner.run_test_gen_experiment

SLURM array usage (mutation scoring):
  sbatch --export=ALL,CONFIG=path/to.yaml scripts/slurm/run_mutation_array.slurm
The array script passes --shard-id and --n-shards automatically via
$SLURM_ARRAY_TASK_ID / $SLURM_ARRAY_TASK_COUNT.
"""
import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path,
                        help="Path to a YAML config file.")
    parser.add_argument("--shard-id", type=int, default=0,
                        help="This task's shard index (0-based). "
                             "Set by SLURM_ARRAY_TASK_ID in array jobs.")
    parser.add_argument("--n-shards", type=int, default=1,
                        help="Total number of shards. "
                             "Set by SLURM_ARRAY_TASK_COUNT in array jobs.")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    if config.get("task") != "test_generation":
        raise ValueError(
            f"Config must set `task: test_generation`. Got: {config.get('task')!r}"
        )

    # Inject shard info so the runner can slice the problem list and name the
    # output file correctly.  Single-shard runs (n_shards=1) are no-ops.
    config["shard_id"] = args.shard_id
    config["n_shards"] = args.n_shards

    print(f"Config: {config['name']}")
    print(f"  Model:   {config['model']['id']}")
    if args.n_shards > 1:
        print(f"  Shard:   {args.shard_id}/{args.n_shards}")
    print()

    from src.eval.test_gen_runner import run_test_gen_experiment
    output_path = run_test_gen_experiment(config)

    print(f"\nDone. Results at: {output_path}")


if __name__ == "__main__":
    main()
