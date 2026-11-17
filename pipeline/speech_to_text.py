"""
Tigrinya Speech-to-Text (ASR) Pipeline for Mkri Hakaym.
Supports Meta MMS (tir) and Whisper speech models for transcribing Tigrinya
medical advice broadcasts and live phone call audio streams.
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("ASR")


class TigrinyaSpeechRecognizer:
    def __init__(self, model_type: str = "meta-mms"):
        self.model_type = model_type
        self.model = None
        self.processor = None
        self._initialized = False

    def load_model(self):
        """
        Lazy loads the Meta MMS or Whisper speech model for Tigrinya (tir).
        Meta MMS explicitly supports Tigrinya speech recognition.
        """
        if self._initialized:
            return

        try:
            if self.model_type == "meta-mms":
                from transformers import Wav2Vec2ForCTC, AutoProcessor
                import torch

                model_id = "facebook/mms-1b-all"
                logger.info(f"Loading Tigrinya ASR model: {model_id} (target_lang='tir')...")
                self.processor = AutoProcessor.from_pretrained(model_id, target_lang="tir")
                self.model = Wav2Vec2ForCTC.from_pretrained(model_id, target_lang="tir")
                self._initialized = True
                logger.info("Meta MMS Tigrinya ASR loaded successfully.")
            else:
                logger.info(f"Using model type {self.model_type}")
        except Exception as e:
            logger.warning(
                f"Could not initialize neural ASR in offline mode: {e}. "
                "Will use mock/audio-stream fallback for development."
            )

    def transcribe_audio_file(self, audio_path: Path) -> Dict[str, Any]:
        """
        Transcribes a recorded audio file into Tigrinya text.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing {audio_path.name}...")

        # If offline neural model is loaded
        if self._initialized and self.model and self.processor:
            import torchaudio
            import torch

            speech_array, sampling_rate = torchaudio.load(str(audio_path))
            # Resample to 16kHz if needed
            if sampling_rate != 16000:
                resampler = torchaudio.transforms.Resample(sampling_rate, 16000)
                speech_array = resampler(speech_array)

            inputs = self.processor(speech_array.squeeze().numpy(), sampling_rate=16000, return_tensors="pt")
            with torch.no_grad():
                logits = self.model(inputs.input_values).logits
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = self.processor.batch_decode(predicted_ids)[0]
            return {"transcription": transcription, "status": "success"}

        # Development fallback
        return {
            "transcription": "ማዕዳ ሓካይም፡ ዛዕባ ክትትል ጥንሲ። ጥንሲ ኣብ እዋኑ ክትትል ምግባር ኣገዳሲ እዩ።",
            "status": "dev_mock",
            "note": "Install torch/torchaudio weights or cloud STT for production live transcription.",
        }


if __name__ == "__main__":
    asr = TigrinyaSpeechRecognizer()
    print("Tigrinya Speech-to-Text Module Ready.")
