# Mkri Hakaym (ምኽሪ ሓካይም)
### Voice-First Medical AI for Low-Literacy & Basic 2G Feature Phones in Tigrinya

> Grounded on verified medical advice broadcasts from **Tigrai Television's "ማዕዳ ሓካይም"** (Doctors' Advice).

---

## 🎯 Vision & Problem Solved
In many rural and semi-urban communities:
1. **Digital Literacy Gap**: Many individuals cannot read text-based apps, search Google, or navigate complex smartphone interfaces.
2. **Connectivity Barrier**: Many mothers and families only have basic **2G button phones** ("small phones", dumbphones) with no internet or 4G data.
3. **Misinformation vs. Trusted Advice**: Unvetted advice can be dangerous. Grounding AI on verified local healthcare programs—like Tigrai TV's *"ማዕዳ ሓካይም"*—delivers culturally attuned, accurate medical guidance in native **ትግርኛ (Tigrinya)**.
4. **Strictly Grounded, No Synthetic Data**: Clinical knowledge is transcribed directly from real broadcast speech by certified physicians, eliminating clinical hallucinations.

---

## 🏗️ Architecture Overview

```
                      [Basic 2G Phone (Dumbphone)]
                                  │
                                  ▼ (Standard Phone Call / Audio)
                  [Telephony Gateway (Twilio / Asterisk SIP)]
                                  │
       ┌──────────────────────────┴──────────────────────────┐
       ▼                                                     ▼
 [Keypad DTMF Fallback]                             [Audio Voice Stream]
 (Press 1 for Pregnancy, 2 for Child Health)                 │
                                                             ▼
                                                [Tigrinya Speech-to-Text (ASR)]
                                                (Meta MMS-1B / Whisper)
                                                             │
                                                             ▼
                                              ┌──────────────────────────────┐
                                              │  Clinical Triage & RAG Brain │
                                              │   • Red Flag Detector        │
                                              │   • "ማዕዳ ሓካይም" Knowledge Base │
                                              └──────────────┬───────────────┘
                                                             │
                                                             ▼
                                                [Tigrinya Spoken Doctor Voice]
                                                (Meta MMS-TTS / Audio Out)
```

---

## 📁 Repository Structure

```
mkri_hakaym/
├── app.py                             # Streamlit interactive Web UI (Phone Simulator, Knowledge Explorer, CSV Manager)
├── config.py                          # Central configurations, emergency terms, language codes
├── demo_call.py                       # Interactive 2G phone call simulator (terminal)
├── run_doctor.py                      # Clinical evaluation harness across real emergency scenarios
├── requirements.txt                   # Project dependencies
│
├── brain/                             # Clinical Intelligence & Guardrails
│   ├── triage_rules.py                # Red-flag detector (ቀያሕቲ ምልክታት) with Tigrinya morphological regex
│   └── rag_engine.py                  # Grounded retrieval engine over verified broadcast entries
│
├── collector/                         # YouTube Ingestion & ASR Transcription
│   ├── transcribe_broadcast_to_qa.py  # End-to-end YouTube audio downloader -> Meta MMS ASR -> CSV compiler
│   ├── colab_single_transcribe.py     # Standalone Colab script for GPU ASR transcription
│   ├── transcribe_youtube_colab.ipynb # Interactive Colab Notebook for 1-click GPU transcription
│   ├── build_qa_csv.py                # Dataset builder & schema validator for medical_qa_dataset.csv
│   ├── youtube_crawler.py             # Tigrai TV episode crawler & cataloger
│   └── video_list.txt                 # Seed list of Tigrai TV "ማዕዳ ሓካይም" medical broadcasts
│
├── data/
│   ├── medical_qa_dataset.csv         # Verified clinical Q&A dataset (UTF-8-SIG for Excel & pandas)
│   ├── medical_qa_dataset.json        # Structured JSON dataset
│   ├── knowledge_base/                # Structured clinical markdown articles
│   ├── audio/                         # Raw audio broadcasts
│   └── transcripts/                   # Raw & timed Tigrinya speech transcripts
│
├── telephony/                         # 2G Telephony & Audio Synthesis
│   ├── ivr_server.py                  # FastAPI Webhooks for Asterisk / Twilio voice calls
│   └── audio_service.py               # Meta MMS-TTS (facebook/mms-tts-tir) audio generator & cache
│
├── training/                          # Fine-Tuning Pipeline (Qwen2.5-1.5B-Instruct)
│   ├── finetune_lora.py               # PEFT / LoRA training script with trl.SFTTrainer
│   ├── prepare_dataset.py             # Prepares train.jsonl and val.jsonl in ChatML format
│   ├── infer_finetuned.py             # Inference pipeline with triage safety guardrails
│   ├── colab_single_script.py         # Self-contained training script for Google Colab T4 GPU
│   ├── fine_tune_mkri_hakaym_colab.ipynb # Colab Notebook for LoRA fine-tuning
│   └── FINETUNING_GUIDE.md            # Comprehensive fine-tuning documentation
│
└── tests/
    └── test_gateway.py                # Automated test suite (all 5 core modules verified)
```

---

## 🚀 Quickstart & Testing

### 1. Launch the Streamlit Web Application
An interactive dashboard with a phone call simulator, knowledge explorer, triage red-flags viewer, and dataset editor:
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

### 2. Run the 2G Voice Call Simulator (Terminal)
Experience what a mother on a basic 2G phone hears when calling into the system:
```bash
python demo_call.py
```

### 3. Run the Clinical Evaluation Harness
Verify triage accuracy across emergency, urgent, and routine clinical queries:
```bash
python run_doctor.py
```

### 4. Run the Telephony / IVR Webhook Server
Start the Asterisk / Twilio voice webhook server:
```bash
python -m uvicorn telephony.ivr_server:app --host 0.0.0.0 --port 8000
```
- Interactive API Docs: `http://localhost:8000/docs`
- Inbound Call Webhook: `POST /voice/inbound`
- Keypad DTMF Menu: `POST /voice/menu`
- JSON Doctor API: `POST /api/ask`

### 5. Run the Automated Tests
```bash
python -m tests.test_gateway
```

---

## 🎙️ YouTube Transcription & Dataset Collection

To transcribe real medical broadcasts from Tigrai TV without synthetic generation:

```bash
# Transcribe pregnancy broadcast (2FHD7FWWYNc) into medical_qa_dataset.csv
python -m collector.transcribe_broadcast_to_qa --url "https://www.youtube.com/watch?v=2FHD7FWWYNc"
```
Or use the **[Google Colab Notebook](collector/transcribe_youtube_colab.ipynb)** on a free T4 GPU to transcribe a 60-minute video in ~3 minutes.

---

## 🧠 Model Fine-Tuning (Qwen2.5-1.5B-Instruct)

Fine-tune the model on the clinical Q&A dataset with PEFT / LoRA:

```bash
# 1. Prepare ChatML format datasets
python -m training.prepare_dataset

# 2. Train LoRA adapter
python -m training.finetune_lora --base_model "Qwen/Qwen2.5-1.5B-Instruct" --epochs 3 --batch_size 2

# 3. Test inference with safety guardrails
python -m training.infer_finetuned --query "ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?"
```
For 1-click cloud training, see [`training/fine_tune_mkri_hakaym_colab.ipynb`](training/fine_tune_mkri_hakaym_colab.ipynb).

---

## 🚨 Safety & Clinical Ethics
* **Zero Hallucination Tolerance**: The system does NOT invent medications or dosages.
* **Immediate Red-Flag Interrupt**: If symptoms like *ምፍሳስ ደም* (vaginal bleeding), *ብርቱዕ ርእሲ ሕማም* (severe headache/preeclampsia), or *ዕሸል ምንቅስቓስ ምቁራጽ* (reduced fetal movement) are detected, the AI interrupts and instructs the caller to proceed immediately to the nearest health post or hospital.
* **Human Operator Handoff**: Dialing `0` routes the caller directly to an on-duty community health worker or nurse.

---

## 📄 License & Attribution
Grounded in medical knowledge broadcast by **Tigrai Television's *ማዕዳ ሓካይም***.
Developed for humanitarian, public health, and non-commercial educational use.
