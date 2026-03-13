from __future__ import annotations

import asyncio
import os
from pathlib import Path


async def convert_to_wav(input_path: str, output_dir: str) -> str:
    """Convert any audio file to 16kHz mono WAV (required for pyannote + whisper)."""
    output_path = os.path.join(
        output_dir, Path(input_path).stem + ".wav"
    )
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "16000", "-ac", "1", "-f", "wav", output_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed for {input_path}")
    return output_path


async def get_duration(audio_path: str) -> float:
    """Return audio duration in seconds using ffprobe."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()
    try:
        return float(stdout.decode().strip())
    except ValueError:
        return 0.0


def cleanup_audio(*paths: str) -> None:
    """Delete temporary audio files."""
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass
