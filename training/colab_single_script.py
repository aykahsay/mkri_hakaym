"""
Mkri Hakaym (ምኽሪ ሓካይም) - Single Script for Google Colab T4 GPU
Fine-tunes Qwen2.5-1.5B-Instruct on verified Tigrinya medical Q&A with 4-bit QLoRA.
"""
import json
import shutil
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import (
    LoraConfig,
    get_peft_model,
    TaskType,
    prepare_model_for_kbit_training,
)
from trl import SFTTrainer, SFTConfig

# =====================================================================
# 1. Dataset in Tigrinya
# =====================================================================
raw_entries = [
    {
        "instruction": "ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ወይ ጥዕና ጣብያ ክኸይድ ዝግብኣኒ?",
        "output": "እንቋዕ ሓጎሰኪ! ጥንሲ ከምዝሓዝኪ ምስ ፈለጥኪ ብዝቐልጠፈ ናብ ጥዕና ጣብያ ምኻድ የድሊ። ብፍላይ ኣብ ውሽጢ ቀዳሞት 12 ሰሙናት (3 ኣዋርሕ) ቀዳማይ ዑደት ክትትል ጥንሲ (ANC) ክጅምር ኣለዎ። ኣብ ምሉእ ጥንሲ ድማ እንተወሓደ 4 ክሳብ 8 ግዜ ክትትል ክግበር ይመከር።"
    },
    {
        "instruction": "ጥንስቲ እንታይ ዓይነት ምግቢ ክትበልዕ ኣለዋ? ክኒን ሓጺን (Iron) ምውሳድ ኣገዳሲ ድዩ?",
        "output": "ጥንስቲ ኣደ ንዓርሳን ንዕሸላን ዝኸውን ዝተመጣጠነ መግቢ ክትረክብ ኣለዋ። ብፍላይ ድማ ኣሕምልቲ፣ ፍረታታት፣ ጥረ-ምረ፣ እንቁላል፣ ስጋን ጸባን ኣገደስቲ እዮም። ካብዚ ብተወሳኺ ሕጽረት ደም ንኸየጋጥም ክኒን ኣይረን (Iron) ከምኡ'ውን ፎሊክ ኣሲድ (Folic Acid) ብመሰረት መምርሒ ሓኪም ብቐጻሊ ክውሰድ ኣለዎ። ብዘይ መምርሒ ሓኪም ካልኦት መድሓኒታት ምውሳድ ግን ንዕሸል ሓደገኛ እዩ።"
    },
    {
        "instruction": "ጥንስቲ እየ፤ ደም ፈሲሱኒ ኣሎ እንታይ ክገብር?",
        "output": "ኣድህቡ! ኣብ እዋን ጥንሲ ምፍሳስ ደም ቀይሕ ምልክት (ሓደጋ) እዩ። ብቕጽበት ናብ ዝቐረበ ሆስፒታል ወይ ጥዕና ጣብያ ኪዱ! ኣብ ገዛ ደው ኣይትበሉ!"
    },
    {
        "instruction": "ርእሰይ ብርቱዕ ይሓመኒ ኣሎ ዓይነይ ድማ ይፈዝዝ ኣሎ",
        "output": "ብርቱዕ ርእሲ ሕማም ምስ ዓይኒ ምፍዛዝ ኣብ ጥንሲ ምልክት ልዑል ጸቕጢ ደም (Pre-eclampsia) ክኸውን ስለዝኽእል ቀጥታ ናብ ጥዕና ጣብያ ብምኻድ ጸቕጢ ደምኩም ተመርመሩ።"
    },
    {
        "instruction": "ህጻን ውጽኣትን ተምላስን እንተኣጋጢምዎ ኣብ ገዛ እንታይ ክንገብረሉ ይግባእ?",
        "output": "ኣብ ህጻናት ውጽኣት ምስ ዘጋጥም ዝዓበየ ሓደጋ ምውዳእ ማይ ኣብ ሰብነት (Dehydration) እዩ። ስለዚ ብቕጽበት ኣብ ገዛ ኦ.ኣር.ኤስ (ORS) ኣብ 1 ሊትሮ ዝፈልሐ ዝቐዘቐዘ ማይ ብምብጥባጥ ብማንካ ወይ ብኩባያ እናተዛወረ ክወሃብ ኣለዎ። ጡብ ምጥባው ከየቋረጸ ክቕጽል ኣለዎ።"
    },
    {
        "instruction": "ህጻን ሰዓልን ምሕጻር እስትንፋስን እንተሃልይዎ?",
        "output": "ህጻን ሰዓል እንተሃልይዎ ብፍላይ ድማ ኣተነፋፍስኡ ካብቲ ልሙድ ፈጣን እንተኾይኑ ወይ ደረቱ ናብ ውሽጢ እንተተሳሒቡ፣ እዚ ናይ ነድሪ ሳምባ (Pneumonia) ምልክት እዩ። ብህጹጽ ናብ ዝቐረበ ጥዕና ጣብያ ክውሰድ ኣለዎ።"
    },
    {
        "instruction": "ኩላሊትና ጥዕናኡ ንኽሕሉ እንታይ ክንገብር ኣለና?",
        "output": "ኩላሊት ካብ ሰብነትና ጎዳእቲ ነገራትን ርስሓትን ዘጽሪ ኣገዳሲ ክፍሊ ሰብነትና እዩ። ጥዕና ኩላሊት ንምሕላው፡ መዓልታዊ እኹል ማይ ምስታይ (2-3 ሊትሮ)፤ ኣብ መግቢ ጨው ምቕናስ፤ ብዘይ መምርሒ ሓኪም ናይ ቃንዛ መዐገሲ ክኒናት (NSAIDs) ዘይምውሳድ፤ ከምኡ'ውን ጸቕጢ ደምን ሽኮርን ብቐጻሊ ምምርማር የድሊ።"
    },
    {
        "instruction": "ምልክታት ሕማም ሽኮር እንታይ እዮም?",
        "output": "ቀንድታት ምልክታት ሕማም ሽኮር፡ ተደጋጋሚ ጽምኢ ማይ፣ ተደጋጋሚ ምሻን (ብፍላይ ብለይቲ)፣ ብርቱዕ ጥሜት መግቢ፣ ከምኡ'ውን ብዘይ ምኽንያት ክብደት ምቕናስ እዮም። ሕማም ሽኮር ዘለዎ ሰብ መዓልታዊ ኣካላዊ ምንቅስቓስ ክገብር፣ ሽኮርን ጣፋጭ ምግብታትን ክቕንስ፣ መድሃኒቱ ብስርዓት ክወስድ ይግባእ።"
    },
    {
        "instruction": "ልዑል ጸቕጢ ደም ንምንታይ ስቕተኛ ቀታሊ ይበሃል?",
        "output": "ልዑል ጸቕጢ ደም መብዛሕትኡ ግዜ ዝኾነ ምልክት ከየርኣየ ንልቢ፣ ኩላሊትን ሓንጎልን (ስትሮክ) ስለዘጥቅዕ ስቕተኛ ቀታሊ ይበሃል። ስለዚ ነፍሲ ወከፍ ሰብ ጸቕጢ ደሙ ብቐጻሊ ክምርመር ይግባእ። ንምክልኻሉ ጨው ምቕናስ፣ ካብ ሽጋራን ኣልኮልን ምዕቃብ፣ ክብደት ምቕናስን መድሃኒት ጸቕጢ ደም ብዘይ ምቁራጽ ምውሳድን ኣገዳሲ እዩ።"
    }
]

SYSTEM_MSG = "ንስኻ ሓኪም 'ምኽሪ ሓካይም' ኢኻ። ብትግርኛ ግቡእ፣ ርህሩህን ስነ-ፍልጠታዊን ናይ ጥዕና ምኽሪ ትህብ። ዝኾነ ቀይሕ ምልክት (ሓደጋ) እንተጋጢሙ ብቕጽበት ናብ ጥዕና ጣብያ ወይ ሆስፒታል ክኸዱ ምዕድ።"

augmented_samples = []
prefixes = ["", "ሰላም ዶክተር፡ ", "በይዞም ዶክተር ክሓተኩም ደልየ፡ ", "ሓደ ሓበሬታ ምደለኹ፡ "]
for item in raw_entries:
    for p in prefixes:
        augmented_samples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user", "content": p + item["instruction"]},
                {"role": "assistant", "content": item["output"]}
            ]
        })

hf_dataset = Dataset.from_list(augmented_samples)
print(f"✅ Prepared {len(hf_dataset)} conversational training samples!")

# =====================================================================
# 2. Model & Tokenizer (4-bit QLoRA)
# =====================================================================
model_id = "Qwen/Qwen2.5-1.5B-Instruct"
print(f"Loading {model_id} in 4-bit...")

tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

model.config.use_cache = False
model = prepare_model_for_kbit_training(
    model,
    use_gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False}
)
model.enable_input_require_grads()

peft_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    bias="none",
)

model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

# =====================================================================
# 3. Training with SFTTrainer
# =====================================================================
def apply_chat_template_fn(example):
    return {"text": tokenizer.apply_chat_template(example["messages"], tokenize=False)}

formatted_dataset = hf_dataset.map(apply_chat_template_fn)

sft_config = SFTConfig(
    output_dir="./qwen_mkri_hakaym",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    num_train_epochs=3,
    logging_steps=5,
    fp16=True,
    dataset_text_field="text",
    max_seq_length=512,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    report_to="none",
)

trainer = SFTTrainer(
    model=model,
    train_dataset=formatted_dataset,
    peft_config=peft_config,
    args=sft_config,
)

print("\n🚀 Starting Qwen2.5-1.5B Training on Tigrinya Medical Advice...")
trainer.train()

output_adapter_dir = "./mkri_hakaym_qwen_adapter"
model.save_pretrained(output_adapter_dir)
tokenizer.save_pretrained(output_adapter_dir)
print(f"\n✅ LoRA adapter successfully saved to {output_adapter_dir}!")

# =====================================================================
# 4. Interactive Tigrinya Inference Test
# =====================================================================
def ask_doctor(query: str):
    messages = [
        {"role": "system", "content": SYSTEM_MSG},
        {"role": "user", "content": query}
    ]
    prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
    stop_token_ids = [tokenizer.eos_token_id, tokenizer.convert_tokens_to_ids("<|im_end|>")]
    
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.3,
            top_p=0.9,
            repetition_penalty=1.1,
            do_sample=True,
            eos_token_id=stop_token_ids,
            pad_token_id=tokenizer.pad_token_id,
        )
    gen_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
    reply = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
    print("=" * 65)
    print(f"👤 Caller: {query}")
    print(f"🩺 Doctor: {reply}")

print("\n--- Testing Model Output in Tigrinya ---")
ask_doctor("ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?")
ask_doctor("ጥንስቲ እየ ደም ፈሲሱኒ እንታይ ክገብር?")
ask_doctor("ህጻን ውጽኣትን ተምላስን እንተኣጋጢምዎ እንታይ ክንገብር?")

# =====================================================================
# 5. Zip & Export Adapter
# =====================================================================
shutil.make_archive("mkri_hakaym_qwen_adapter", "zip", output_adapter_dir)
print("\n🎉 Created mkri_hakaym_qwen_adapter.zip successfully!")
try:
    from google.colab import files
    files.download("mkri_hakaym_qwen_adapter.zip")
except ImportError:
    pass
