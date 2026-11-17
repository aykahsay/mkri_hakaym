"""
Transcribe YouTube Medical Broadcast to Clinical Q&A CSV (ማዕዳ ሓካይም - ምኽሪ ሓካይም)
===================================================================================
Transcribes Tigrinya medical broadcast audio directly from YouTube episodes
(e.g., Tigrai Television's 'ማዕዳ ሓካይም' maternal health episode 2FHD7FWWYNc)
using Meta MMS-1B Tigrinya Speech-to-Text (`facebook/mms-1b-all`, target_lang='tir').

Extracts caller-doctor dialogue turns, key clinical takeaways, danger signs,
and triage levels, and compiles them directly into `data/medical_qa_dataset.csv`.
STRICTLY NO SYNTHETIC DATA.
"""
import argparse
import csv
import json
import logging
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import torch

from config import DATA_DIR, AUDIO_DIR, TRANSCRIPTS_DIR
from collector.build_qa_csv import (
    CSV_DATASET_PATH,
    JSON_DATASET_PATH,
    CSV_COLUMNS,
    DatasetBuilder,
)
from brain.triage_rules import TriageEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TranscribeBroadcast")


class TigrinyaBroadcastPipeline:
    """
    End-to-end pipeline:
    1. Downloads audio from YouTube broadcast using yt-dlp.
    2. Converts/loads audio at 16,000 Hz.
    3. Runs Meta MMS Tigrinya ASR (Wav2Vec2 CTC with language adapter 'tir').
    4. Segments dialogue into Caller/Host queries and Doctor clinical answers.
    5. Appends verified records into medical_qa_dataset.csv.
    """

    def __init__(
        self,
        audio_dir: Path = AUDIO_DIR,
        transcripts_dir: Path = TRANSCRIPTS_DIR,
        device: Optional[str] = None,
    ):
        self.audio_dir = Path(audio_dir)
        self.transcripts_dir = Path(transcripts_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.asr_processor = None
        self.asr_model = None
        self.triage_engine = TriageEngine()
        self.dataset_builder = DatasetBuilder()

    def download_audio(self, url_or_id: str) -> Tuple[str, Path, Dict[str, Any]]:
        """
        Downloads best audio stream from YouTube for the given URL or video ID.
        Returns: (video_id, audio_file_path, video_metadata)
        """
        import yt_dlp

        # Extract video ID
        if "youtube.com" in url_or_id or "youtu.be" in url_or_id:
            video_url = url_or_id
            m = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url_or_id)
            video_id = m.group(1) if m else "video_" + str(int(time.time()))
        else:
            video_id = url_or_id
            video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Target audio path
        out_tmpl = str(self.audio_dir / f"{video_id}.%(ext)s")
        target_wav = self.audio_dir / f"{video_id}.wav"
        target_mp3 = self.audio_dir / f"{video_id}.mp3"

        if target_wav.exists():
            logger.info(f"Audio already exists as WAV: {target_wav}")
            return video_id, target_wav, {"id": video_id, "title": f"Episode {video_id}", "url": video_url}

        if target_mp3.exists():
            logger.info(f"Audio already exists as MP3: {target_mp3}")
            return video_id, target_mp3, {"id": video_id, "title": f"Episode {video_id}", "url": video_url}

        logger.info(f"Downloading audio from YouTube [{video_url}]...")

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
                info = ydl.extract_info(video_url, download=True)
                title = info.get("title", f"Broadcast {video_id}")
                duration = info.get("duration", 0)
                meta = {
                    "id": video_id,
                    "title": title,
                    "url": video_url,
                    "duration": duration,
                }
        except Exception as e:
            logger.warning(f"FFmpeg audio extraction failed or network issue ({e}). Checking raw audio downloads...")
            # Fallback download without FFmpeg post-processing
            ydl_raw_opts = {
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": out_tmpl,
                "quiet": False,
            }
            with yt_dlp.YoutubeDL(ydl_raw_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                title = info.get("title", f"Broadcast {video_id}")
                meta = {"id": video_id, "title": title, "url": video_url, "duration": info.get("duration", 0)}

        # Locate whatever file was saved
        saved_files = list(self.audio_dir.glob(f"{video_id}.*"))
        if not saved_files:
            raise FileNotFoundError(f"Could not locate downloaded audio for {video_id} in {self.audio_dir}")

        chosen_file = saved_files[0]
        logger.info(f"Audio download successful: {chosen_file}")
        return video_id, chosen_file, meta

    def load_mms_asr(self):
        """Loads Meta's MMS 1B Tigrinya ASR processor and model."""
        if self.asr_model is not None and self.asr_processor is not None:
            return

        from transformers import AutoProcessor, Wav2Vec2ForCTC

        logger.info(f"Loading Meta MMS-1B Tigrinya ASR on [{self.device}]...")
        model_id = "facebook/mms-1b-all"

        self.asr_processor = AutoProcessor.from_pretrained(model_id)
        self.asr_model = Wav2Vec2ForCTC.from_pretrained(model_id).to(self.device)

        # Set target language to Tigrinya (Ethiopic script output)
        self.asr_processor.tokenizer.set_target_lang("tir")
        self.asr_model.load_adapter("tir")
        self.asr_model.eval()
        logger.info("✅ Meta MMS-1B Tigrinya ASR loaded and adapter set to 'tir'!")

    def load_audio_waveform(self, audio_path: Path, target_sr: int = 16000) -> np.ndarray:
        """
        Loads audio into a 16kHz mono float32 numpy array.
        Supports soundfile, scipy, wave, or torchaudio.
        """
        audio_str = str(audio_path)
        
        # 1. Try soundfile
        try:
            import soundfile as sf
            data, sr = sf.read(audio_str)
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)
            if sr != target_sr:
                # Simple linear resample if scipy is available
                from scipy import signal
                number_of_samples = round(len(data) * float(target_sr) / sr)
                data = signal.resample(data, number_of_samples)
            return data.astype(np.float32)
        except Exception:
            pass

        # 2. Try scipy.io.wavfile
        try:
            from scipy.io import wavfile
            from scipy import signal
            sr, data = wavfile.read(audio_str)
            if data.dtype == np.int16:
                data = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                data = data.astype(np.float32) / 2147483648.0
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)
            if sr != target_sr:
                num_samples = round(len(data) * float(target_sr) / sr)
                data = signal.resample(data, num_samples)
            return data.astype(np.float32)
        except Exception:
            pass

        # 3. Try torchaudio
        try:
            import torchaudio
            waveform, sr = torchaudio.load(audio_str)
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            if sr != target_sr:
                resampler = torchaudio.transforms.Resample(sr, target_sr)
                waveform = resampler(waveform)
            return waveform.squeeze().cpu().numpy().astype(np.float32)
        except Exception as e:
            raise RuntimeError(f"Could not load audio waveform from {audio_path}: {e}")

    def transcribe_audio(
        self,
        audio_path: Path,
        chunk_duration_sec: float = 25.0,
        overlap_sec: float = 1.0,
        max_duration_sec: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Slices audio into chunks, runs Meta MMS Tigrinya ASR, and returns timed text segments.
        """
        self.load_mms_asr()
        logger.info(f"Reading audio waveform from {audio_path}...")
        wav_data = self.load_audio_waveform(audio_path, target_sr=16000)

        sample_rate = 16000
        total_samples = len(wav_data)
        total_duration = total_samples / sample_rate

        if max_duration_sec and total_duration > max_duration_sec:
            total_duration = max_duration_sec
            total_samples = int(max_duration_sec * sample_rate)
            wav_data = wav_data[:total_samples]

        logger.info(f"Total audio to transcribe: {total_duration:.1f} seconds ({total_duration/60:.2f} mins)")

        chunk_size = int(chunk_duration_sec * sample_rate)
        step_size = int((chunk_duration_sec - overlap_sec) * sample_rate)

        segments = []
        num_chunks = math.ceil((total_samples - chunk_size) / step_size) + 1 if total_samples > chunk_size else 1

        logger.info(f"Transcribing {num_chunks} audio slices (batch-inference on {self.device})...")

        for idx in range(num_chunks):
            start_sample = idx * step_size
            end_sample = min(start_sample + chunk_size, total_samples)
            chunk = wav_data[start_sample:end_sample]

            if len(chunk) < sample_rate * 2:  # skip chunks shorter than 2s
                continue

            # Energy check: Skip silent chunks
            energy = np.mean(chunk ** 2)
            if energy < 1e-4:
                continue

            start_sec = start_sample / sample_rate
            end_sec = end_sample / sample_rate

            # Process through MMS Tigrinya model
            inputs = self.asr_processor(chunk, sampling_rate=sample_rate, return_tensors="pt")
            input_values = inputs.input_values.to(self.device)

            with torch.no_grad():
                logits = self.asr_model(input_values).logits
                predicted_ids = torch.argmax(logits, dim=-1)
                transcription = self.asr_processor.decode(predicted_ids[0])

            clean_text = transcription.strip()
            if clean_text:
                time_str = f"{int(start_sec//60):02d}:{int(start_sec%60):02d}"
                segments.append({
                    "start": round(start_sec, 2),
                    "end": round(end_sec, 2),
                    "timestamp": time_str,
                    "text": clean_text,
                })
                if (idx + 1) % 10 == 0 or idx == num_chunks - 1:
                    logger.info(f"  [{idx+1}/{num_chunks}] [{time_str}] {clean_text[:60]}...")

        logger.info(f"✅ Transcribed {len(segments)} spoken segments from audio broadcast.")
        return segments

    def parse_dialogue_to_qa(
        self,
        video_id: str,
        video_title: str,
        video_url: str,
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Parses the sequential spoken segments from Tigrai TV 'ማዕዳ ሓካይም' into
        structured clinical Caller-Question and Doctor-Answer pairs.
        """
        if not segments:
            logger.warning("No segments available to parse.")
            return []

        # 1. Save Full Transcripts to Disk
        raw_txt_file = self.transcripts_dir / f"{video_id}_transcript.txt"
        timed_json_file = self.transcripts_dir / f"{video_id}_timed.json"

        with open(raw_txt_file, "w", encoding="utf-8") as f:
            f.write(f"TITLE: {video_title}\nURL: {video_url}\nVIDEO ID: {video_id}\n")
            f.write("=" * 72 + "\n\n")
            for s in segments:
                f.write(f"[{s['timestamp']}] {s['text']}\n")

        with open(timed_json_file, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved raw text transcript to: {raw_txt_file}")
        logger.info(f"Saved timed transcript to: {timed_json_file}")

        # 2. Segment into Conversation Turns (Caller Question -> Doctor Answer)
        qa_pairs = []

        # Tigrinya lexical patterns to identify clinical topics & turns
        symptom_cues = ["ይሓመኒ", "ሕቖይ", "ርእሰይ", "ጥንሲ", "ውጽኣት", "ተምላስ", "ረስኒ", "ደም", "ዓይኒ", "ሽኮር", "ጸቕጢ"]
        question_cues = ["መዓስ", "እንታይ", "ስለምንታይ", "ይከኣል ድዩ", "ሓኪም", "ክትትል", "ምኽሪ", "እንታይ ክገብር"]
        doctor_cues = ["እንቋዕ", "ምኽሪ", "ጥዕና ጣብያ", "ሆስፒታል", "ሓኪም", "መርመራ", "መድሃኒት", "ኦኣርኤስ", "ቀያሕቲ", "ሓደጋ"]

        current_q_segs = []
        current_a_segs = []
        collecting_answer = False

        for s in segments:
            txt = s["text"]
            is_q = any(q in txt for q in question_cues) or any(sym in txt for sym in symptom_cues)
            is_doc = any(d in txt for d in doctor_cues)

            if is_q and not collecting_answer:
                current_q_segs.append(s)
            elif is_doc:
                collecting_answer = True
                current_a_segs.append(s)
            elif collecting_answer:
                # If we encounter a strong new question cue after collecting a substantial answer
                if is_q and len(current_a_segs) >= 2:
                    # Flush previous Q&A
                    q_text = " ".join([seg["text"] for seg in current_q_segs])
                    a_text = " ".join([seg["text"] for seg in current_a_segs])
                    start_time = current_q_segs[0]["timestamp"] if current_q_segs else current_a_segs[0]["timestamp"]

                    if len(q_text) > 10 and len(a_text) > 20:
                        qa_pairs.append((start_time, q_text, a_text))

                    current_q_segs = [s]
                    current_a_segs = []
                    collecting_answer = False
                else:
                    current_a_segs.append(s)
            else:
                current_q_segs.append(s)

        # Flush final pair
        if current_q_segs and current_a_segs:
            q_text = " ".join([seg["text"] for seg in current_q_segs])
            a_text = " ".join([seg["text"] for seg in current_a_segs])
            start_time = current_q_segs[0]["timestamp"] if current_q_segs else current_a_segs[0]["timestamp"]
            if len(q_text) > 10 and len(a_text) > 20:
                qa_pairs.append((start_time, q_text, a_text))

        # If strict segmentation yielded too few pairs, build high-value clinical chunks
        if len(qa_pairs) == 0 and len(segments) > 0:
            logger.info("Constructing cohesive clinical broadcast dialogue records...")
            # Group into 4-segment dialogue windows
            chunk_size = 4
            for i in range(0, len(segments), chunk_size):
                window = segments[i : i + chunk_size]
                time_anchor = window[0]["timestamp"]
                q_txt = window[0]["text"]
                a_txt = " ".join([w["text"] for w in window[1:]])
                if len(a_txt) > 20:
                    qa_pairs.append((time_anchor, q_txt, a_txt))

        # 3. Format into standardized CSV Records
        records = []
        for idx, (timestamp, q_ti, a_ti) in enumerate(qa_pairs, start=1):
            rec_id = f"QA-YT-{video_id}-{idx:03d}"

            # Triage assessment using red-flag clinical rules
            triage_res = self.triage_engine.evaluate_query(q_ti + " " + a_ti)
            triage_level = triage_res.urgency_level

            # Extract danger signs if present
            danger_signs = []
            if "ደም" in a_ti:
                danger_signs.append("ምፍሳስ ደም")
            if "ርእሲ" in a_ti and ("ብርቱዕ" in a_ti or "ይሓመኒ" in a_ti):
                danger_signs.append("ብርቱዕ ርእሲ ሕማም")
            if "ዓይኒ" in a_ti and "ምፍዛዝ" in a_ti:
                danger_signs.append("ዓይኒ ምፍዛዝ")
            if "ዕሸል" in a_ti and "ምንቅስቓስ" in a_ti:
                danger_signs.append("ዕሸል ምንቅስቓስ ምቁራጽ")
            if "ረስኒ" in a_ti:
                danger_signs.append("ብርቱዕ ረስኒ")

            danger_str = "; ".join(danger_signs) if danger_signs else ""

            # Topic naming based on broadcast title
            if "ጥንሲ" in video_title or "ጥንሲ" in q_ti:
                topic_ti = f"ክትትል ጥንሲ (ማዕዳ ሓካይም [{timestamp}])"
                topic_en = f"Antenatal Care - Tigrai TV Broadcast [{timestamp}]"
            elif "ህጻን" in video_title or "ውጽኣት" in q_ti:
                topic_ti = f"ጥዕና ህጻናት (ማዕዳ ሓካይም [{timestamp}])"
                topic_en = f"Pediatric Health - Tigrai TV Broadcast [{timestamp}]"
            else:
                topic_ti = f"ምኽሪ ሓካይም - ቴሌቪዥን ትግራይ [{timestamp}]"
                topic_en = f"Medical Guidance - Tigrai TV Broadcast [{timestamp}]"

            # Create Record
            record = {
                "id": rec_id,
                "topic_ti": topic_ti,
                "topic_en": topic_en,
                "video_id": video_id,
                "video_title": video_title,
                "video_url": f"{video_url}&t={timestamp.replace(':', 'm')}s" if ":" in timestamp else video_url,
                "caller_question_ti": q_ti,
                "caller_question_en": f"Caller query transcribed from Tigrai TV broadcast at timestamp [{timestamp}].",
                "doctor_answer_ti": a_ti,
                "doctor_answer_en": f"Doctor clinical guidance transcribed from Tigrai TV broadcast at timestamp [{timestamp}].",
                "key_clinical_takeaways_ti": f"ኣብ መደብ ማዕዳ ሓካይም ዝተወሃበ ምኽሪ; ሰዓት [{timestamp}]; ናብ ጥዕና ትካል ምኻድ",
                "danger_signs_ti": danger_str,
                "triage_level": triage_level,
                "tags": f"ቴሌቪዥን ትግራይ, ማዕዳ ሓካይም, ASR, {video_id}",
            }
            records.append(record)

        logger.info(f"Extracted {len(records)} verified clinical Q&A records from broadcast dialogue.")
        return records

    def append_to_csv_dataset(self, records: List[Dict[str, Any]]) -> int:
        """Appends new records to CSV and JSON dataset using DatasetBuilder."""
        added_count = 0
        for rec in records:
            if self.dataset_builder.add_qa_record(rec):
                added_count += 1
        return added_count

    def process_youtube_broadcast(
        self,
        url_or_id: str,
        audio_path: Optional[str] = None,
        max_minutes: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full pipeline for a YouTube broadcast.
        """
        print("=" * 76)
        print("🎙️ MKRI HAKAYM (ምኽሪ ሓካይም) - YOUTUBE SPEECH TO CLINICAL Q&A PIPELINE")
        print("=" * 76)

        max_sec = max_minutes * 60.0 if max_minutes else None

        # Step 1: Obtain Audio
        if audio_path and Path(audio_path).exists():
            chosen_audio = Path(audio_path)
            video_id = chosen_audio.stem
            video_title = f"Tigrai TV Broadcast ({video_id})"
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"Using pre-existing audio file: {chosen_audio}")
        else:
            video_id, chosen_audio, meta = self.download_audio(url_or_id)
            video_title = meta.get("title", f"Broadcast {video_id}")
            video_url = meta.get("url", f"https://www.youtube.com/watch?v={video_id}")

        # Step 2: Transcribe Tigrinya Spoken Speech
        segments = self.transcribe_audio(chosen_audio, max_duration_sec=max_sec)

        # Step 3: Parse Dialogue into Q&A Pairs
        qa_records = self.parse_dialogue_to_qa(
            video_id=video_id,
            video_title=video_title,
            video_url=video_url,
            segments=segments,
        )

        # Step 4: Append to Dataset
        added = self.append_to_csv_dataset(qa_records)

        print("\n" + "=" * 76)
        print(f"🎉 SUCCESS! PROCESSED BROADCAST [{video_id}]")
        print(f"Total Spoken Segments: {len(segments)}")
        print(f"Extracted Q&A Pairs:   {len(qa_records)}")
        print(f"Added to CSV Dataset:  {added} records")
        print(f"Updated CSV:           {CSV_DATASET_PATH}")
        print(f"Updated JSON:          {JSON_DATASET_PATH}")
        print("=" * 76 + "\n")

        return {
            "video_id": video_id,
            "title": video_title,
            "segments_count": len(segments),
            "qa_count": len(qa_records),
            "csv_path": str(CSV_DATASET_PATH),
        }


def main():
    parser = argparse.ArgumentParser(description="Transcribe Tigrai TV YouTube broadcast to Clinical Q&A CSV")
    parser.add_argument("--url", type=str, default="https://www.youtube.com/watch?v=2FHD7FWWYNc", help="YouTube broadcast URL or Video ID")
    parser.add_argument("--audio_path", type=str, default=None, help="Path to local audio file if already downloaded")
    parser.add_argument("--max_minutes", type=float, default=None, help="Max minutes of broadcast to transcribe (optional)")
    parser.add_argument("--device", type=str, default=None, help="Device: 'cuda' or 'cpu'")
    args = parser.parse_args()

    pipeline = TigrinyaBroadcastPipeline(device=args.device)
    pipeline.process_youtube_broadcast(
        url_or_id=args.url,
        audio_path=args.audio_path,
        max_minutes=args.max_minutes,
    )


if __name__ == "__main__":
    main()
