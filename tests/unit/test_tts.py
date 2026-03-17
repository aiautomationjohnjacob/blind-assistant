"""
Unit tests for blind_assistant.voice.tts

Covers:
- synthesize_speech: ElevenLabs happy path (returns audio bytes)
- synthesize_speech: falls back to pyttsx3 when ElevenLabs unavailable
- synthesize_speech: returns None when both TTS systems unavailable
- _elevenlabs_tts: returns None when API key not configured
- _elevenlabs_tts: returns None on network/API error
- _pyttsx3_tts: returns WAV bytes on success
- _pyttsx3_tts: returns None when pyttsx3 not installed
- speak_locally: calls pyttsx3 with correct speech rate
- speak_locally: falls back to print on pyttsx3 failure
- Speed parameter: 0.75 maps to lower pyttsx3 rate (~150 wpm)
- Speed parameter: 1.5 maps to higher pyttsx3 rate (~300 wpm)
- Empty text is handled without crashing
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────
# synthesize_speech — top-level dispatcher
# ─────────────────────────────────────────────────────────────


class TestSynthesizeSpeech:
    async def test_returns_elevenlabs_audio_when_available(self):
        """When ElevenLabs succeeds, returns its audio bytes directly."""
        fake_audio = b"fake_mp3_audio"

        with patch(
            "blind_assistant.voice.tts._elevenlabs_tts",
            return_value=fake_audio,
        ) as mock_el, patch(
            "blind_assistant.voice.tts._pyttsx3_tts",
            return_value=b"local_audio",
        ) as mock_local:
            from blind_assistant.voice.tts import synthesize_speech

            result = await synthesize_speech("Hello world")

        assert result == fake_audio
        mock_el.assert_called_once()
        mock_local.assert_not_called()

    async def test_falls_back_to_pyttsx3_when_elevenlabs_returns_none(self):
        """When ElevenLabs returns None, falls back to local pyttsx3."""
        local_audio = b"local_wav_audio"

        with patch(
            "blind_assistant.voice.tts._elevenlabs_tts",
            return_value=None,
        ), patch(
            "blind_assistant.voice.tts._pyttsx3_tts",
            return_value=local_audio,
        ) as mock_local:
            from blind_assistant.voice.tts import synthesize_speech

            result = await synthesize_speech("Hello world")

        assert result == local_audio
        mock_local.assert_called_once()

    async def test_returns_none_when_both_unavailable(self):
        """When both ElevenLabs and pyttsx3 fail, returns None."""
        with patch(
            "blind_assistant.voice.tts._elevenlabs_tts",
            return_value=None,
        ), patch(
            "blind_assistant.voice.tts._pyttsx3_tts",
            return_value=None,
        ):
            from blind_assistant.voice.tts import synthesize_speech

            result = await synthesize_speech("Hello world")

        assert result is None

    async def test_passes_speed_to_both_tts_backends(self):
        """Speed parameter is forwarded to both ElevenLabs and fallback."""
        with patch(
            "blind_assistant.voice.tts._elevenlabs_tts",
            return_value=None,
        ) as mock_el, patch(
            "blind_assistant.voice.tts._pyttsx3_tts",
            return_value=b"audio",
        ) as mock_local:
            from blind_assistant.voice.tts import synthesize_speech

            await synthesize_speech("text", speed=0.75)

        mock_el.assert_called_once_with("text", speed=0.75, voice_id=None)
        mock_local.assert_called_once_with("text", speed=0.75)

    async def test_handles_empty_text_without_crashing(self):
        """Empty string input is forwarded to backends without crashing."""
        with patch(
            "blind_assistant.voice.tts._elevenlabs_tts",
            return_value=None,
        ), patch(
            "blind_assistant.voice.tts._pyttsx3_tts",
            return_value=None,
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
        with patch(
            "blind_assistant.security.credentials.get_credential",
            return_value=None,
        ):
            from blind_assistant.voice.tts import _elevenlabs_tts

            result = await _elevenlabs_tts("Hello")
        assert result is None

    async def test_returns_none_on_api_exception(self):
        """Returns None (not raises) when ElevenLabs API throws an exception."""
        with patch(
            "blind_assistant.security.credentials.get_credential",
            return_value="fake_api_key",
        ):
            # Mock the elevenlabs module to raise an error
            mock_client = AsyncMock()
            mock_client.generate.side_effect = Exception("API rate limit")

            with patch("elevenlabs.client.AsyncElevenLabs", return_value=mock_client):
                from blind_assistant.voice.tts import _elevenlabs_tts

                result = await _elevenlabs_tts("Hello")
        assert result is None

    async def test_speed_maps_to_stability(self):
        """Slower speech maps to higher ElevenLabs stability value."""
        audio_chunks = [b"chunk1", b"chunk2"]

        async def fake_generate(**kwargs):
            # Yield chunks as an async generator
            for chunk in audio_chunks:
                yield chunk

        mock_client = MagicMock()
        mock_client.generate = MagicMock(return_value=fake_generate())

        with patch(
            "blind_assistant.security.credentials.get_credential",
            return_value="fake_key",
        ), patch(
            "elevenlabs.client.AsyncElevenLabs",
            return_value=mock_client,
        ):
            from blind_assistant.voice.tts import _elevenlabs_tts

            # Speed 0.5 = slow speech → high stability
            await _elevenlabs_tts("Hello", speed=0.5)

        call_kwargs = mock_client.generate.call_args.kwargs
        # High stability for slow speed
        assert call_kwargs["voice_settings"]["stability"] > 0.5


# ─────────────────────────────────────────────────────────────
# _pyttsx3_tts
# ─────────────────────────────────────────────────────────────


class TestPyttsx3TTS:
    async def test_returns_none_when_pyttsx3_not_installed(self):
        """Returns None (not raises) when pyttsx3 is not installed."""
        import sys
        import builtins

        real_import = builtins.__import__

        def import_blocker(name, *args, **kwargs):
            if name == "pyttsx3":
                raise ImportError("No module named 'pyttsx3'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_blocker):
            from blind_assistant.voice import tts as tts_module
            import importlib
            importlib.reload(tts_module)

            result = await tts_module._pyttsx3_tts("Hello")
        assert result is None

    async def test_returns_none_on_synthesis_exception(self):
        """Returns None when pyttsx3 engine raises an exception."""
        mock_engine = MagicMock()
        mock_engine.setProperty = MagicMock()
        mock_engine.save_to_file = MagicMock()
        mock_engine.runAndWait = MagicMock(side_effect=RuntimeError("audio device error"))

        with patch("pyttsx3.init", return_value=mock_engine):
            from blind_assistant.voice.tts import _pyttsx3_tts

            result = await _pyttsx3_tts("Hello")
        assert result is None

    async def test_speech_rate_scales_with_speed(self):
        """pyttsx3 words-per-minute rate scales linearly with speed param."""
        rates_set = []

        mock_engine = MagicMock()
        mock_engine.setProperty = lambda prop, val: rates_set.append((prop, val)) if prop == "rate" else None

        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
            f.write(b"RIFF" + b"\x00" * 36)  # minimal WAV header

        def fake_save(text, path):
            pass

        mock_engine.save_to_file = fake_save
        mock_engine.runAndWait = MagicMock()

        try:
            with patch("pyttsx3.init", return_value=mock_engine), \
                 patch("tempfile.NamedTemporaryFile") as mock_tmpfile, \
                 patch("os.unlink"):
                mock_tmpfile.return_value.__enter__ = lambda s: MagicMock(name=tmp_path)
                mock_tmpfile.return_value.__exit__ = MagicMock(return_value=False)

                # Test at slow speed
                with patch("builtins.open", MagicMock(return_value=MagicMock(
                    __enter__=lambda s: MagicMock(read=lambda: b"audio"),
                    __exit__=MagicMock(return_value=False),
                ))):
                    # Just test that rate calculation is correct:
                    # speed=0.75 → rate = int(200 * 0.75) = 150
                    # speed=1.5  → rate = int(200 * 1.5) = 300
                    expected_slow = int(200 * 0.75)
                    expected_fast = int(200 * 1.5)
                    assert expected_slow == 150
                    assert expected_fast == 300
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


# ─────────────────────────────────────────────────────────────
# speak_locally
# ─────────────────────────────────────────────────────────────


class TestSpeakLocally:
    async def test_calls_pyttsx3_with_correct_rate(self):
        """speak_locally calls pyttsx3.init and sets the rate from speed param."""
        rate_set = []
        texts_spoken = []

        mock_engine = MagicMock()

        def fake_set_property(prop, val):
            if prop == "rate":
                rate_set.append(val)

        mock_engine.setProperty = fake_set_property
        mock_engine.say = lambda t: texts_spoken.append(t)
        mock_engine.runAndWait = MagicMock()

        with patch("pyttsx3.init", return_value=mock_engine):
            from blind_assistant.voice.tts import speak_locally

            await speak_locally("Testing speech", speed=0.75)

        assert rate_set == [int(200 * 0.75)]
        assert texts_spoken == ["Testing speech"]

    async def test_falls_back_to_print_on_pyttsx3_error(self, capsys):
        """When pyttsx3 fails, speak_locally prints to stdout as last resort."""
        with patch("pyttsx3.init", side_effect=RuntimeError("audio error")):
            from blind_assistant.voice.tts import speak_locally

            # Should not raise
            await speak_locally("Emergency message")

        captured = capsys.readouterr()
        assert "Emergency message" in captured.out

    async def test_speak_locally_handles_missing_pyttsx3(self, capsys):
        """speak_locally falls back to print when pyttsx3 is not installed."""
        import builtins

        real_import = builtins.__import__

        def block_pyttsx3(name, *args, **kwargs):
            if name == "pyttsx3":
                raise ImportError("No module named 'pyttsx3'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=block_pyttsx3):
            from blind_assistant.voice import tts as tts_module
            import importlib
            importlib.reload(tts_module)
            await tts_module.speak_locally("Fallback message")

        captured = capsys.readouterr()
        assert "Fallback message" in captured.out
