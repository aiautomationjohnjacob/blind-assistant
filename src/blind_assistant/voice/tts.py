"""
Text-to-Speech — ElevenLabs (cloud) + pyttsx3 (local fallback)

Priority:
1. ElevenLabs (cloud) — highest quality, natural voice
2. pyttsx3 (local) — fallback when offline or ElevenLabs unavailable

Per USER_STORIES.md (Dorothy): speech rate must be configurable.
Per USER_STORIES.md (Jordan): text-only mode must work with no TTS at all.
Per USER_STORIES.md (Marcus): brief mode — no preamble, concise responses.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Voice ID for ElevenLabs (can be user-configured)
DEFAULT_ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # "Bella" — clear, natural

# Speech rate range: 0.5 (very slow) to 2.0 (fast)
# Default 1.0. Dorothy default: 0.75.
DEFAULT_SPEECH_RATE = 1.0


async def synthesize_speech(
    text: str,
    speed: float = DEFAULT_SPEECH_RATE,
    voice_id: Optional[str] = None,
) -> Optional[bytes]:
    """
    Convert text to speech audio bytes.

    Tries ElevenLabs first; falls back to pyttsx3 if unavailable.

    Args:
        text: Text to speak
        speed: Speech rate (0.5 = slow, 1.0 = normal, 2.0 = fast)
        voice_id: ElevenLabs voice ID (uses default if None)

    Returns:
        MP3 audio bytes, or None if TTS is unavailable
    """
    # Try ElevenLabs first
    audio = await _elevenlabs_tts(text, speed=speed, voice_id=voice_id)
    if audio:
        return audio

    # Fall back to local pyttsx3
    logger.info("ElevenLabs unavailable, using local TTS")
    return await _pyttsx3_tts(text, speed=speed)


async def _elevenlabs_tts(
    text: str,
    speed: float = DEFAULT_SPEECH_RATE,
    voice_id: Optional[str] = None,
) -> Optional[bytes]:
    """ElevenLabs cloud TTS."""
    try:
        from blind_assistant.security.credentials import (
            get_credential,
            ELEVENLABS_API_KEY,
        )

        api_key = get_credential(ELEVENLABS_API_KEY)
        if not api_key:
            return None  # Fall through to local

        from elevenlabs.client import AsyncElevenLabs

        client = AsyncElevenLabs(api_key=api_key)
        vid = voice_id or DEFAULT_ELEVENLABS_VOICE_ID

        # ElevenLabs speed is controlled via voice settings
        # speed 0.5 → stability 0.8; speed 1.0 → stability 0.5; speed 2.0 → stability 0.2
        stability = max(0.1, min(0.9, 1.0 - (speed - 0.5) * 0.4))

        audio_generator = await client.generate(
            text=text,
            voice=vid,
            model="eleven_turbo_v2",
            voice_settings={
                "stability": stability,
                "similarity_boost": 0.75,
            },
        )

        # Collect all chunks
        audio_bytes = b"".join(
            chunk async for chunk in audio_generator
            if isinstance(chunk, bytes)
        )
        return audio_bytes if audio_bytes else None

    except Exception as e:
        logger.warning(f"ElevenLabs TTS failed: {e}")
        return None


async def _pyttsx3_tts(
    text: str,
    speed: float = DEFAULT_SPEECH_RATE,
) -> Optional[bytes]:
    """
    Local pyttsx3 TTS (no internet required).
    Lower quality but always available.

    Returns WAV bytes.
    """
    try:
        import pyttsx3
        import io
        import tempfile
        import os

        loop = asyncio.get_event_loop()

        def _synth() -> bytes:
            engine = pyttsx3.init()
            # pyttsx3 rate is words per minute; normal = 200
            # speed 1.0 = 200 wpm; speed 0.75 = 150 wpm
            engine.setProperty("rate", int(200 * speed))
            engine.setProperty("volume", 0.9)

            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            ) as tmp:
                tmp_path = tmp.name

            try:
                engine.save_to_file(text, tmp_path)
                engine.runAndWait()
                with open(tmp_path, "rb") as f:
                    return f.read()
            finally:
                os.unlink(tmp_path)

        return await loop.run_in_executor(None, _synth)

    except Exception as e:
        logger.error(f"Local TTS failed: {e}", exc_info=True)
        return None


async def speak_locally(
    text: str,
    speed: float = DEFAULT_SPEECH_RATE,
) -> None:
    """
    Speak text through the local speaker immediately.
    Used by the local voice interface and installer.
    """
    try:
        import pyttsx3

        loop = asyncio.get_event_loop()

        def _speak() -> None:
            engine = pyttsx3.init()
            engine.setProperty("rate", int(200 * speed))
            engine.setProperty("volume", 0.9)
            engine.say(text)
            engine.runAndWait()

        await loop.run_in_executor(None, _speak)

    except Exception as e:
        logger.error(f"Local speak failed: {e}")
        # Print to stdout as last resort — at least something gets through
        print(f"[SPEECH]: {text}")
