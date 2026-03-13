from __future__ import annotations

import asyncio
import functools
import logging
import os

from openai import OpenAI

log = logging.getLogger(__name__)


class TranscriptionPipeline:
    """Transcription using OpenAI Whisper API — no ffmpeg or local model needed."""

    def __init__(self, api_key: str, model: str = "whisper-1", prompt: str = ""):
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._prompt = prompt

    async def process(self, audio_path: str) -> tuple[str, float]:
        """
        Transcribe audio via OpenAI Whisper API.
        Returns (transcript_text, duration_seconds).
        Runs in a thread to avoid blocking the event loop.
        """
        loop = asyncio.get_event_loop()
        transcript, duration = await loop.run_in_executor(
            None, functools.partial(self._transcribe, audio_path)
        )
        return transcript, duration

    def _transcribe(self, audio_path: str) -> tuple[str, float]:
        """Synchronous transcription call to OpenAI."""
        file_size = os.path.getsize(audio_path)
        log.info("Transcribing audio: %s (%.1f KB)", audio_path, file_size / 1024)

        with open(audio_path, "rb") as f:
            kwargs = dict(
                model=self._model,
                file=f,
                response_format="verbose_json",
            )
            if self._prompt:
                kwargs["prompt"] = self._prompt
            response = self._client.audio.transcriptions.create(**kwargs)

        transcript = response.text.strip() if response.text else ""
        duration = getattr(response, "duration", 0.0) or 0.0

        log.info("Transcription complete: %d chars, %.1fs", len(transcript), duration)
        return transcript, duration
