"""
LoRA / PEFT Fine-Tuning Script for Mkri Hakaym (ምኽሪ ሓካይም).
Fine-tunes open multilingual LLMs (e.g. Qwen2.5, Gemma-2, Llama-3.2) on verified
Tigrinya medical consultations, clinical triage, and broadcast advice.
"""
import argparse
import json
import logging
import sys
from pathlib import Path
import torch

from config import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stdout)
logger = logging.getLogger("FineTune")

MODELS_DIR = DATA_DIR.parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def load_jsonl_dataset(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def format_instruction_prompt(sample: dict) -> str:
    """Format sample into standard ChatML instruction prompt."""
    system = sample.get("system", "")
    instruction = sample.get("instruction", "")
    output = sample.get("output", "")

    return (
        f"<|im_start|>system\n{system}<|im_end|>\n"
        f"<|im_start|>user\n{instruction}<|im_end|>\n"
        f"<|im_start|>assistant\n{output}<|im_end|>"
    )


def run_training(
    base_model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
    output_dir: str = "models/mkri_hakaym_lora",
    epochs: int = 3,
    batch_size: int = 2,
    learning_rate: float = 2e-4,
    dry_run: bool = False,
):
    from datasets import Dataset, DatasetDict
    from peft import LoraConfig, get_peft_model, TaskType

    train_file = DATA_DIR / "training_data" / "train.jsonl"
    val_file = DATA_DIR / "training_data" / "val.jsonl"

    if not train_file.exists():
        raise FileNotFoundError(f"Training data not found at {train_file}. Run prepare_dataset.py first.")

    logger.info(f"Loading dataset offline from {train_file} and {val_file}...")
    train_data = load_jsonl_dataset(train_file)
    val_data = load_jsonl_dataset(val_file)

    dataset = DatasetDict({
        "train": Dataset.from_list(train_data),
        "validation": Dataset.from_list(val_data),
    })
    logger.info(f"Loaded: {len(dataset['train'])} train, {len(dataset['validation'])} val samples.")

    # Inspect formatted sample
    sample_text = format_instruction_prompt(dataset["train"][0])
    logger.info(f"\n--- Formatted Sample Prompt ---\n{sample_text}\n-------------------------------")

    # Define LoRA Configuration
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )
    logger.info(f"Configured LoRA: rank={peft_config.r}, alpha={peft_config.lora_alpha}")

    if dry_run:
        logger.info("✅ DRY-RUN SUCCESS: Dataset and LoRA configuration fully validated!")
        return {"status": "dry_run_passed", "train_samples": len(dataset["train"])}

    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForSeq2Seq,
    )

    logger.info(f"Loading tokenizer and model: {base_model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    def tokenize_fn(examples):
        prompts = [format_instruction_prompt({"system": s, "instruction": i, "output": o}) 
                   for s, i, o in zip(examples["system"], examples["instruction"], examples["output"])]
        return tokenizer(prompts, truncation=True, max_length=512, padding="max_length")

    tokenized_train = dataset["train"].map(tokenize_fn, batched=True)
    tokenized_val = dataset["validation"].map(tokenize_fn, batched=True)

    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        num_train_epochs=epochs,
        logging_steps=5,
        eval_strategy="epoch",
        save_strategy="epoch",
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_val,
        data_collator=DataCollatorForSeq2Seq(tokenizer, pad_to_multiple_of=8, return_tensors="pt"),
    )

    logger.info("Starting training...")
    trainer.train()

    final_save_path = Path(output_dir) / "final_adapter"
    model.save_pretrained(str(final_save_path))
    tokenizer.save_pretrained(str(final_save_path))
    logger.info(f"Model saved successfully to {final_save_path}")
    return {"status": "trained", "save_path": str(final_save_path)}


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Mkri Hakaym model on Tigrinya medical data")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--output_dir", type=str, default="models/mkri_hakaym_lora")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--dry_run", action="store_true", help="Validate pipeline without heavy weights download")

    args = parser.parse_args()
    run_training(
        base_model_name=args.base_model,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
