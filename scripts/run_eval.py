"""Run one experimental config from a YAML file."""
import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.eval.runner import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", required=True, type=Path,
        help="Path to a YAML config file."
    )
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    print(f"Config: {config['name']}")
    print(f"  Model:   {config['model']['id']}")
    print(f"  Dataset: {config['dataset']}")
    print(f"  Seed:    {config['generation']['seed']}\n")

    output_path = run_experiment(config)
    print(f"\nDone. Results at: {output_path}")


if __name__ == "__main__":
    main()