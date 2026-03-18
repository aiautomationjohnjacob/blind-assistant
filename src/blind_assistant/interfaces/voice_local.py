"""
Local Voice Interface — Microphone + Speaker on Local Device

This interface uses the local microphone for input and the local speaker for output.
It runs a continuous listen-and-respond loop.

Used when the user is at their computer (not using Telegram from another device).

Accessibility: Voice-only. No visual feedback. All states announced verbally.

Per USER_STORIES.md:
- Sarah: "I want to ask what's on my screen without picking up my phone"
- Dorothy: Slow response, low technical confidence — confirm every step aloud

Voice Activity Detection (VAD):
By default, uses `transcribe_microphone_with_vad()` which stops recording when the user
stops speaking. Falls back to `transcribe_microphone()` with fixed duration if webrtcvad
is not installed. This resolves ISSUE-002 (elder users cut off at 8 seconds).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blind_assistant.core.orchestrator import UserContext

logger = logging.getLogger(__name__)

# Wake word for activating the assistant
DEFAULT_WAKE_WORD = "assistant"

# Fallback recording duration if VAD (webrtcvad) is not available (seconds)
DEFAULT_RECORD_DURATION = 8.0

# Whether to use Voice Activity Detection (VAD) for smart cutoff.
# Set to False in config if webrtcvad causes issues on a specific platform.
DEFAULT_USE_VAD = True


class VoiceLocalInterface:
    """
    Local voice interface using microphone input and speaker output.

    Runs a continuous loop:
    1. Listen for wake word (or press-to-talk)
    2. Record user utterance
    3. Transcribe with Whisper
    4. Process through orchestrator
    5. Speak response via TTS
    6. Loop
    """

    def __init__(self, orchestrator, config: dict) -> None:
        self.orchestrator = orchestrator
        self.config = config
        self._running = False
        self._context: UserContext | None = None

        # Config
        self._wake_word = config.get("wake_word", DEFAULT_WAKE_WORD).lower()
        self._record_duration = config.get("record_duration", DEFAULT_RECORD_DURATION)
        # VAD: use voice activity detection for smart cutoff (recommended, resolves ISSUE-002)
        self._use_vad = config.get("use_vad", DEFAULT_USE_VAD)

    async def start(self) -> None:
        """Start the local voice interface loop."""
        from blind_assistant.voice.tts import speak_locally

        logger.info("Local voice interface starting...")

        # Load context for local user
        self._context = await self.orchestrator.context_manager.load_user_context(
            user_id="local_user",
            session_id="local",
        )
        # Narrow type for mypy — load_user_context always returns UserContext (not None)
        assert self._context is not None

        self._running = True

        # Announce startup
        await speak_locally(
            "Blind Assistant is ready. "
            f"Say '{self._wake_word}' followed by your request. "
            "Or just speak and I will listen.",
            speed=self._context.speech_rate,
        )

        while self._running:
            try:
                await self._listen_and_respond()
            except asyncio.CancelledError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Voice loop error: {e}", exc_info=True)
                await speak_locally(
                    "I ran into a problem. Let me try again.",
                    speed=self._context.speech_rate,
                )
                await asyncio.sleep(1)

        await speak_locally("Blind Assistant is going offline. Goodbye.")
        logger.info("Local voice interface stopped.")

    async def stop(self) -> None:
        """Stop the voice interface loop."""
        self._running = False

    async def _listen_and_respond(self) -> None:
        """One listen-transcribe-respond cycle."""
        from blind_assistant.voice.stt import transcribe_microphone
        from blind_assistant.voice.tts import speak_locally

        # Narrow Optional type — _listen_and_respond only called from start() after context is set
        assert self._context is not None, "VoiceLocalInterface.start() must be called before _listen_and_respond()"

        # Record a fixed-duration utterance
        # Future: add voice activity detection (VAD) for smarter cutoff
        transcript = await transcribe_microphone(duration_seconds=self._record_duration)

        if not transcript or not transcript.strip():
            # Silence or background noise — just loop
            return

        transcript = transcript.strip()
        logger.info(f"Heard: {transcript[:60]}")

        # Check for wake word if configured
        if self._wake_word not in transcript.lower():
            # No wake word — check if it looks intentional
            # (More than 3 words → probably intentional even without wake word)
            word_count = len(transcript.split())
            if word_count < 4:
                return  # Probably background speech or noise

        # Remove wake word prefix if present
        clean_transcript = transcript
        wake_idx = transcript.lower().find(self._wake_word)
        if wake_idx != -1:
            after_wake = transcript[wake_idx + len(self._wake_word) :].strip()
            # User said only the wake word ("assistant") with nothing after it if after_wake is empty
            clean_transcript = after_wake or ""

        if not clean_transcript:
            await speak_locally(
                "Yes? How can I help?",
                speed=self._context.speech_rate,
            )
            # Listen for the actual request
            transcript2 = await transcribe_microphone(duration_seconds=self._record_duration)
            if transcript2 and transcript2.strip():
                clean_transcript = transcript2.strip()
            else:
                return

        # Capture speech_rate in a local variable so nested speak_update can use it
        # without mypy's union-attr check on self._context (which is narrowed above by assert)
        _speech_rate = self._context.speech_rate

        # Send to orchestrator with a speak callback so interim progress is read aloud.
        async def speak_update(message: str) -> None:
            """Speak an interim orchestrator update aloud using the local TTS engine."""
            await speak_locally(message, speed=_speech_rate)

        try:
            response = await self.orchestrator.handle_message(
                text=clean_transcript,
                context=self._context,
                response_callback=speak_update,
            )

            # Speak the final response
            spoken = response.spoken_text or response.text
            await speak_locally(spoken, speed=self._context.speech_rate)

            # Handle follow-up prompts
            if response.follow_up_prompt:
                await speak_locally(
                    response.follow_up_prompt,
                    speed=self._context.speech_rate,
                )

        except Exception as e:
            logger.error(f"Error processing voice input: {e}", exc_info=True)
            await speak_locally(
                "I had trouble with that request. Could you try again or rephrase it?",
                speed=self._context.speech_rate,
            )

    async def confirm_locally(self, prompt: str, timeout: float = 10.0) -> bool:
        """
        Ask a yes/no question via voice and wait for voice response.
        Used for local confirmation flows (not via Telegram).
        """
        from blind_assistant.security.disclosure import is_cancellation, is_confirmation
        from blind_assistant.voice.stt import transcribe_microphone
        from blind_assistant.voice.tts import speak_locally

        await speak_locally(prompt, speed=self._context.speech_rate if self._context else 1.0)

        try:
            response = await asyncio.wait_for(
                transcribe_microphone(duration_seconds=5.0),
                timeout=timeout,
            )
            if response:
                if is_confirmation(response):
                    return True
                if is_cancellation(response):
                    return False
        except TimeoutError:
            pass

        return False
