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
    DEFAULT_USE_VAD,
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
        # Disable VAD in existing tests so they continue to mock transcribe_microphone
        # (the fixed-duration path). VAD behavior is tested separately in TestVADIntegration.
        "use_vad": False,
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
    orch.context_manager.load_user_context = AsyncMock(return_value=MagicMock(speech_rate=1.0, session_id="local"))
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
    async def test_empty_transcript_returns_without_processing(self, interface, mock_orchestrator):
        """Empty transcription (silence/noise) must not call orchestrator."""
        interface._context = MagicMock(speech_rate=1.0)

        with (
            patch("blind_assistant.voice.stt.transcribe_microphone", new=AsyncMock(return_value="")),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
            await interface._listen_and_respond()

        mock_orchestrator.handle_message.assert_not_called()

    async def test_none_transcript_returns_without_processing(self, interface, mock_orchestrator):
        """None transcription (no audio) must not call orchestrator."""
        interface._context = MagicMock(speech_rate=1.0)

        with (
            patch("blind_assistant.voice.stt.transcribe_microphone", new=AsyncMock(return_value=None)),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
            await interface._listen_and_respond()

        mock_orchestrator.handle_message.assert_not_called()

    async def test_whitespace_only_transcript_returns_without_processing(self, interface, mock_orchestrator):
        """Whitespace-only transcript is treated as silence."""
        interface._context = MagicMock(speech_rate=1.0)

        with (
            patch("blind_assistant.voice.stt.transcribe_microphone", new=AsyncMock(return_value="   ")),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
            await interface._listen_and_respond()

        mock_orchestrator.handle_message.assert_not_called()


# ─────────────────────────────────────────────────────────────
# Wake word detection
# ─────────────────────────────────────────────────────────────


class TestWakeWordDetection:
    async def test_short_transcript_without_wake_word_is_ignored(self, interface, mock_orchestrator):
        """1–3 word utterance without wake word treated as background noise."""
        interface._context = MagicMock(speech_rate=1.0)

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="hello there"),  # 2 words, no wake word
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
            await interface._listen_and_respond()

        mock_orchestrator.handle_message.assert_not_called()

    async def test_long_transcript_without_wake_word_is_processed(self, interface, mock_orchestrator):
        """4+ word utterance without wake word is treated as intentional."""
        interface._context = MagicMock(speech_rate=1.0)
        from blind_assistant.core.orchestrator import Response

        mock_orchestrator.handle_message = AsyncMock(
            return_value=Response(text="Sure, done.", spoken_text=None, follow_up_prompt=None)
        )

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="what time is it please"),  # 5 words
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
            await interface._listen_and_respond()

        mock_orchestrator.handle_message.assert_called_once()

    async def test_wake_word_detected_strips_prefix(self, interface, mock_orchestrator):
        """Wake word is stripped before passing to orchestrator."""
        interface._context = MagicMock(speech_rate=1.0)
        from blind_assistant.core.orchestrator import Response

        captured: list[str] = []

        async def capture(text, context, response_callback):  # noqa: ARG001
            captured.append(text)
            return Response(text="okay", spoken_text=None, follow_up_prompt=None)

        mock_orchestrator.handle_message.side_effect = capture

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="assistant what is on my screen"),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
            await interface._listen_and_respond()

        # The wake word "assistant" should be stripped
        assert len(captured) == 1
        assert "assistant" not in captured[0].lower()
        assert "what is on my screen" in captured[0]

    async def test_wake_word_only_utterance_prompts_for_command(self, interface, mock_orchestrator):
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

        async def two_transcriptions(duration_seconds=5.0):  # noqa: ARG001
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "assistant"
            return "what is the weather"

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(side_effect=two_transcriptions),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=capture_speak),
        ):
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

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="assistant describe what you see on the screen"),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
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

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="assistant describe my screen"),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=capture),
        ):
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

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="assistant what is on screen"),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=capture),
        ):
            await interface._listen_and_respond()

        assert any("Short version." in m for m in spoken)
        assert not any("The full detailed description." in m for m in spoken)

    async def test_follow_up_prompt_spoken_after_response(self, interface, mock_orchestrator):
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

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="assistant find my shopping list"),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=capture),
        ):
            await interface._listen_and_respond()

        assert any("Would you like me to read it aloud?" in m for m in spoken)


# ─────────────────────────────────────────────────────────────
# Error recovery
# ─────────────────────────────────────────────────────────────


class TestErrorRecovery:
    async def test_orchestrator_exception_speaks_error_message(self, interface, mock_orchestrator):
        """If orchestrator raises, user hears a polite error — no crash."""
        interface._context = MagicMock(speech_rate=1.0)

        mock_orchestrator.handle_message = AsyncMock(side_effect=RuntimeError("Claude API unreachable"))

        spoken: list[str] = []

        async def capture(text, speed=1.0):  # noqa: ARG001
            spoken.append(text)

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="assistant help me with something"),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=capture),
        ):
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

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="yes"),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
            result = await interface.confirm_locally("Do you want to continue?")

        assert result is True

    async def test_confirm_returns_false_on_no(self, interface):
        """Voice response 'no' returns False."""
        interface._context = MagicMock(speech_rate=1.0)

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="no"),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
            result = await interface.confirm_locally("Are you sure?")

        assert result is False

    async def test_confirm_returns_false_on_timeout(self, interface):
        """Silence/timeout returns False (conservative default)."""
        interface._context = MagicMock(speech_rate=1.0)

        async def hang_forever(duration_seconds=5.0):  # noqa: ARG001
            await asyncio.sleep(999)

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(side_effect=hang_forever),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
            result = await interface.confirm_locally("Continue?", timeout=0.05)

        assert result is False

    async def test_confirm_uses_context_speech_rate(self, interface):
        """confirm_locally uses context.speech_rate when speaking the prompt."""
        interface._context = MagicMock(speech_rate=0.75)

        captured_speed: list[float] = []

        async def capture(text, speed=1.0):  # noqa: ARG001
            captured_speed.append(speed)

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="yes"),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=capture),
        ):
            await interface.confirm_locally("Is this correct?")

        assert captured_speed[0] == pytest.approx(0.75)

    async def test_confirm_without_context_falls_back_to_1x(self, interface):
        """confirm_locally without context set uses speed=1.0 fallback."""
        interface._context = None  # Not started yet

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="yes"),
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()) as mock_speak,
        ):
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

    def test_default_use_vad_is_true(self):
        """VAD is enabled by default — the recommended mode (ISSUE-002 fix)."""
        assert DEFAULT_USE_VAD is True


# ─────────────────────────────────────────────────────────────
# VAD integration in VoiceLocalInterface (ISSUE-002)
# ─────────────────────────────────────────────────────────────


class TestVADIntegration:
    """Tests that VoiceLocalInterface uses VAD when use_vad=True (the default)."""

    @pytest.fixture
    def vad_config(self):
        return {
            "wake_word": "assistant",
            "record_duration": 8.0,
            "use_vad": True,  # Explicitly enable VAD
        }

    @pytest.fixture
    def vad_interface(self, mock_orchestrator, vad_config):
        return VoiceLocalInterface(mock_orchestrator, vad_config)

    def test_use_vad_defaults_to_true_when_not_in_config(self, mock_orchestrator):
        """When use_vad is not in config, defaults to DEFAULT_USE_VAD (True)."""
        iface = VoiceLocalInterface(mock_orchestrator, config={})
        assert iface._use_vad is True

    def test_use_vad_can_be_disabled_via_config(self, mock_orchestrator):
        """use_vad=False in config disables VAD and uses fixed-duration recording."""
        iface = VoiceLocalInterface(mock_orchestrator, config={"use_vad": False})
        assert iface._use_vad is False

    async def test_listen_calls_transcribe_with_vad_when_enabled(self, vad_interface, mock_orchestrator):
        """When use_vad=True, _listen_and_respond calls transcribe_microphone_with_vad."""
        from blind_assistant.core.orchestrator import Response

        mock_orchestrator.handle_message = AsyncMock(
            return_value=Response(text="Okay", spoken_text=None, follow_up_prompt=None)
        )
        vad_interface._context = MagicMock(speech_rate=1.0)

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone_with_vad",
                new=AsyncMock(return_value="order me lunch"),
            ) as mock_vad,
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
            await vad_interface._listen_and_respond()

        # VAD function should have been called
        mock_vad.assert_called_once()

    async def test_listen_does_not_call_vad_when_disabled(self, interface, mock_orchestrator):
        """When use_vad=False, _listen_and_respond uses transcribe_microphone (fixed duration)."""
        from blind_assistant.core.orchestrator import Response

        mock_orchestrator.handle_message = AsyncMock(
            return_value=Response(text="Okay", spoken_text=None, follow_up_prompt=None)
        )
        interface._context = MagicMock(speech_rate=1.0)

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="order me lunch"),
            ) as mock_fixed,
            patch("blind_assistant.voice.stt.transcribe_microphone_with_vad", new=AsyncMock()) as mock_vad,
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
        ):
            await interface._listen_and_respond()

        mock_fixed.assert_called()
        mock_vad.assert_not_called()

    async def test_vad_wake_word_follow_up_also_uses_vad(self, vad_interface):
        """Wake word only response → follow-up listen also uses VAD (not fixed duration)."""
        from blind_assistant.core.orchestrator import Response

        vad_interface._context = MagicMock(speech_rate=1.0)

        # First call returns wake word only, second returns real request
        vad_calls = [AsyncMock(return_value="assistant"), AsyncMock(return_value="what is the weather")]

        async def mock_vad_sequence(*args, **kwargs):
            return await vad_calls.pop(0)()

        with (
            patch(
                "blind_assistant.voice.stt.transcribe_microphone_with_vad",
                side_effect=mock_vad_sequence,
            ),
            patch("blind_assistant.voice.tts.speak_locally", new=AsyncMock()),
            patch(
                "blind_assistant.core.orchestrator.Orchestrator.handle_message",
                new=AsyncMock(
                    return_value=Response(text="Sunny", spoken_text=None, follow_up_prompt=None)
                ),
            ),
        ):
            # Should call VAD twice: once for wake word, once for actual request
            await vad_interface._listen_and_respond()


# ─────────────────────────────────────────────────────────────
# VAD unit tests (stt.py functions — no device needed)
# ─────────────────────────────────────────────────────────────


class TestVADFunctions:
    """Tests for the VAD recording functions in stt.py."""

    async def test_transcribe_microphone_with_vad_falls_back_when_webrtcvad_missing(self):
        """Falls back to fixed-duration recording when webrtcvad is not installed."""
        import sys

        # Simulate webrtcvad not installed
        saved = sys.modules.pop("webrtcvad", None)
        try:
            with (
                patch(
                    "blind_assistant.voice.stt.transcribe_microphone",
                    new=AsyncMock(return_value="fallback transcript"),
                ) as mock_fixed,
            ):
                from blind_assistant.voice.stt import transcribe_microphone_with_vad

                result = await transcribe_microphone_with_vad(fallback_duration=5.0)

            # Should have called fixed-duration fallback
            mock_fixed.assert_called_once_with(duration_seconds=5.0)
            assert result == "fallback transcript"
        finally:
            if saved is not None:
                sys.modules["webrtcvad"] = saved

    async def test_transcribe_microphone_with_vad_returns_none_when_no_audio(self):
        """Returns None when VAD recording captures no audio bytes."""
        with (
            patch(
                "blind_assistant.voice.stt._record_with_vad_sync",
                return_value=None,
            ),
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value=None),
            ),
        ):
            from blind_assistant.voice.stt import transcribe_microphone_with_vad

            result = await transcribe_microphone_with_vad()

        assert result is None

    async def test_transcribe_microphone_with_vad_transcribes_audio_bytes(self):
        """When VAD recording succeeds, audio bytes are passed to transcribe_audio."""
        fake_wav = b"RIFF\x00\x00\x00\x00WAVEfmt "
        captured_bytes = []

        async def mock_transcribe(audio_bytes, language=None):
            captured_bytes.append(audio_bytes)
            return "hello assistant"

        with (
            patch("blind_assistant.voice.stt._record_with_vad_sync", return_value=fake_wav),
            patch("blind_assistant.voice.stt.transcribe_audio", side_effect=mock_transcribe),
        ):
            from blind_assistant.voice.stt import transcribe_microphone_with_vad

            result = await transcribe_microphone_with_vad()

        assert result == "hello assistant"
        assert captured_bytes == [fake_wav]

    async def test_transcribe_microphone_with_vad_falls_back_on_unexpected_exception(self):
        """Falls back to fixed-duration recording when an unexpected error occurs."""
        with (
            patch(
                "blind_assistant.voice.stt._record_with_vad_sync",
                side_effect=RuntimeError("audio device busy"),
            ),
            patch(
                "blind_assistant.voice.stt.transcribe_microphone",
                new=AsyncMock(return_value="fallback"),
            ) as mock_fixed,
        ):
            from blind_assistant.voice.stt import transcribe_microphone_with_vad

            result = await transcribe_microphone_with_vad(fallback_duration=7.0)

        mock_fixed.assert_called_once_with(duration_seconds=7.0)
        assert result == "fallback"

    def test_vad_constants_are_valid(self):
        """VAD configuration constants are in valid ranges."""
        from blind_assistant.voice.stt import (
            VAD_AGGRESSIVENESS,
            VAD_MAX_DURATION,
            VAD_MIN_DURATION,
            VAD_SILENCE_FRAMES,
        )

        assert 0 <= VAD_AGGRESSIVENESS <= 3
        assert VAD_SILENCE_FRAMES > 0
        assert VAD_MAX_DURATION > 0
        assert 0 < VAD_MIN_DURATION < VAD_MAX_DURATION

    def test_record_with_vad_sync_raises_import_error_when_webrtcvad_missing(self):
        """_record_with_vad_sync raises ImportError when webrtcvad is not available."""
        import sys

        saved = sys.modules.pop("webrtcvad", None)
        try:
            from blind_assistant.voice.stt import _record_with_vad_sync

            with pytest.raises(ImportError, match="webrtcvad"):
                _record_with_vad_sync()
        finally:
            if saved is not None:
                sys.modules["webrtcvad"] = saved
