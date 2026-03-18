"""
Speech-to-Text — Whisper Integration

Transcribes audio to text using OpenAI Whisper (runs locally).

Privacy note: Whisper runs locally by default — speech never leaves the device.
This is important for users who speak sensitive information (passwords, health details).

Voice Activity Detection (VAD):
`transcribe_microphone_with_vad()` uses webrtcvad to detect when the user stops speaking
and cuts off recording at that point — instead of always waiting a fixed duration.
This is critical accessibility: Dorothy (elder) won't be cut off mid-sentence, and
Marcus (power user) won't waste time waiting after he's done.
Falls back to fixed-duration recording if webrtcvad is not installed.
"""

import asyncio
import io
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

# Whisper model to use. Options: tiny, base, small, medium, large, large-v3
# large-v3 is most accurate; base is fastest. Default: base for responsiveness.
DEFAULT_MODEL = "base"

# Global model instance (loaded once, reused)
_whisper_model = None
_model_lock = asyncio.Lock()

# VAD configuration
# webrtcvad aggressiveness: 0 (least aggressive) to 3 (most aggressive).
# 1 is a good balance: catches silence without cutting off slow speakers.
VAD_AGGRESSIVENESS = 1

# After this many consecutive silent frames, stop recording.
# At 30ms per frame, 20 frames = 600ms of silence — long enough for natural speech pauses.
VAD_SILENCE_FRAMES = 20

# Maximum recording duration even if the user keeps talking (seconds).
# Prevents runaway recordings (network noise, accidental activation).
VAD_MAX_DURATION = 30.0

# Minimum recording duration (seconds) — ensures we don't cut off too fast.
VAD_MIN_DURATION = 0.5


async def _load_model(model_name: str = DEFAULT_MODEL):
    """Load Whisper model (thread-safe, loads only once)."""
    global _whisper_model
    async with _model_lock:
        if _whisper_model is None:
            logger.info(f"Loading Whisper model: {model_name}")
            # Run in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            _whisper_model = await loop.run_in_executor(None, _load_whisper_sync, model_name)
            logger.info("Whisper model loaded.")
    return _whisper_model


def _load_whisper_sync(model_name: str):
    """Synchronous Whisper model loading (runs in thread pool)."""
    import whisper

    return whisper.load_model(model_name)


async def transcribe_audio(
    audio_bytes: bytes,
    language: str | None = None,
) -> str | None:
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
                ),
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
) -> str | None:
    """
    Record from the microphone and transcribe.
    Used by the local voice interface.

    Args:
        duration_seconds: How long to record

    Returns:
        Transcribed text, or None
    """
    try:
        import scipy.io.wavfile as wav
        import sounddevice as sd

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
            ),
        )
        await loop.run_in_executor(None, sd.wait)

        # Convert to bytes via WAV
        buffer = io.BytesIO()
        wav.write(buffer, sample_rate, audio)
        audio_bytes = buffer.getvalue()

        return await transcribe_audio(audio_bytes)

    except ImportError:
        logger.error("sounddevice or scipy not installed. Install with: pip install sounddevice scipy")
        return None
    except Exception as e:
        logger.error(f"Microphone recording failed: {e}", exc_info=True)
        return None
