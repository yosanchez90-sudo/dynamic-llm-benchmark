"""One model, one prompt, log the result. The smallest end-to-end pipeline."""
import sys
from pathlib import Path

# Make `src` importable when running this from the project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.models.local import GenerationConfig, LocalModel
from src.logging_utils import append_jsonl


def main() -> None:
    model = LocalModel("Qwen/Qwen2.5-Coder-1.5B-Instruct")
    cfg = GenerationConfig(max_new_tokens=256, do_sample=False, seed=42)

    messages = [
        {
            "role": "user",
            "content": (
                "Write a Python function `is_prime(n: int) -> bool` that "
                "returns True if n is prime, False otherwise. "
                "Include a one-line docstring."
            ),
        }
    ]

    print(f"Loaded {model.model_id}")
    print(f"Revision (pinned): {model.revision}")
    print(f"Generating...\n")

    result = model.generate(messages, cfg)

    print("--- Response ---")
    print(result.response)
    print(f"\n--- {result.input_tokens} input + "
          f"{result.output_tokens} output tokens ---")

    output_path = ROOT / "data" / "results" / "first_run.jsonl"
    append_jsonl(result, output_path)
    print(f"\nLogged to {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()