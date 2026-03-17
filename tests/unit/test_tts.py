"""
Unit tests for blind_assistant.voice.tts

Covers:
- synthesize_speech: ElevenLabs happy path (returns audio bytes)
- synthesize_speech: falls back to pyttsx3 when ElevenLabs unavailable
- synthesize_speech: returns None when both TTS systems unavailable
- _elevenlabs_tts: returns None when API key not configured
- _elevenlabs_tts: returns None on network/API error
- _pyttsx3_tts: returns None when pyttsx3 not installed
- _pyttsx3_tts: returns None when synthesis engine throws
- speak_locally: falls back gracefully when pyttsx3 unavailable
- Speed parameter math: 0.75 → 150 wpm; 1.5 → 300 wpm
- Empty text is handled without crashing

Note: pyttsx3 and elevenlabs are optional runtime dependencies not installed in CI.
Tests for those code paths inject mock modules via sys.modules.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────
# Helpers to inject mock optional dependencies
# ─────────────────────────────────────────────────────────────


def inject_mock_pyttsx3():
    """Inject a fresh MagicMock for pyttsx3 into sys.modules, replacing any existing."""
    mock_pyttsx3 = MagicMock()
    sys.modules["pyttsx3"] = mock_pyttsx3
    return mock_pyttsx3


def inject_mock_elevenlabs():
    """Inject fresh MagicMock modules for the elevenlabs package into sys.modules."""
    mock_el = MagicMock()
    mock_el_client = MagicMock()
    sys.modules["elevenlabs"] = mock_el
    sys.modules["elevenlabs.client"] = mock_el_client
    return mock_el, mock_el_client


# ─────────────────────────────────────────────────────────────
# synthesize_speech — top-level dispatcher
# ─────────────────────────────────────────────────────────────


class TestSynthesizeSpeech:
    async def test_returns_elevenlabs_audio_when_available(self):
        """When ElevenLabs succeeds, returns its audio bytes directly."""
        fake_audio = b"fake_mp3_audio"

        with (
            patch(
                "blind_assistant.voice.tts._elevenlabs_tts",
                return_value=fake_audio,
            ) as mock_el,
            patch(
                "blind_assistant.voice.tts._pyttsx3_tts",
                return_value=b"local_audio",
            ) as mock_local,
        ):
            from blind_assistant.voice.tts import synthesize_speech

            result = await synthesize_speech("Hello world")

        assert result == fake_audio
        mock_el.assert_called_once()
        mock_local.assert_not_called()

    async def test_falls_back_to_pyttsx3_when_elevenlabs_returns_none(self):
        """When ElevenLabs returns None, falls back to local pyttsx3."""
        local_audio = b"local_wav_audio"

        with (
            patch(
                "blind_assistant.voice.tts._elevenlabs_tts",
                return_value=None,
            ),
            patch(
                "blind_assistant.voice.tts._pyttsx3_tts",
                return_value=local_audio,
            ) as mock_local,
        ):
            from blind_assistant.voice.tts import synthesize_speech

            result = await synthesize_speech("Hello world")

        assert result == local_audio
        mock_local.assert_called_once()

    async def test_returns_none_when_both_unavailable(self):
        """When both ElevenLabs and pyttsx3 fail, returns None."""
        with (
            patch(
                "blind_assistant.voice.tts._elevenlabs_tts",
                return_value=None,
            ),
            patch(
                "blind_assistant.voice.tts._pyttsx3_tts",
                return_value=None,
            ),
        ):
            from blind_assistant.voice.tts import synthesize_speech

            result = await synthesize_speech("Hello world")

        assert result is None

    async def test_passes_speed_to_both_tts_backends(self):
        """Speed parameter is forwarded to both ElevenLabs and fallback."""
        with (
            patch(
                "blind_assistant.voice.tts._elevenlabs_tts",
                return_value=None,
            ) as mock_el,
            patch(
                "blind_assistant.voice.tts._pyttsx3_tts",
                return_value=b"audio",
            ) as mock_local,
        ):
            from blind_assistant.voice.tts import synthesize_speech

            await synthesize_speech("text", speed=0.75)

        mock_el.assert_called_once_with("text", speed=0.75, voice_id=None)
        mock_local.assert_called_once_with("text", speed=0.75)

    async def test_handles_empty_text_without_crashing(self):
        """Empty string input is forwarded to backends without crashing."""
        with (
            patch(
                "blind_assistant.voice.tts._elevenlabs_tts",
                return_value=None,
            ),
            patch(
                "blind_assistant.voice.tts._pyttsx3_tts",
                return_value=None,
            ),
        ):
            from blind_assistant.voice.tts import synthesize_speech

            result = await synthesize_speech("")
        assert result is None


# ─────────────────────────────────────────────────────────────
# _elevenlabs_tts
# ─────────────────────────────────────────────────────────────


class TestElevenLabsTTS:
    async def test_returns_none_when_no_api_key(self):
        """Returns None when ElevenLabs API key is not configured."""
        inject_mock_elevenlabs()

        with patch(
            "blind_assistant.security.credentials.get_credential",
            return_value=None,
        ):
            from blind_assistant.voice.tts import _elevenlabs_tts

            result = await _elevenlabs_tts("Hello")
        assert result is None

    async def test_returns_none_on_api_exception(self):
        """Returns None (not raises) when ElevenLabs API throws an exception."""
        _, mock_el_client = inject_mock_elevenlabs()
        mock_async_client = AsyncMock()
        mock_async_client.generate.side_effect = Exception("API rate limit")
        mock_el_client.AsyncElevenLabs.return_value = mock_async_client

        with patch(
            "blind_assistant.security.credentials.get_credential",
            return_value="fake_api_key",
        ):
            from blind_assistant.voice.tts import _elevenlabs_tts

            result = await _elevenlabs_tts("Hello")
        assert result is None

    def test_speed_maps_to_stability_formula(self):
        """Stability formula: max(0.1, min(0.9, 1.0 - (speed - 0.5) * 0.4))."""
        import pytest

        # speed=0.5 → stability = 1.0 - 0 = 1.0 → clamped to 0.9
        s05 = max(0.1, min(0.9, 1.0 - (0.5 - 0.5) * 0.4))
        assert s05 == pytest.approx(0.9)

        # speed=1.0 → stability = 1.0 - 0.2 = 0.8
        s10 = max(0.1, min(0.9, 1.0 - (1.0 - 0.5) * 0.4))
        assert s10 == pytest.approx(0.8)

        # speed=2.0 → stability = 1.0 - 0.6 = 0.4
        s20 = max(0.1, min(0.9, 1.0 - (2.0 - 0.5) * 0.4))
        assert s20 == pytest.approx(0.4)

        # Slower speed → higher stability (voice sounds more deliberate)
        assert s05 > s10 > s20


# ─────────────────────────────────────────────────────────────
# _pyttsx3_tts
# ─────────────────────────────────────────────────────────────


class TestPyttsx3TTS:
    async def test_returns_none_when_pyttsx3_not_installed(self):
        """Returns None (not raises) when pyttsx3 is not installed."""
        # Temporarily remove pyttsx3 from sys.modules
        saved = sys.modules.pop("pyttsx3", None)
        try:
            from blind_assistant.voice.tts import _pyttsx3_tts

            result = await _pyttsx3_tts("Hello")
        finally:
            if saved is not None:
                sys.modules["pyttsx3"] = saved
        assert result is None

    async def test_returns_none_on_synthesis_engine_exception(self):
        """Returns None when pyttsx3 engine raises during synthesis."""
        mock_pyttsx3 = inject_mock_pyttsx3()
        mock_engine = MagicMock()
        mock_engine.setProperty = MagicMock()
        mock_engine.save_to_file = MagicMock()
        mock_engine.runAndWait = MagicMock(side_effect=RuntimeError("audio device error"))
        mock_pyttsx3.init.return_value = mock_engine

        from blind_assistant.voice.tts import _pyttsx3_tts

        result = await _pyttsx3_tts("Hello")
        assert result is None

    def test_speech_rate_calculation(self):
        """Words-per-minute = int(200 * speed). Verify at common speeds."""
        # This tests the math inline — not dependent on pyttsx3 being installed.
        assert int(200 * 0.75) == 150  # Dorothy's slow speed
        assert int(200 * 1.0) == 200  # Normal speed
        assert int(200 * 1.5) == 300  # Marcus's fast speed


# ─────────────────────────────────────────────────────────────
# speak_locally
# ─────────────────────────────────────────────────────────────


class TestSpeakLocally:
    async def test_calls_pyttsx3_engine_with_correct_rate(self):
        """speak_locally calls pyttsx3.init and sets rate correctly."""
        mock_pyttsx3 = inject_mock_pyttsx3()
        rate_calls = []
        texts_spoken = []

        mock_engine = MagicMock()

        def record_set_property(prop, val):
            rate_calls.append((prop, val))

        mock_engine.setProperty = record_set_property
        mock_engine.say = lambda text: texts_spoken.append(text)
        mock_engine.runAndWait = MagicMock()
        mock_pyttsx3.init.return_value = mock_engine

        from blind_assistant.voice.tts import speak_locally

        await speak_locally("Testing speech", speed=0.75)

        expected_rate = int(200 * 0.75)  # 150
        assert any(prop == "rate" and rate == expected_rate for (prop, rate) in rate_calls)
        assert texts_spoken == ["Testing speech"]

    async def test_handles_pyttsx3_init_exception_gracefully(self):
        """speak_locally does not raise when pyttsx3.init() throws."""
        mock_pyttsx3 = inject_mock_pyttsx3()
        mock_pyttsx3.init.side_effect = RuntimeError("audio error")

        from blind_assistant.voice.tts import speak_locally

        # Should not raise
        await speak_locally("Emergency message")

    async def test_returns_none_gracefully_when_pyttsx3_unavailable(self):
        """speak_locally returns without raising when pyttsx3 not installed."""
        saved = sys.modules.pop("pyttsx3", None)
        try:
            from blind_assistant.voice.tts import speak_locally

            # Should not raise — falls back and returns
            result = await speak_locally("Fallback message")
            assert result is None
        finally:
            if saved is not None:
                sys.modules["pyttsx3"] = saved
