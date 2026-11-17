"""
Configuration and constants for Mkri Hakaym (ምኽሪ ሓካይም)
Voice-First Medical AI for Low-Literacy & Basic Phone Users
"""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
METADATA_DIR = DATA_DIR / "raw_metadata"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
KB_DIR = DATA_DIR / "knowledge_base"

# Ensure runtime directories exist
for p in [AUDIO_DIR, METADATA_DIR, TRANSCRIPTS_DIR, KB_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# YouTube Crawling Configuration
YOUTUBE_SEED_URLS = [
    "https://www.youtube.com/watch?v=2FHD7FWWYNc",  # ማዕዳ ሓካይም ፡ ዛዕባ፦ክትትል ጥንሲ (Pregnancy Follow-up)
]

TIGRAI_TV_CHANNEL = "https://www.youtube.com/@TigraiTv"

SEARCH_QUERIES = [
    "ማዕዳ ሓካይም",
    "ምኽሪ ሓካይም ቴሌቪዥን ትግራይ",
    "ማዕዳ ሓካይም ክትትል ጥንሲ",
    "ማዕዳ ሓካይም ኩላሊት",
    "ማዕዳ ሓካይም ሽኮር",
    "ማዕዳ ሓካይም ልቢ",
]

# Audio Configuration
SAMPLE_RATE_TRAIN = 16000  # Standard for Whisper/MMS speech recognition
SAMPLE_RATE_TELEPHONY = 8000  # Standard for 2G / G.711 / PSTN phone lines

# Language
LANGUAGE_CODE = "ti"  # Tigrinya
LANGUAGE_NAME = "ትግርኛ"

# Clinical Emergency / Red-Flag Keywords (ቀያሕቲ ምልክታት)
# Used for instantaneous triage interrupt during telephone calls
RED_FLAG_CONDITIONS = {
    "maternal_bleeding": {
        "keywords": ["ደም", "ምፍሳስ ደም", "ደም ምፍሳስ", "bleeding"],
        "severity": "CRITICAL",
        "action_ti": "ብህጹጽ ናብ ዝቐረበ ሆስፒታል ወይ ጥዕና ጣብያ ኪዱ! እዚ ቀይሕ ምልክት እዩ። ደው ኣይትበሉ!",
    },
    "severe_pregnancy_headache_hypertension": {
        "keywords": ["ብርቱዕ ርእሲ ሕማም", "ዕንቅርቢት", "ዓይኒ ምፍዛዝ", "ዓይኒ ዘይምርኣይ", "መንቀጥቀጥ"],
        "severity": "CRITICAL",
        "action_ti": "እዚ ምልክት ጸቕጢ ደም ጥንሲ (Pre-eclampsia) ክኸውን ስለ ዝኽእል ቀጥታ ናብ ሓኪም ኪዱ።",
    },
    "reduced_fetal_movement": {
        "keywords": ["ምንቅስቓስ ዕሸል ምቁራጽ", "ዕሸል ኣይተንቀሳቐሰን", "ምንቅስቓስ ምቕናስ"],
        "severity": "HIGH",
        "action_ti": "ዕሸል ምንቅስቓስ ምስ ዘቋርጽ ብቕጽበት መርመራ የድሊ።",
    },
    "difficulty_breathing": {
        "keywords": ["ምሕጻር እስትንፋስ", "ምትንፋስ ምእባይ", "እስትንፋስ ምቁራጽ"],
        "severity": "CRITICAL",
        "action_ti": "ብህጹጽ ኦክስጅንን ናይ ሓኪም ክትትልን የድልየኩም!",
    },
}
