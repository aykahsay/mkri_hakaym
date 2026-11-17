"""
Dataset Preparation for Fine-Tuning Mkri Hakaym (ምኽሪ ሓካይም).
Compiles verified doctor Q&A into instruction-tuning datasets (train.jsonl, val.jsonl)
with synthetic dialect variations, clinical guardrails, and triage protocols.
"""
import json
import random
from pathlib import Path
from typing import List, Dict, Any

from config import DATA_DIR, KB_DIR

TRAIN_DATA_DIR = DATA_DIR / "training_data"
TRAIN_DATA_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT_TI = (
    "ንስኻ ሓኪም 'ምኽሪ ሓካይም' ኢኻ። ብትግርኛ ግቡእ፣ ርህሩህን ስነ-ፍልጠታዊን ናይ ጥዕና ምኽሪ ትህብ። "
    "ዝኾነ ቀይሕ ምልክት (ሓደጋ) እንተጋጢሙ ብቕጽበት ናብ ጥዕና ጣብያ ወይ ሆስፒታል ክኸዱ ምዕድ። "
    "ብዘይ መምርሒ ሓኪም መድሃኒታት ኣይተኣዝዝን።"
)

# Colloquial caller phrasing augmentations (how callers naturally ask on the phone)
QUERY_AUGMENTATIONS = [
    lambda q: f"ሰላም ዶክተር፡ {q}",
    lambda q: f"በይዞም ዶክተር ክሓተኩም ደልየ፡ {q}",
    lambda q: f"ሓደ ሓበሬታ ምደለኹ፡ {q}",
    lambda q: f"{q} እንታይ ክገብር ይግባእ?",
    lambda q: f"{q} መፍትሒኡ እንታይ እዩ?",
]


def load_all_kb_entries() -> List[Dict[str, Any]]:
    entries = []
    for f in KB_DIR.glob("*.json"):
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            if isinstance(data, list):
                entries.extend(data)
            elif isinstance(data, dict):
                entries.append(data)
    return entries


def create_instruction_dataset():
    kb_entries = load_all_kb_entries()
    print(f"Loaded {len(kb_entries)} base clinical entries from knowledge base.")

    dataset = []

    for item in kb_entries:
        base_q = item.get("question_ti", "")
        base_a = item.get("answer_ti", "")
        topic = item.get("topic", "")

        # 1. Base standard pair
        dataset.append({
            "system": SYSTEM_PROMPT_TI,
            "instruction": base_q,
            "input": f"ዛዕባ: {topic}",
            "output": base_a,
        })

        # 2. Add conversational augmentations (simulating phone callers)
        for aug in QUERY_AUGMENTATIONS:
            caller_variant = aug(base_q)
            dataset.append({
                "system": SYSTEM_PROMPT_TI,
                "instruction": caller_variant,
                "input": f"ቴሌፎን ደዋሊ: {caller_variant}",
                "output": base_a,
            })

    # 3. Add Clinical Triage & Red-Flag Training Samples
    red_flag_cases = [
        ("ጥንስቲ እየ ደም ፈሲሱኒ", "ኣድህቡ! ኣብ እዋን ጥንሲ ምፍሳስ ደም ቀይሕ ምልክት (ሓደጋ) እዩ። ብቕጽበት ናብ ዝቐረበ ሆስፒታል ወይ ጥዕና ጣብያ ኪዱ! ኣብ ገዛ ደው ኣይትበሉ!"),
        ("ርእሰይ ብርቱዕ ይሓመኒ ኣሎ ዓይነይ ድማ ይፈዝዝ ኣሎ", "ብርቱዕ ርእሲ ሕማም ምስ ዓይኒ ምፍዛዝ ኣብ ጥንሲ ምልክት ልዑል ጸቕጢ ደም (Pre-eclampsia) ክኸውን ስለዝኽእል ቀጥታ ናብ ጥዕና ጣብያ ብምኻድ ጸቕጢ ደምኩም ተመርመሩ።"),
        ("ዕሸል ምንቅስቓስ ኣቋሪጹኒ 2 መዓልቲ ገይሩ", "ዕሸል ምንቅስቓሱ እንተቋሪጹ ወይ ብርቱዕ እንተቀኒሱ፣ ብህጹጽ ናብ ጥዕና ጣብያ ብምኻድ ናይ ልቢ ትርግታ ዕሸል (Fetal Heartbeat) ክረጋገጽ ኣለዎ።"),
        ("ምሕጻር እስትንፋስን ሕማም ደረትን ኣሎኒ", "ምሕጻር እስትንፋስን ሕማም ደረትን ህጹጽ ሕክምናዊ ሓገዝ ዘድልዮ እዩ። ቀጥታ ናብ ህጹጽ ረድኤት (Emergency) ኪዱ።"),
    ]

    for rf_q, rf_a in red_flag_cases:
        for aug in QUERY_AUGMENTATIONS:
            variant = aug(rf_q)
            dataset.append({
                "system": SYSTEM_PROMPT_TI,
                "instruction": variant,
                "input": "ህጹጽ ሓደጋ (ቀይሕ ምልክት)",
                "output": rf_a,
            })

    # Shuffle and split into train (90%) and val (10%)
    random.seed(42)
    random.shuffle(dataset)

    split_idx = int(len(dataset) * 0.9)
    train_data = dataset[:split_idx]
    val_data = dataset[split_idx:]

    train_path = TRAIN_DATA_DIR / "train.jsonl"
    val_path = TRAIN_DATA_DIR / "val.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for ex in train_data:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for ex in val_data:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"Created instruction dataset:")
    print(f" - Train samples: {len(train_data)} -> {train_path}")
    print(f" - Val samples:   {len(val_data)} -> {val_path}")


if __name__ == "__main__":
    create_instruction_dataset()
