from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class WhisperTranscriber:
    """Wrapper around lightning-whisper-mlx for Apple Silicon transcription."""

    def __init__(self, model: str = "distil-large-v3", batch_size: int = 12):
        self._model_name = model
        self._batch_size = batch_size
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            log.info("Loading Whisper model %s ...", self._model_name)
            from lightning_whisper_mlx import LightningWhisperMLX
            self._model = LightningWhisperMLX(
                model=self._model_name, batch_size=self._batch_size
            )
            log.info("Whisper model loaded.")

    def transcribe(self, audio_path: str) -> dict:
        """Transcribe audio file. Returns {"text": str}."""
        self._ensure_loaded()
        result = self._model.transcribe(audio_path)
        return result
