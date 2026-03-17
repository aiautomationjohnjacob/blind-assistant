"""
Unit tests for blind_assistant.interfaces.voice_local

Covers:
- VoiceLocalInterface initialization
- _listen_and_respond: silence, wake word detection, message routing
- confirm_locally: voice confirmation gate
- Error recovery in the voice loop
- Wake word detection and stripping
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.interfaces.voice_local import (
    DEFAULT_RECORD_DURATION,
    DEFAULT_WAKE_WORD,
    ELDER_RECORD_DURATION,
    VoiceLocalInterface,
)

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def minimal_config():
    return {
        "wake_word": "assistant",
        "record_duration": 8.0,
    }


@pytest.fixture
def mock_orchestrator():
    """Fully mocked orchestrator that returns a canned Response."""
    from blind_assistant.core.orchestrator import Response

    orch = MagicMock()
    orch.handle_message = AsyncMock(
        return_value=Response(text="I can help with that.", spoken_text=None, follow_up_prompt=None)
    )
    orch.context_manager = MagicMock()
    orch.context_manager.load_user_context = AsyncMock(
        return_value=MagicMock(speech_rate=1.0, session_id="local")
    )
    return orch


@pytest.fixture
def interface(mock_orchestrator, minimal_config):
    return VoiceLocalInterface(mock_orchestrator, minimal_config)


# ─────────────────────────────────────────────────────────────
# Initialization
# ─────────────────────────────────────────────────────────────


class TestVoiceLocalInit:
    def test_defaults_from_config(self, interface, minimal_config):
        """Wake word and duration are read from config at init time."""
        assert interface._wake_word == minimal_config["wake_word"].lower()
        assert interface._record_duration == minimal_config["record_duration"]

    def test_fallback_defaults_when_config_empty(self, mock_orchestrator):
        """When config has no wake_word/record_duration, defaults are used."""
        iface = VoiceLocalInterface(mock_orchestrator, config={})
        assert iface._wake_word == DEFAULT_WAKE_WORD
        assert iface._record_duration == DEFAULT_RECORD_DURATION

    def test_not_running_on_create(self, interface):
        assert interface._running is False

    def test_context_is_none_before_start(self, interface):
        assert interface._context is None


# ─────────────────────────────────────────────────────────────
# _listen_and_respond: silence handling
# ─────────────────────────────────────────────────────────────


class TestListenAndRespondSilence:
    async def test_empty_transcript_returns_without_processing(
        self, interface, mock_orchestrator
    ):
        """Empty transcription (silence/noise) must not call orchestrator."""
        interface._context = MagicMock(speech_rate=1.0)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone", new=AsyncMock(return_value="")
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()):
            await interface._listen_and_respond()

        mock_orchestrator.handle_message.assert_not_called()

    async def test_none_transcript_returns_without_processing(
        self, interface, mock_orchestrator
    ):
        """None transcription (no audio) must not call orchestrator."""
        interface._context = MagicMock(speech_rate=1.0)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone", new=AsyncMock(return_value=None)
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()):
            await interface._listen_and_respond()

        mock_orchestrator.handle_message.assert_not_called()

    async def test_whitespace_only_transcript_returns_without_processing(
        self, interface, mock_orchestrator
    ):
        """Whitespace-only transcript is treated as silence."""
        interface._context = MagicMock(speech_rate=1.0)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone", new=AsyncMock(return_value="   ")
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()):
            await interface._listen_and_respond()

        mock_orchestrator.handle_message.assert_not_called()


# ─────────────────────────────────────────────────────────────
# Wake word detection
# ─────────────────────────────────────────────────────────────


class TestWakeWordDetection:
    async def test_short_transcript_without_wake_word_is_ignored(
        self, interface, mock_orchestrator
    ):
        """1–3 word utterance without wake word treated as background noise."""
        interface._context = MagicMock(speech_rate=1.0)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="hello there"),  # 2 words, no wake word
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()):
            await interface._listen_and_respond()

        mock_orchestrator.handle_message.assert_not_called()

    async def test_long_transcript_without_wake_word_is_processed(
        self, interface, mock_orchestrator
    ):
        """4+ word utterance without wake word is treated as intentional."""
        interface._context = MagicMock(speech_rate=1.0)
        from blind_assistant.core.orchestrator import Response

        mock_orchestrator.handle_message = AsyncMock(
            return_value=Response(text="Sure, done.", spoken_text=None, follow_up_prompt=None)
        )

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="what time is it please"),  # 5 words
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()):
            await interface._listen_and_respond()

        mock_orchestrator.handle_message.assert_called_once()

    async def test_wake_word_detected_strips_prefix(
        self, interface, mock_orchestrator
    ):
        """Wake word is stripped before passing to orchestrator."""
        interface._context = MagicMock(speech_rate=1.0)
        from blind_assistant.core.orchestrator import Response

        captured: list[str] = []

        async def capture(text, context, response_callback):  # noqa: ARG001
            captured.append(text)
            return Response(text="okay", spoken_text=None, follow_up_prompt=None)

        mock_orchestrator.handle_message.side_effect = capture

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="assistant what is on my screen"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()):
            await interface._listen_and_respond()

        # The wake word "assistant" should be stripped
        assert len(captured) == 1
        assert "assistant" not in captured[0].lower()
        assert "what is on my screen" in captured[0]

    async def test_wake_word_only_utterance_prompts_for_command(
        self, interface, mock_orchestrator
    ):
        """'assistant' with nothing after it speaks 'Yes?' and awaits another transcription."""
        interface._context = MagicMock(speech_rate=1.0)
        from blind_assistant.core.orchestrator import Response

        mock_orchestrator.handle_message = AsyncMock(
            return_value=Response(text="done", spoken_text=None, follow_up_prompt=None)
        )

        spoken_messages: list[str] = []

        async def capture_speak(text, speed=1.0):  # noqa: ARG001
            spoken_messages.append(text)

        call_count = 0

        async def two_transcriptions():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "assistant"
            return "what is the weather"

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(side_effect=two_transcriptions),
        ), patch("blind_assistant.voice.tts.speak_locally", new=capture_speak):
            await interface._listen_and_respond()

        # Should have spoken the "Yes?" prompt
        assert any("yes" in m.lower() for m in spoken_messages)


# ─────────────────────────────────────────────────────────────
# Orchestrator routing
# ─────────────────────────────────────────────────────────────


class TestListenAndRespondRouting:
    async def test_message_routed_to_orchestrator(self, interface, mock_orchestrator):
        """Transcribed text is forwarded to orchestrator.handle_message."""
        interface._context = MagicMock(speech_rate=1.0)
        from blind_assistant.core.orchestrator import Response

        mock_orchestrator.handle_message = AsyncMock(
            return_value=Response(text="Done!", spoken_text=None, follow_up_prompt=None)
        )

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="assistant describe what you see on the screen"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()):
            await interface._listen_and_respond()

        mock_orchestrator.handle_message.assert_called_once()

    async def test_orchestrator_response_spoken_aloud(self, interface, mock_orchestrator):
        """The response text from orchestrator is spoken via TTS."""
        interface._context = MagicMock(speech_rate=1.0)
        from blind_assistant.core.orchestrator import Response

        mock_orchestrator.handle_message = AsyncMock(
            return_value=Response(text="Your screen shows a browser.", spoken_text=None, follow_up_prompt=None)
        )

        spoken: list[str] = []

        async def capture(text, speed=1.0):  # noqa: ARG001
            spoken.append(text)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="assistant describe my screen"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=capture):
            await interface._listen_and_respond()

        assert any("Your screen shows a browser." in m for m in spoken)

    async def test_spoken_text_preferred_over_text(self, interface, mock_orchestrator):
        """When spoken_text is different from text, spoken_text is played."""
        interface._context = MagicMock(speech_rate=1.0)
        from blind_assistant.core.orchestrator import Response

        mock_orchestrator.handle_message = AsyncMock(
            return_value=Response(
                text="The full detailed description.",
                spoken_text="Short version.",
                follow_up_prompt=None,
            )
        )

        spoken: list[str] = []

        async def capture(text, speed=1.0):  # noqa: ARG001
            spoken.append(text)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="assistant what is on screen"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=capture):
            await interface._listen_and_respond()

        assert any("Short version." in m for m in spoken)
        assert not any("The full detailed description." in m for m in spoken)

    async def test_follow_up_prompt_spoken_after_response(
        self, interface, mock_orchestrator
    ):
        """If orchestrator provides a follow_up_prompt, it is spoken after the main response."""
        interface._context = MagicMock(speech_rate=1.0)
        from blind_assistant.core.orchestrator import Response

        mock_orchestrator.handle_message = AsyncMock(
            return_value=Response(
                text="I found a note.",
                spoken_text=None,
                follow_up_prompt="Would you like me to read it aloud?",
            )
        )

        spoken: list[str] = []

        async def capture(text, speed=1.0):  # noqa: ARG001
            spoken.append(text)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="assistant find my shopping list"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=capture):
            await interface._listen_and_respond()

        assert any("Would you like me to read it aloud?" in m for m in spoken)


# ─────────────────────────────────────────────────────────────
# Error recovery
# ─────────────────────────────────────────────────────────────


class TestErrorRecovery:
    async def test_orchestrator_exception_speaks_error_message(
        self, interface, mock_orchestrator
    ):
        """If orchestrator raises, user hears a polite error — no crash."""
        interface._context = MagicMock(speech_rate=1.0)

        mock_orchestrator.handle_message = AsyncMock(
            side_effect=RuntimeError("Claude API unreachable")
        )

        spoken: list[str] = []

        async def capture(text, speed=1.0):  # noqa: ARG001
            spoken.append(text)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="assistant help me with something"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=capture):
            await interface._listen_and_respond()

        # User should hear an error message, not a silence
        assert any(len(m) > 5 for m in spoken), "Expected at least one spoken error message"

    async def test_stop_sets_running_false(self, interface):
        """stop() sets _running to False."""
        interface._running = True
        await interface.stop()
        assert interface._running is False


# ─────────────────────────────────────────────────────────────
# confirm_locally
# ─────────────────────────────────────────────────────────────


class TestConfirmLocally:
    async def test_confirm_returns_true_on_yes(self, interface):
        """Voice response 'yes' returns True."""
        interface._context = MagicMock(speech_rate=1.0)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="yes"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()):
            result = await interface.confirm_locally("Do you want to continue?")

        assert result is True

    async def test_confirm_returns_false_on_no(self, interface):
        """Voice response 'no' returns False."""
        interface._context = MagicMock(speech_rate=1.0)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="no"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()):
            result = await interface.confirm_locally("Are you sure?")

        assert result is False

    async def test_confirm_returns_false_on_timeout(self, interface):
        """Silence/timeout returns False (conservative default)."""
        interface._context = MagicMock(speech_rate=1.0)

        async def hang_forever():
            await asyncio.sleep(999)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(side_effect=hang_forever),
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()):
            result = await interface.confirm_locally("Continue?", timeout=0.05)

        assert result is False

    async def test_confirm_uses_context_speech_rate(self, interface):
        """confirm_locally uses context.speech_rate when speaking the prompt."""
        interface._context = MagicMock(speech_rate=0.75)

        captured_speed: list[float] = []

        async def capture(text, speed=1.0):  # noqa: ARG001
            captured_speed.append(speed)

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="yes"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=capture):
            await interface.confirm_locally("Is this correct?")

        assert captured_speed[0] == pytest.approx(0.75)

    async def test_confirm_without_context_falls_back_to_1x(self, interface):
        """confirm_locally without context set uses speed=1.0 fallback."""
        interface._context = None  # Not started yet

        with patch(
            "blind_assistant.voice.stt.transcribe_microphone",
            new=AsyncMock(return_value="yes"),
        ), patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()) as mock_speak:
            await interface.confirm_locally("Okay?")

        # Should not crash — just use fallback speed
        mock_speak.assert_called()


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────


class TestConstants:
    def test_default_wake_word_is_assistant(self):
        assert DEFAULT_WAKE_WORD == "assistant"

    def test_default_record_duration_is_positive(self):
        assert DEFAULT_RECORD_DURATION > 0

    def test_elder_record_duration_longer_than_default(self):
        """Elder users need more time to speak — elder duration must exceed default."""
        assert ELDER_RECORD_DURATION > DEFAULT_RECORD_DURATION
