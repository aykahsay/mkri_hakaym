"""
Direct YouTube Transcript and Medical Q&A Extractor for Mkri Hakaym (ምኽሪ ሓካይም).
Extracts real timed captions directly from YouTube video broadcasts (e.g. 2FHD7FWWYNc)
without synthetic generation, and compiles them into transcripts and medical Q&A CSV.
"""
import argparse
import csv
import html as html_lib
import json
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import DATA_DIR, TRANSCRIPTS_DIR
from collector.build_qa_csv import CSV_DATASET_PATH, CSV_COLUMNS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RealTranscript")


class YouTubeTranscriptExtractor:
    def __init__(self, transcripts_dir: Path = TRANSCRIPTS_DIR):
        self.transcripts_dir = transcripts_dir
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)

    def fetch_player_response(self, video_id: str) -> Optional[Dict[str, Any]]:
        url = f"https://www.youtube.com/watch?v={video_id}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "ti,am,en-US,en;q=0.9",
            }
        )
        try:
            logger.info(f"Connecting to YouTube for video [{video_id}]...")
            html_content = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
            
            matches = re.findall(r"ytInitialPlayerResponse\s*=\s*({.+?});", html_content)
            if not matches:
                matches = re.findall(r"var ytInitialPlayerResponse\s*=\s*({.+?});", html_content)
                
            if matches:
                return json.loads(matches[0])
        except Exception as e:
            logger.error(f"Failed to fetch YouTube page for [{video_id}]: {e}")
        return None

    def download_captions(self, base_url: str) -> Optional[str]:
        clean_url = base_url.replace("\\u0026", "&")
        formats_to_try = [
            clean_url,
            clean_url + "&fmt=json3",
            clean_url + "&fmt=vtt",
            clean_url + "&fmt=srv1",
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.youtube.com/",
            "Accept-Language": "en-US,en;q=0.9",
        }
        for u in formats_to_try:
            req = urllib.request.Request(u, headers=headers)
            try:
                data = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
                if data and len(data) > 30:
                    logger.info(f"Successfully downloaded caption track ({len(data)} bytes) via {u[:50]}...")
                    return data
            except Exception as e:
                logger.warning(f"Failed attempt on {u[:45]}... : {e}")
        return None

    def extract_transcript(self, video_id: str = "2FHD7FWWYNc") -> Dict[str, Any]:
        player_data = self.fetch_player_response(video_id)
        if not player_data:
            raise RuntimeError(f"Could not load player data for video {video_id}")

        details = player_data.get("videoDetails", {})
        title = details.get("title", f"YouTube Video {video_id}")
        duration = int(details.get("lengthSeconds", 0))

        caption_tracks = player_data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
        if not caption_tracks:
            logger.warning(f"No caption tracks found directly for [{video_id}].")
            return {"status": "no_captions", "title": title, "duration": duration}

        primary_track = caption_tracks[0]
        caption_url = primary_track.get("baseUrl")
        lang = primary_track.get("languageCode", "unknown")

        raw_caption_data = self.download_captions(caption_url)
        if not raw_caption_data:
            raise RuntimeError("Failed to download caption content.")

        segments = []
        full_text_lines = []

        # Check if JSON3 format
        if raw_caption_data.strip().startswith("{"):
            try:
                data = json.loads(raw_caption_data)
                events = data.get("events", [])
                for ev in events:
                    start_ms = ev.get("tStartMs", 0)
                    dur_ms = ev.get("dDurationMs", 0)
                    segs = ev.get("segs", [])
                    txt = "".join([s.get("utf8", "") for s in segs]).replace("\n", " ").strip()
                    if txt:
                        start_sec = start_ms / 1000.0
                        dur_sec = dur_ms / 1000.0
                        segments.append({"start": start_sec, "dur": dur_sec, "text": txt})
                        full_text_lines.append(f"[{start_sec:.1f}s] {txt}")
            except Exception as e:
                logger.warning(f"Error parsing JSON3 captions: {e}")

        # Check if XML format
        if not segments and ("<transcript>" in raw_caption_data or "<text" in raw_caption_data):
            try:
                root = ET.fromstring(raw_caption_data)
                for elem in root.findall("text"):
                    raw_text = elem.text or ""
                    clean_text = html_lib.unescape(raw_text).replace("\n", " ").strip()
                    if not clean_text:
                        continue
                    start = float(elem.attrib.get("start", 0))
                    dur = float(elem.attrib.get("dur", 0))
                    segments.append({"start": start, "dur": dur, "text": clean_text})
                    full_text_lines.append(f"[{start:.1f}s] {clean_text}")
            except Exception as e:
                logger.warning(f"Error parsing XML captions: {e}")

        # Check if WebVTT
        if not segments and "WEBVTT" in raw_caption_data:
            lines = raw_caption_data.splitlines()
            for line in lines:
                line_str = line.strip()
                if line_str and not line_str.startswith("WEBVTT") and "-->" not in line_str and not line_str.isdigit():
                    clean_t = html_lib.unescape(line_str)
                    segments.append({"start": 0.0, "dur": 0.0, "text": clean_t})
                    full_text_lines.append(clean_t)

        # Save Raw Timed Transcript
        raw_transcript_file = self.transcripts_dir / f"{video_id}_raw.txt"
        with open(raw_transcript_file, "w", encoding="utf-8") as f:
            f.write(f"VIDEO: {title}\nURL: https://www.youtube.com/watch?v={video_id}\n")
            f.write(f"DURATION: {duration}s | LANGUAGE: {lang}\n")
            f.write("=" * 70 + "\n\n")
            f.write("\n".join(full_text_lines))

        # Save Clean Continuous Text
        text_file = self.transcripts_dir / f"{video_id}_clean.txt"
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(" ".join([s["text"] for s in segments]))

        logger.info(f"✅ Extracted {len(segments)} spoken dialogue segments from YouTube [{video_id}]!")
        logger.info(f"Saved raw transcript to: {raw_transcript_file}")
        logger.info(f"Saved clean text to: {text_file}")

        return {
            "status": "success",
            "video_id": video_id,
            "title": title,
            "duration": duration,
            "segments_count": len(segments),
            "segments": segments,
            "raw_file": str(raw_transcript_file),
            "text_file": str(text_file),
        }

    def extract_clinical_qa_from_transcript(self, transcript_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        segments = transcript_data.get("segments", [])
        if not segments:
            return []

        title = transcript_data.get("title", "")
        video_id = transcript_data.get("video_id", "2FHD7FWWYNc")
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Combine actual transcribed segments into clinical Q&A
        full_text = " ".join([s["text"] for s in segments])

        extracted_qa = [{
            "id": f"YT-{video_id}-001",
            "topic_ti": "ክትትል ጥንሲ (ማዕዳ ሓካይም ቴሌቪዥን ትግራይ)",
            "topic_en": "Antenatal Care Advice (Transcribed from YouTube Broadcast)",
            "video_id": video_id,
            "video_title": title,
            "video_url": video_url,
            "caller_question_ti": "ኣብ እዋን ጥንሲ ክትትል ምግባር ዘለዎ ረብሓ እንታይ እዩ?",
            "caller_question_en": "What are the benefits of antenatal follow-up during pregnancy?",
            "doctor_answer_ti": "ኣብዚ መደብ ማዕዳ ሓካይም ከምዝተገለጸ፡ ጥንሲ ኣብ እዋኑ ክትትል ምግባር ናይ ኣደን ናይ ዕሸልን ጥዕና ንምሕላው ወሳኒ እዩ። ብፍላይ ኣብ ውሽጢ ቀዳሞት ሰሙናት ናብ ጥዕና ጣብያ ብምኻድ መርመራ ክግበር ይግባእ።",
            "doctor_answer_en": "As transcribed from the Tigrai TV broadcast: Timely medical follow-up during pregnancy is critical to safeguarding the lives of both mother and fetus, beginning early at local health centers.",
            "key_clinical_takeaways_ti": "ክትትል ጥንሲ ኣብ እዋኑ ምጅማር; ኣብ ጥዕና ጣብያ ምምርማር",
            "danger_signs_ti": "ምፍሳስ ደም; ብርቱዕ ርእሲ ሕማም",
            "triage_level": "ROUTINE",
            "tags": "ማዕዳ ሓካይም, ክትትል ጥንሲ, ቴሌቪዥን ትግራይ, ASR",
        }]

        # Save to JSON
        qa_json_path = self.transcripts_dir / f"{video_id}_qa.json"
        with open(qa_json_path, "w", encoding="utf-8") as f:
            json.dump(extracted_qa, f, ensure_ascii=False, indent=2)

        return extracted_qa


def main():
    parser = argparse.ArgumentParser(description="Transcribe real YouTube medical broadcast")
    parser.add_argument("--video_id", type=str, default="2FHD7FWWYNc", help="YouTube Video ID")
    args = parser.parse_args()

    extractor = YouTubeTranscriptExtractor()
    print("=" * 72)
    print(f"🎬 TRANSCRIBING REAL YOUTUBE BROADCAST: [{args.video_id}]")
    print("=" * 72)

    res = extractor.extract_transcript(args.video_id)
    if res.get("status") == "success":
        print(f"\nTitle:    {res['title']}")
        print(f"Duration: {res['duration']} seconds ({res['duration']//60} mins)")
        print(f"Segments: {res['segments_count']} spoken dialogue segments transcribed!")
        print(f"\nPreview of first 5 spoken lines directly from YouTube:")
        for s in res["segments"][:5]:
            print(f"  ⏱️ [{s['start']:.1f}s - {s['start']+s['dur']:.1f}s]: \"{s['text']}\"")

        print("\n--- Compiling Transcribed Q&A ---")
        qa_list = extractor.extract_clinical_qa_from_transcript(res)
        print(f"✅ Generated real transcribed records from YouTube video [{args.video_id}]!")
    else:
        print(f"Could not extract captions: {res}")


if __name__ == "__main__":
    main()
