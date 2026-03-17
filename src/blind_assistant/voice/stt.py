"""
Speech-to-Text — Whisper Integration

Transcribes audio to text using OpenAI Whisper (runs locally).

Privacy note: Whisper runs locally by default — speech never leaves the device.
This is important for users who speak sensitive information (passwords, health details).
"""

import asyncio
import logging
import io
import tempfile
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Whisper model to use. Options: tiny, base, small, medium, large, large-v3
# large-v3 is most accurate; base is fastest. Default: base for responsiveness.
DEFAULT_MODEL = "base"

# Global model instance (loaded once, reused)
_whisper_model = None
_model_lock = asyncio.Lock()


async def _load_model(model_name: str = DEFAULT_MODEL):
    """Load Whisper model (thread-safe, loads only once)."""
    global _whisper_model
    async with _model_lock:
        if _whisper_model is None:
            logger.info(f"Loading Whisper model: {model_name}")
            # Run in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            _whisper_model = await loop.run_in_executor(
                None, _load_whisper_sync, model_name
            )
            logger.info("Whisper model loaded.")
    return _whisper_model


def _load_whisper_sync(model_name: str):
    """Synchronous Whisper model loading (runs in thread pool)."""
    import whisper
    return whisper.load_model(model_name)


async def transcribe_audio(
    audio_bytes: bytes,
    language: Optional[str] = None,
) -> Optional[str]:
    """
    Transcribe audio bytes to text using local Whisper.

    Args:
        audio_bytes: Raw audio data (wav, mp3, ogg, or any format ffmpeg supports)
        language: Optional language hint (e.g., "en"). Auto-detected if None.

    Returns:
        Transcribed text, or None if transcription failed.

    Privacy: All processing is local. Audio never sent to external services.
    """
    model = await _load_model()

    try:
        # Write to temp file (Whisper requires file path, not bytes)
        # Use a temp file with restricted permissions
        with tempfile.NamedTemporaryFile(
            suffix=".ogg",
            delete=False,
            mode="wb",
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # Run transcription in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: model.transcribe(
                    tmp_path,
                    language=language,
                    fp16=False,  # CPU-safe
                )
            )
            transcript = result.get("text", "").strip()
            logger.debug(f"Transcribed: {transcript[:60]}...")
            return transcript if transcript else None
        finally:
            # Always delete the temp file
            os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        return None


async def transcribe_microphone(
    duration_seconds: float = 5.0,
) -> Optional[str]:
    """
    Record from the microphone and transcribe.
    Used by the local voice interface.

    Args:
        duration_seconds: How long to record

    Returns:
        Transcribed text, or None
    """
    try:
        import sounddevice as sd
        import numpy as np
        import scipy.io.wavfile as wav

        sample_rate = 16000
        logger.debug(f"Recording for {duration_seconds}s...")

        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,
            lambda: sd.rec(
                int(duration_seconds * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
            )
        )
        await loop.run_in_executor(None, sd.wait)

        # Convert to bytes via WAV
        buffer = io.BytesIO()
        wav.write(buffer, sample_rate, audio)
        audio_bytes = buffer.getvalue()

        return await transcribe_audio(audio_bytes)

    except ImportError:
        logger.error(
            "sounddevice or scipy not installed. "
            "Install with: pip install sounddevice scipy"
        )
        return None
    except Exception as e:
        logger.error(f"Microphone recording failed: {e}", exc_info=True)
        return None
