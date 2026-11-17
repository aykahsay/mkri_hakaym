"""
Audio Synthesis and Telephony Audio Server for Mkri Hakaym (ምኽሪ ሓካይም).
Manages spoken Tigrinya audio files for phone playback via Meta MMS-TTS (tir)
or pre-recorded studio clips.
"""
import logging
from pathlib import Path
from typing import Optional
import numpy as np

from config import DATA_DIR

logger = logging.getLogger("AudioService")

AUDIO_CACHE_DIR = DATA_DIR / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class TigrinyaAudioService:
    def __init__(self, cache_dir: Path = AUDIO_CACHE_DIR):
        self.cache_dir = cache_dir
        self.model = None
        self.tokenizer = None
        self._tts_loaded = False

    def load_tts_model(self):
        """Lazy load Meta MMS-TTS for Tigrinya (facebook/mms-tts-tir)."""
        if self._tts_loaded:
            return

        try:
            from transformers import VitsModel, AutoTokenizer
            logger.info("Loading Meta MMS-TTS model for Tigrinya (facebook/mms-tts-tir)...")
            self.model = VitsModel.from_pretrained("facebook/mms-tts-tir")
            self.tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-tir")
            self._tts_loaded = True
            logger.info("Meta MMS-TTS Tigrinya voice model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load neural TTS weights: {e}. Will use audio cache / tone fallback.")

    def synthesize_to_wav(self, text: str, output_filename: str) -> Path:
        """
        Synthesizes Tigrinya text to a standard 16kHz WAV file.
        If neural model is not active, creates a clean audio tone placeholder.
        """
        target_wav = self.cache_dir / output_filename
        if target_wav.exists():
            return target_wav

        if self._tts_loaded and self.model and self.tokenizer:
            import torch
            import scipy.io.wavfile

            inputs = self.tokenizer(text, return_tensors="pt")
            with torch.no_grad():
                output = self.model(**inputs).waveform
            
            rate = self.model.config.sampling_rate
            data = output.squeeze().cpu().numpy()
            scipy.io.wavfile.write(str(target_wav), rate=rate, data=data)
            logger.info(f"Synthesized Tigrinya voice audio to {target_wav}")
            return target_wav

        # Fallback: create a standard telephony-compatible WAV tone (8000Hz PCM)
        import scipy.io.wavfile
        sample_rate = 8000
        duration = 2.0  # seconds
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        # Gentle dial tone tone (440Hz)
        tone = np.sin(440 * t * 2 * np.pi) * 0.3
        scipy.io.wavfile.write(str(target_wav), sample_rate, tone.astype(np.float32))
        logger.info(f"Generated audio placeholder: {target_wav}")
        return target_wav

    def get_audio_path(self, filename: str) -> Optional[Path]:
        p = self.cache_dir / filename
        return p if p.exists() else None


if __name__ == "__main__":
    svc = TigrinyaAudioService()
    p = svc.synthesize_to_wav("እንቋዕ ናብ ምኽሪ ሓካይም ብደሓን መጻእኹም።", "welcome.wav")
    print(f"Generated test audio at: {p}")
