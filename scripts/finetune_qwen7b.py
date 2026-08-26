"""LoRA fine-tuning of Qwen2.5-Coder-7B-Instruct for the contamination-simulation experiment.

What this script does
---------------------
1. Loads the base Qwen 7B model in bfloat16 with gradient checkpointing.
2. Wraps it with a LoRA adapter (PEFT library). Only ~0.5% of parameters are
   trained; the original weights are frozen.
3. Formats the training data as Qwen's chat template and trains with TRL's
   SFTTrainer (Supervised Fine-Tuning Trainer).
4. Saves only the LoRA adapter weights to output_dir (not the full 14GB model).

After training, the adapter can be loaded on top of the base model with:
    model = PeftModel.from_pretrained(base_model, "data/finetune/qwen7b_lora_inst1")

Usage:
    python scripts/finetune_qwen7b.py --config configs/finetune_qwen7b_inst1.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "configs/finetune_qwen7b_inst1.yaml")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())

    # ── imports (deferred so --help works without torch) ─────────────────────
    import json
    import os

    import torch
    from datasets import Dataset
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    os.environ.setdefault("HF_HOME",
        f"/mnt/scratch2/users/{os.environ['USER']}/.huggingface")
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    model_cfg = cfg["model"]
    lora_cfg  = cfg["lora"]
    train_cfg = cfg["training"]
    data_cfg  = cfg["data"]

    # ── load tokenizer ────────────────────────────────────────────────────────
    print(f"Loading tokenizer: {model_cfg['id']} @ {model_cfg['revision'][:8]}…")
    tokenizer = AutoTokenizer.from_pretrained(
        model_cfg["id"],
        revision=model_cfg["revision"],
        local_files_only=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── load base model ───────────────────────────────────────────────────────
    dtype = torch.bfloat16 if model_cfg["dtype"] == "bfloat16" else torch.float32
    print(f"Loading model in {dtype}…")
    model = AutoModelForCausalLM.from_pretrained(
        model_cfg["id"],
        revision=model_cfg["revision"],
        dtype=dtype,
        device_map="auto",
        local_files_only=True,
    )
    model.enable_input_require_grads()   # required for gradient checkpointing + PEFT

    # ── apply LoRA ────────────────────────────────────────────────────────────
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_cfg["r"],
        lora_alpha=lora_cfg["alpha"],
        lora_dropout=lora_cfg["dropout"],
        target_modules=lora_cfg["target_modules"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ── load and format training data ─────────────────────────────────────────
    train_file = ROOT / data_cfg["train_file"]
    raw = [json.loads(l) for l in train_file.read_text().splitlines() if l.strip()]
    print(f"Training examples: {len(raw)}")

    # Apply Qwen's chat template to each example, producing a single string.
    # The SFTTrainer will then tokenise these strings.
    def apply_template(example: dict) -> dict:
        text = tokenizer.apply_chat_template(
            example["messages"],
            tokenize=False,
            add_generation_prompt=False,   # full conversation including assistant turn
        )
        return {"text": text}

    dataset = Dataset.from_list(raw).map(apply_template, remove_columns=["messages"])
    print(f"Sample formatted text (first 400 chars):\n{dataset[0]['text'][:400]}\n")

    # ── training arguments ────────────────────────────────────────────────────
    out_dir = ROOT / train_cfg["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    # SFTConfig extends TrainingArguments and also owns max_seq_length +
    # dataset_text_field (moved out of SFTTrainer in TRL 1.6).
    # Support both old (max_seq_length) and new (max_length) config key names.
    max_length = train_cfg.get("max_length") or train_cfg.get("max_seq_length", 2048)

    sft_kwargs: dict = dict(
        output_dir                  = str(out_dir),
        num_train_epochs            = train_cfg["num_train_epochs"],
        per_device_train_batch_size = train_cfg["per_device_train_batch_size"],
        gradient_accumulation_steps = train_cfg["gradient_accumulation_steps"],
        learning_rate               = train_cfg["learning_rate"],
        lr_scheduler_type           = train_cfg["lr_scheduler_type"],
        warmup_ratio                = train_cfg["warmup_ratio"],
        bf16                        = train_cfg["bf16"],
        gradient_checkpointing      = train_cfg["gradient_checkpointing"],
        save_strategy               = train_cfg["save_strategy"],
        logging_steps               = train_cfg["logging_steps"],
        seed                        = train_cfg["seed"],
        max_length                  = max_length,
        dataset_text_field          = "text",
        remove_unused_columns       = False,
        report_to                   = "none",
    )
    if "save_total_limit" in train_cfg:
        sft_kwargs["save_total_limit"] = train_cfg["save_total_limit"]

    training_args = SFTConfig(**sft_kwargs)

    # ── trainer ───────────────────────────────────────────────────────────────
    trainer = SFTTrainer(
        model            = model,
        processing_class = tokenizer,   # renamed in TRL 1.6
        train_dataset    = dataset,
        args             = training_args,
    )

    print("Starting training…")
    trainer.train()

    # ── save adapter only (not the 14GB base model) ───────────────────────────
    adapter_dir = out_dir / "adapter_final"
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    print(f"\nAdapter saved to: {adapter_dir}")
    print("Training complete.")


if __name__ == "__main__":
    main()
