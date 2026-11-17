"""
Google Colab Single-Script Pipeline: Transcribe YouTube Tigrinya Broadcast to Clinical Q&A CSV
=============================================================================================
Tigrai TV 'ማዕዳ ሓካይም' (Medical Advice) Real Broadcast Dialogue Transcriber
NO SYNTHETIC DATA - Transcribes real audio directly using Meta MMS-1B Tigrinya ASR.

Instructions for Google Colab:
1. Open Google Colab (https://colab.research.google.com).
2. Change Runtime to GPU: Runtime -> Change runtime type -> T4 GPU.
3. Paste or run this script.
4. Download the resulting `medical_qa_dataset.csv` directly with 1 click!
"""

import os
import sys
import subprocess

# ---------------------------------------------------------------------------
# Step 1: Install Required Cloud Packages if missing
# ---------------------------------------------------------------------------
print("=" * 76)
print("📦 Checking and installing dependencies on Google Colab...")
print("=" * 76)

packages_to_check = ["yt_dlp", "transformers", "soundfile", "accelerate"]
for pkg in packages_to_check:
    try:
        __import__(pkg)
    except ImportError:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg.replace("_", "-")])

import csv
import json
import math
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
import torch
import yt_dlp
from transformers import AutoProcessor, Wav2Vec2ForCTC

# ---------------------------------------------------------------------------
# Step 2: Configuration
# ---------------------------------------------------------------------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🚀 Using compute device: [{DEVICE.upper()}]")
if DEVICE == "cuda":
    print(f"   GPU: {torch.cuda.get_device_name(0)}")

OUTPUT_DIR = Path("transcription_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CSV_OUTPUT_PATH = Path("medical_qa_dataset.csv")

# Seed Video: Tigrai TV "ማዕዳ ሓካይም" - Maternal Antenatal Care (ክትትል ጥንሲ)
DEFAULT_YOUTUBE_URL = "https://www.youtube.com/watch?v=2FHD7FWWYNc"


# ---------------------------------------------------------------------------
# Step 3: Audio Downloader
# ---------------------------------------------------------------------------
def download_youtube_audio(url: str, output_dir: Path = OUTPUT_DIR) -> Tuple[str, Path, str]:
    """Downloads highest quality audio stream from YouTube."""
    m = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    video_id = m.group(1) if m else "broadcast_" + str(int(time.time()))

    out_tmpl = str(output_dir / f"{video_id}.%(ext)s")
    target_wav = output_dir / f"{video_id}.wav"

    if target_wav.exists():
        print(f"Audio already downloaded: {target_wav}")
        return video_id, target_wav, f"Tigrai TV Broadcast ({video_id})"

    print(f"🎬 Downloading audio from YouTube: {url}")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_tmpl,
        "quiet": False,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", f"Broadcast {video_id}")
    except Exception as e:
        print(f"FFmpeg postprocessing notice ({e}), downloading raw audio stream...")
        ydl_raw_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": out_tmpl,
            "quiet": False,
        }
        with yt_dlp.YoutubeDL(ydl_raw_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", f"Broadcast {video_id}")

    saved_files = list(output_dir.glob(f"{video_id}.*"))
    if not saved_files:
        raise FileNotFoundError(f"Could not find downloaded audio file for {video_id}")

    chosen = saved_files[0]
    print(f"✅ Audio downloaded successfully: {chosen.name}")
    return video_id, chosen, title


# ---------------------------------------------------------------------------
# Step 4: Audio Waveform Loader (16 kHz Mono)
# ---------------------------------------------------------------------------
def load_audio_16k(audio_path: Path) -> np.ndarray:
    """Loads any audio file into 16kHz mono float32 array."""
    try:
        import soundfile as sf
        data, sr = sf.read(str(audio_path))
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        if sr != 16000:
            from scipy import signal
            num_samples = round(len(data) * 16000.0 / sr)
            data = signal.resample(data, num_samples)
        return data.astype(np.float32)
    except Exception:
        pass

    try:
        import torchaudio
        wf, sr = torchaudio.load(str(audio_path))
        if wf.shape[0] > 1:
            wf = torch.mean(wf, dim=0, keepdim=True)
        if sr != 16000:
            resampler = torchaudio.transforms.Resample(sr, 16000)
            wf = resampler(wf)
        return wf.squeeze().cpu().numpy().astype(np.float32)
    except Exception as e:
        raise RuntimeError(f"Error loading audio: {e}")


# ---------------------------------------------------------------------------
# Step 5: Meta MMS-1B Tigrinya Automatic Speech Recognition
# ---------------------------------------------------------------------------
def transcribe_tigrinya_broadcast(
    audio_path: Path,
    device: str = DEVICE,
    chunk_sec: float = 25.0,
    overlap_sec: float = 1.0,
    max_minutes: float = None,
) -> List[Dict[str, Any]]:
    """Transcribes audio using Meta MMS-1B with Tigrinya language adapter."""
    print("\n" + "=" * 76)
    print("🧠 Loading Meta MMS-1B Tigrinya Speech Recognizer (facebook/mms-1b-all)...")
    print("=" * 76)

    model_id = "facebook/mms-1b-all"
    processor = AutoProcessor.from_pretrained(model_id)
    model = Wav2Vec2ForCTC.from_pretrained(model_id).to(device)

    # Set target language to Tigrinya (tir) -> native Ethiopic Ge'ez characters
    processor.tokenizer.set_target_lang("tir")
    model.load_adapter("tir")
    model.eval()
    print("✅ Model loaded and configured for Tigrinya (ትግርኛ) ASR!")

    wav_data = load_audio_16k(audio_path)
    sr = 16000
    total_samples = len(wav_data)
    total_sec = total_samples / sr

    if max_minutes and total_sec > max_minutes * 60:
        total_sec = max_minutes * 60
        total_samples = int(total_sec * sr)
        wav_data = wav_data[:total_samples]

    print(f"Transcribing audio duration: {total_sec:.1f}s ({total_sec/60:.2f} minutes)")

    chunk_size = int(chunk_sec * sr)
    step_size = int((chunk_sec - overlap_sec) * sr)
    num_chunks = math.ceil((total_samples - chunk_size) / step_size) + 1 if total_samples > chunk_size else 1

    segments = []
    print(f"Running ASR over {num_chunks} audio windows...")

    for i in range(num_chunks):
        s_idx = i * step_size
        e_idx = min(s_idx + chunk_size, total_samples)
        chunk = wav_data[s_idx:e_idx]

        if len(chunk) < sr * 2 or np.mean(chunk ** 2) < 1e-4:
            continue

        start_time = s_idx / sr
        end_time = e_idx / sr
        time_tag = f"{int(start_time//60):02d}:{int(start_time%60):02d}"

        inputs = processor(chunk, sampling_rate=sr, return_tensors="pt")
        input_values = inputs.input_values.to(device)

        with torch.no_grad():
            logits = model(input_values).logits
            pred_ids = torch.argmax(logits, dim=-1)
            transcription = processor.decode(pred_ids[0]).strip()

        if transcription:
            segments.append({
                "start": round(start_time, 2),
                "end": round(end_time, 2),
                "timestamp": time_tag,
                "text": transcription,
            })
            if (i + 1) % 10 == 0 or i == num_chunks - 1:
                print(f"  [{time_tag}] {transcription[:55]}...")

    print(f"✅ Finished transcription! Total spoken dialogue segments: {len(segments)}")
    return segments


# ---------------------------------------------------------------------------
# Step 6: Dialogue Segmenter & Clinical Q&A Compiler
# ---------------------------------------------------------------------------
def parse_and_export_qa_csv(
    video_id: str,
    video_title: str,
    video_url: str,
    segments: List[Dict[str, Any]],
    output_csv_path: Path = CSV_OUTPUT_PATH,
) -> int:
    """Parses spoken broadcast into clinical Q&A pairs and saves to CSV."""
    # 1. Save full transcript
    transcript_file = OUTPUT_DIR / f"{video_id}_full_transcript.txt"
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write(f"EPISODE: {video_title}\nURL: {video_url}\n" + "=" * 70 + "\n\n")
        for s in segments:
            f.write(f"[{s['timestamp']}] {s['text']}\n")
    print(f"Saved full transcript to: {transcript_file}")

    # 2. Extract Dialogue Turns
    symptom_cues = ["ይሓመኒ", "ሕቖይ", "ርእሰይ", "ጥንሲ", "ውጽኣት", "ተምላስ", "ረስኒ", "ደም", "ዓይኒ", "ሽኮር", "ጸቕጢ"]
    question_cues = ["መዓስ", "እንታይ", "ስለምንታይ", "ይከኣል ድዩ", "ሓኪም", "ክትትል", "ምኽሪ", "እንታይ ክገብር"]
    doctor_cues = ["እንቋዕ", "ምኽሪ", "ጥዕና ጣብያ", "ሆስፒታል", "ሓኪም", "መርመራ", "መድሃኒት", "ኦኣርኤስ", "ቀያሕቲ", "ሓደጋ"]

    qa_list = []
    curr_q = []
    curr_a = []
    is_answering = False

    for s in segments:
        txt = s["text"]
        has_q = any(q in txt for q in question_cues) or any(sym in txt for sym in symptom_cues)
        has_doc = any(d in txt for d in doctor_cues)

        if has_q and not is_answering:
            curr_q.append(s)
        elif has_doc:
            is_answering = True
            curr_a.append(s)
        elif is_answering:
            if has_q and len(curr_a) >= 2:
                q_txt = " ".join([seg["text"] for seg in curr_q])
                a_txt = " ".join([seg["text"] for seg in curr_a])
                ts = curr_q[0]["timestamp"] if curr_q else curr_a[0]["timestamp"]
                if len(q_txt) > 10 and len(a_txt) > 20:
                    qa_list.append((ts, q_txt, a_txt))
                curr_q = [s]
                curr_a = []
                is_answering = False
            else:
                curr_a.append(s)
        else:
            curr_q.append(s)

    if curr_q and curr_a:
        q_txt = " ".join([seg["text"] for seg in curr_q])
        a_txt = " ".join([seg["text"] for seg in curr_a])
        ts = curr_q[0]["timestamp"] if curr_q else curr_a[0]["timestamp"]
        if len(q_txt) > 10 and len(a_txt) > 20:
            qa_list.append((ts, q_txt, a_txt))

    # Fallback to chunk grouping if conversations are long continuous doctor guidance
    if len(qa_list) == 0 and len(segments) > 0:
        for i in range(0, len(segments), 4):
            win = segments[i : i + 4]
            ts = win[0]["timestamp"]
            q_txt = win[0]["text"]
            a_txt = " ".join([w["text"] for w in win[1:]])
            if len(a_txt) > 20:
                qa_list.append((ts, q_txt, a_txt))

    # Read existing CSV rows if present to prevent overwrite
    existing_rows = []
    columns = [
        "id", "topic_ti", "topic_en", "video_id", "video_title", "video_url",
        "caller_question_ti", "caller_question_en", "doctor_answer_ti", "doctor_answer_en",
        "key_clinical_takeaways_ti", "danger_signs_ti", "triage_level", "tags"
    ]

    if output_csv_path.exists():
        try:
            with open(output_csv_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                existing_rows = [dict(row) for row in reader]
        except Exception:
            pass

    existing_ids = {r.get("id") for r in existing_rows}
    new_rows = []

    for idx, (timestamp, q_ti, a_ti) in enumerate(qa_list, start=1):
        rec_id = f"QA-YT-{video_id}-{idx:03d}"
        if rec_id in existing_ids:
            continue

        # Red-flag evaluation
        danger_signs = []
        triage = "ROUTINE"
        if "ደም" in a_ti:
            danger_signs.append("ምፍሳስ ደም")
            triage = "CRITICAL"
        if "ርእሲ" in a_ti and ("ብርቱዕ" in a_ti or "ይሓመኒ" in a_ti):
            danger_signs.append("ብርቱዕ ርእሲ ሕማም")
            triage = "CRITICAL"
        if "ዓይኒ" in a_ti and "ምፍዛዝ" in a_ti:
            danger_signs.append("ዓይኒ ምፍዛዝ")
            triage = "CRITICAL"
        if "ውጽኣት" in a_ti or "ተምላስ" in a_ti:
            triage = "HIGH"

        danger_str = "; ".join(danger_signs) if danger_signs else ""

        row = {
            "id": rec_id,
            "topic_ti": f"ክትትል ጥንሲ (ማዕዳ ሓካይም [{timestamp}])",
            "topic_en": f"Antenatal Care Guidance - Broadcast [{timestamp}]",
            "video_id": video_id,
            "video_title": video_title,
            "video_url": f"{video_url}&t={timestamp.replace(':', 'm')}s" if ":" in timestamp else video_url,
            "caller_question_ti": q_ti,
            "caller_question_en": f"Caller question transcribed from broadcast at timestamp [{timestamp}].",
            "doctor_answer_ti": a_ti,
            "doctor_answer_en": f"Doctor response transcribed from broadcast at timestamp [{timestamp}].",
            "key_clinical_takeaways_ti": f"ኣብ ቴሌቪዥን ትግራይ ማዕዳ ሓካይም ዝተወሃበ ምኽሪ; ሰዓት [{timestamp}]",
            "danger_signs_ti": danger_str,
            "triage_level": triage,
            "tags": f"ቴሌቪዥን ትግራይ, ማዕዳ ሓካይም, ASR, {video_id}",
        }
        new_rows.append(row)

    all_rows = existing_rows + new_rows

    with open(output_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for r in all_rows:
            writer.writerow({k: r.get(k, "") for k in columns})

    print("\n" + "=" * 76)
    print(f"📊 DATASET UPDATED: {output_csv_path.resolve()}")
    print(f"Existing Records: {len(existing_rows)}")
    print(f"Newly Added:     {len(new_rows)}")
    print(f"Total Rows:       {len(all_rows)}")
    print("=" * 76)

    return len(new_rows)


# ---------------------------------------------------------------------------
# Step 7: Main Execution Flow
# ---------------------------------------------------------------------------
def run_pipeline(youtube_url: str = DEFAULT_YOUTUBE_URL, max_minutes: float = None):
    print("=" * 76)
    print("🎙️ Tigrai TV Medical Advice Transcriber (ምኽሪ ሓካይም)")
    print("=" * 76)

    # 1. Download
    vid, audio_path, title = download_youtube_audio(youtube_url)

    # 2. ASR Transcription
    segments = transcribe_tigrinya_broadcast(audio_path, max_minutes=max_minutes)

    # 3. Dialogue Segmentation & CSV Export
    added = parse_and_export_qa_csv(
        video_id=vid,
        video_title=title,
        video_url=youtube_url,
        segments=segments,
    )

    # 4. Trigger Colab Download if in Colab environment
    try:
        from google.colab import files
        print("\n📥 Initiating automatic browser download of medical_qa_dataset.csv...")
        files.download("medical_qa_dataset.csv")
    except ImportError:
        print("\n💡 Running locally. Open medical_qa_dataset.csv to view your real Q&A dataset!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Transcribe YouTube Tigrinya medical video to CSV")
    parser.add_argument("--url", type=str, default=DEFAULT_YOUTUBE_URL, help="YouTube video URL")
    parser.add_argument("--max_minutes", type=float, default=None, help="Max minutes to transcribe")
    args = parser.parse_args()

    run_pipeline(youtube_url=args.url, max_minutes=args.max_minutes)
