"""
Inference Engine for Fine-Tuned Mkri Hakaym (ምኽሪ ሓካይም) Model.
Loads fine-tuned PEFT LoRA adapter or provides hybrid reasoning with RAG.
"""
import argparse
import logging
from pathlib import Path
import torch

from brain.rag_engine import MedicalRAGEngine
from training.prepare_dataset import SYSTEM_PROMPT_TI
from training.finetune_lora import format_instruction_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Inference")


class FineTunedDoctorInference:
    def __init__(self, adapter_path: str = "models/mkri_hakaym_lora/final_adapter", base_model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"):
        self.adapter_path = Path(adapter_path)
        self.base_model_name = base_model_name
        self.rag = MedicalRAGEngine()
        self.model = None
        self.tokenizer = None
        self._loaded = False

    def load_adapter(self):
        """Loads base model + fine-tuned LoRA weights."""
        if not self.adapter_path.exists():
            logger.warning(f"Adapter not found at {self.adapter_path}. Using RAG + Rule-based Brain.")
            return

        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel

        logger.info(f"Loading base model {self.base_model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.adapter_path))
        base = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
        )
        self.model = PeftModel.from_pretrained(base, str(self.adapter_path))
        self._loaded = True
        logger.info("Fine-tuned Mkri Hakaym LoRA model loaded successfully.")

    def generate_response(self, user_query: str) -> str:
        # Check emergency triage first (Safety protocol)
        triage_res = self.rag.triage.evaluate_query(user_query)
        if triage_res.is_emergency:
            return triage_res.triage_message_ti

        # If fine-tuned model is active, generate with neural model
        if self._loaded and self.model and self.tokenizer:
            prompt = format_instruction_prompt({
                "system": SYSTEM_PROMPT_TI,
                "instruction": user_query,
                "output": "",
            })
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}

            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.3,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
            generated_text = self.tokenizer.decode(output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            return generated_text.strip()

        # Grounded RAG fallback
        rag_res = self.rag.answer_caller_query(user_query)
        return rag_res["spoken_response_ti"]


def main():
    parser = argparse.ArgumentParser(description="Test fine-tuned doctor inference")
    parser.add_argument("--query", type=str, default="ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?")
    args = parser.parse_args()

    engine = FineTunedDoctorInference()
    reply = engine.generate_response(args.query)

    print(f"\n[Caller Query]: {args.query}")
    print(f"[Fine-Tuned Doctor Reply]:\n{reply}\n")


if __name__ == "__main__":
    main()
