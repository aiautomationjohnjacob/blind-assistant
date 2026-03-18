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


def _record_with_vad_sync(
    sample_rate: int = 16000,
    aggressiveness: int = VAD_AGGRESSIVENESS,
    silence_frames: int = VAD_SILENCE_FRAMES,
    max_duration: float = VAD_MAX_DURATION,
    min_duration: float = VAD_MIN_DURATION,
) -> bytes | None:
    """
    Record audio from the microphone until a sustained silence is detected.

    Uses webrtcvad to detect voice activity frame-by-frame (30ms chunks).
    Stops recording after `silence_frames` consecutive silent frames.
    Always records at least `min_duration` seconds to avoid premature cutoff.
    Returns WAV bytes, or None if recording fails.

    Called in a thread pool to avoid blocking the async event loop.
    """
    try:
        import webrtcvad
    except ImportError as e:
        # webrtcvad not installed — caller should fall back to fixed-duration
        raise ImportError("webrtcvad not installed") from e

    try:
        import numpy as np
        import scipy.io.wavfile as wav
        import sounddevice as sd
    except ImportError as e:
        raise ImportError(f"Audio dependencies missing: {e}") from e

    # webrtcvad requires 16kHz mono, 16-bit PCM in 10/20/30ms frames
    frame_duration_ms = 30  # 30ms frame is the highest resolution webrtcvad supports
    frame_samples = int(sample_rate * frame_duration_ms / 1000)  # 480 samples at 16kHz

    vad = webrtcvad.Vad(aggressiveness)

    max_frames = int(max_duration * 1000 / frame_duration_ms)
    min_frames = int(min_duration * 1000 / frame_duration_ms)

    # Open an input stream and read frame-by-frame until silence
    recorded_frames: list[bytes] = []
    consecutive_silent = 0
    speech_started = False

    try:
        with sd.RawInputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocksize=frame_samples,
        ) as stream:
            for frame_idx in range(max_frames):
                frame_bytes, _ = stream.read(frame_samples)
                pcm = bytes(frame_bytes)
                recorded_frames.append(pcm)

                # Check if this frame contains speech
                try:
                    is_speech = vad.is_speech(pcm, sample_rate)
                except Exception:
                    # VAD can throw on malformed frames — treat as silence
                    is_speech = False

                if is_speech:
                    speech_started = True
                    consecutive_silent = 0
                else:
                    consecutive_silent += 1

                # Stop if: we've heard speech AND we've reached silence threshold
                # AND we've recorded at least the minimum duration
                if speech_started and consecutive_silent >= silence_frames and frame_idx >= min_frames:
                    logger.debug(
                        f"VAD: stopped after {frame_idx + 1} frames "
                        f"({(frame_idx + 1) * frame_duration_ms}ms), "
                        f"{consecutive_silent} silent frames"
                    )
                    break

    except Exception as e:
        logger.error(f"VAD recording failed: {e}", exc_info=True)
        return None

    if not recorded_frames:
        return None

    # Concatenate frames and convert to WAV
    pcm_bytes = b"".join(recorded_frames)
    audio_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    buffer = io.BytesIO()
    wav.write(buffer, sample_rate, audio_array)
    return buffer.getvalue()


async def transcribe_microphone_with_vad(
    max_duration: float = VAD_MAX_DURATION,
    min_duration: float = VAD_MIN_DURATION,
    fallback_duration: float = 8.0,
) -> str | None:
    """
    Record from the microphone using Voice Activity Detection (VAD) and transcribe.

    VAD automatically stops recording when the user stops speaking — no fixed cutoff.
    This is the preferred function for the voice interface (ISSUE-002).

    Args:
        max_duration: Maximum recording length in seconds (prevents runaway recording).
        min_duration: Minimum recording length — prevents cutting off fast speakers.
        fallback_duration: Duration to use if webrtcvad is not installed.

    Returns:
        Transcribed text, or None if recording/transcription fails.

    Accessibility note: VAD stops at natural speech pauses, so elder users who speak
    slowly are not cut off (ISSUE-002). Falls back gracefully if webrtcvad is missing.
    """
    loop = asyncio.get_event_loop()

    try:
        # Attempt VAD recording in a thread pool (blocking I/O)
        audio_bytes = await loop.run_in_executor(
            None,
            lambda: _record_with_vad_sync(
                max_duration=max_duration,
                min_duration=min_duration,
            ),
        )
        if audio_bytes is None:
            logger.warning("VAD recording returned no audio — retrying with fixed duration")
            return await transcribe_microphone(duration_seconds=fallback_duration)

        logger.debug(f"VAD recording complete: {len(audio_bytes)} bytes")
        return await transcribe_audio(audio_bytes)

    except ImportError:
        # webrtcvad not installed — fall back to fixed-duration recording
        logger.info(
            "webrtcvad not installed — using fixed-duration recording. "
            "Install with: pip install webrtcvad-wheels for voice activity detection."
        )
        return await transcribe_microphone(duration_seconds=fallback_duration)
    except Exception as e:
        logger.error(f"VAD transcription failed: {e}", exc_info=True)
        return await transcribe_microphone(duration_seconds=fallback_duration)
