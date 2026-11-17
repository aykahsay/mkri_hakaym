"""
YouTube crawler for Tigrai TV "ማዕዳ ሓካይም" medical education episodes.
Fetches video metadata and downloads clean audio for transcription and dataset creation.
"""
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

import yt_dlp

from config import (
    METADATA_DIR,
    AUDIO_DIR,
    YOUTUBE_SEED_URLS,
    SEARCH_QUERIES,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Crawler")


class MedicalVideoCollector:
    def __init__(self, metadata_dir: Path = METADATA_DIR, audio_dir: Path = AUDIO_DIR):
        self.metadata_dir = metadata_dir
        self.audio_dir = audio_dir
        self.catalog_index_path = self.metadata_dir / "catalog_index.json"
        self.catalog: Dict[str, Dict[str, Any]] = self._load_catalog()

    def _load_catalog(self) -> Dict[str, Dict[str, Any]]:
        if self.catalog_index_path.exists():
            try:
                with open(self.catalog_index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load catalog index: {e}. Starting fresh.")
        return {}

    def _save_catalog(self):
        with open(self.catalog_index_path, "w", encoding="utf-8") as f:
            json.dump(self.catalog, f, ensure_ascii=False, indent=2)

    def extract_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract metadata without downloading media."""
        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None

                video_id = info.get("id")
                metadata = {
                    "id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "title": info.get("title", ""),
                    "description": info.get("description", ""),
                    "duration": info.get("duration", 0),
                    "upload_date": info.get("upload_date", ""),
                    "channel": info.get("channel", info.get("uploader", "")),
                    "channel_id": info.get("channel_id", ""),
                    "view_count": info.get("view_count", 0),
                    "categories": info.get("categories", []),
                    "tags": info.get("tags", []),
                }

                # Save individual JSON
                meta_file = self.metadata_dir / f"{video_id}.json"
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)

                self.catalog[video_id] = {
                    "id": video_id,
                    "title": metadata["title"],
                    "duration": metadata["duration"],
                    "url": metadata["url"],
                    "has_audio": (self.audio_dir / f"{video_id}.mp3").exists(),
                }
                self._save_catalog()

                logger.info(f"Metadata extracted: [{video_id}] {metadata['title']}")
                return metadata
            except Exception as e:
                logger.error(f"Failed extracting metadata for {url}: {e}")
                return None

    def search_episodes(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search YouTube for Tigrai TV medical episodes."""
        search_target = f"ytsearch{max_results}:{query}"
        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
        }
        found_videos = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                logger.info(f"Searching for: '{query}' (limit: {max_results})")
                res = ydl.extract_info(search_target, download=False)
                if res and "entries" in res:
                    for entry in res["entries"]:
                        if entry and "id" in entry:
                            v_url = f"https://www.youtube.com/watch?v={entry['id']}"
                            meta = self.extract_metadata(v_url)
                            if meta:
                                found_videos.append(meta)
            except Exception as e:
                logger.error(f"Search failed for '{query}': {e}")
        return found_videos

    def download_audio(self, video_id: str) -> Optional[Path]:
        """Download high-quality speech audio from video."""
        target_path = self.audio_dir / f"{video_id}.mp3"
        if target_path.exists():
            logger.info(f"Audio already exists for [{video_id}]: {target_path}")
            return target_path

        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(self.audio_dir / f"{video_id}.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "quiet": False,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Downloading audio for [{video_id}]...")
                ydl.download([url])

            if target_path.exists():
                if video_id in self.catalog:
                    self.catalog[video_id]["has_audio"] = True
                    self._save_catalog()
                logger.info(f"Successfully downloaded audio: {target_path}")
                return target_path
            else:
                # If ffmpeg is not available, find whatever audio file was downloaded
                for f in self.audio_dir.glob(f"{video_id}.*"):
                    if f.suffix in [".m4a", ".webm", ".opus", ".mp3"]:
                        logger.info(f"Audio saved as: {f}")
                        return f
        except Exception as e:
            logger.error(f"Audio download failed for {video_id}: {e}")
        return None


def main():
    collector = MedicalVideoCollector()

    print("=== Mkri Hakaym (ምኽሪ ሓካይም) Episode Collector ===")
    
    # 1. Process Seed URLs (including https://www.youtube.com/watch?v=2FHD7FWWYNc)
    print("\n1. Collecting Seed Videos...")
    for seed_url in YOUTUBE_SEED_URLS:
        collector.extract_metadata(seed_url)

    # 2. Search for related Tigrai TV "ማዕዳ ሓካይም" broadcasts
    print("\n2. Searching for medical broadcasts across topics...")
    for q in SEARCH_QUERIES[:2]:
        collector.search_episodes(q, max_results=5)

    print(f"\nTotal cataloged episodes: {len(collector.catalog)}")
    for vid, item in collector.catalog.items():
        print(f" - [{vid}] {item['title']} ({item.get('duration', 0)}s)")


if __name__ == "__main__":
    main()
