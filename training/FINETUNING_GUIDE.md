# 🧠 Fine-Tuning Guide for Mkri Hakaym (ምኽሪ ሓካይም)
### Training a Domain-Specific Tigrinya Medical Reasoning LLM

This guide explains how to fine-tune an open-weights multilingual LLM (e.g., **Qwen2.5-1.5B/7B**, **Gemma-2-2B/9B**, or **Llama-3.2-1B/3B**) to act as a **compassionate, culturally aligned Tigrinya Doctor** grounded on Tigrai TV's *"ማዕዳ ሓካይም"*.

---

## 🎯 Why Fine-Tune?
1. **Vernacular Medical Reasoning**: Rural patients do not speak textbook Amharic or English; they describe pain, pregnancy, and sickness using spoken **ትግርኛ (Tigrinya)** idioms (e.g. *ዓሶ*, *ዕንቅርቢት*, *ሕበጥ*, *ምፍዛዝ*, *ውጽኣት*).
2. **Clinical Persona Alignment**: Ensures the model responds in the warm, respectful, reassuring cadence of an Ethiopian community physician (*ምኽሪ ሓካይም* style).
3. **Safety & Triage Reflexes**: Trains the model to immediately identify danger signs (*ቀያሕቲ ምልክታት*) and route the patient to emergency care.

---

## 📁 Pipeline Components

```
training/
├── prepare_dataset.py   # Compiles KB & conversational variations into JSONL
├── finetune_lora.py     # LoRA/PEFT training script (Qwen2.5, Gemma-2, Llama-3.2)
├── infer_finetuned.py   # Inference engine combining fine-tuned weights + RAG triage
└── FINETUNING_GUIDE.md  # Complete training documentation
```

---

## 🛠️ Step 1: Prepare the Dataset
Run the data compilation and augmentation pipeline:
```powershell
.venv\Scripts\python -m training.prepare_dataset
```
This generates:
* `data/training_data/train.jsonl` (66+ augmented conversational pairs)
* `data/training_data/val.jsonl` (validation hold-out)

Each sample follows standard ChatML formatting:
```json
{
  "system": "ንስኻ ሓኪም 'ምኽሪ ሓካይም' ኢኻ። ብትግርኛ ግቡእ፣ ርህሩህን ስነ-ፍልጠታዊን ናይ ጥዕና ምኽሪ ትህብ...",
  "instruction": "ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ ዝግብኣኒ?",
  "output": "እንቋዕ ሓጎሰኪ! ጥንሲ ከምዝሓዝኪ ምስ ፈለጥኪ ብዝቐልጠፈ ናብ ጥዕና ጣብያ ምኻድ የድሊ..."
}
```

---

## 🚀 Step 2: Validate the LoRA Configuration (Dry-Run)
Before downloading multi-gigabyte weights or starting hours of GPU compute, verify the dataset and LoRA parameter mapping:
```powershell
.venv\Scripts\python -m training.finetune_lora --dry_run
```
✅ Result:
```text
Loaded: 66 train, 8 val samples.
Configured LoRA: rank=16, alpha=32, target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', ...]
✅ DRY-RUN SUCCESS: Dataset and LoRA configuration fully validated!
```

---

## 💻 Step 3: Run Full Training

### Recommended Base Models for Voice / 2G Phone Calls
Because phone calls require **low latency** (< 1.5 seconds response time), lightweight models are best:
1. **`Qwen/Qwen2.5-1.5B-Instruct`** (Recommended: Superb multilingual tokenization, fast CPU/GPU inference)
2. **`google/gemma-2-2b-it`** (Excellent medical reasoning)
3. **`meta-llama/Llama-3.2-1B-Instruct`** (Ultra-compact, runs on low-cost servers)

### To train locally (if GPU available):
```powershell
.venv\Scripts\python -m training.finetune_lora --base_model "Qwen/Qwen2.5-1.5B-Instruct" --epochs 3 --batch_size 2 --lr 2e-4
```

### To train on Google Colab (Free T4 GPU):
You can upload `data/training_data/train.jsonl` and run in 10 minutes on a free Colab GPU!

---

## 🩺 Step 4: Test Inference with Fine-Tuned Weights
Test your model with spoken inquiries:
```powershell
.venv\Scripts\python -m training.infer_finetuned --query "ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?"
```
```powershell
.venv\Scripts\python -m training.infer_finetuned --query "ጥንስቲ እየ ደም ፈሲሱኒ ኣሎ"
```
The engine evaluates danger signs first, then generates or retrieves verified doctor advice.
