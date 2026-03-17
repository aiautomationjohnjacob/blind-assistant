"""
Unit tests for blind_assistant.voice.stt

Covers:
- transcribe_audio: returns text on successful transcription
- transcribe_audio: returns None when model returns empty string
- transcribe_audio: returns None on exception (file write failure, model crash)
- transcribe_audio: temp file is always cleaned up even on failure
- _load_model: loads Whisper model only once (singleton pattern)
- transcribe_microphone: returns None when sounddevice not installed
- transcribe_microphone: calls transcribe_audio with recorded bytes
- transcribe_microphone: returns None on recording failure

Privacy note: all transcription is local; no audio bytes leave device.
This file tests the boundary — mock Whisper to avoid actual model loading.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────
# transcribe_audio
# ─────────────────────────────────────────────────────────────


class TestTranscribeAudio:
    async def test_returns_transcript_on_success(self):
        """Returns transcript text when Whisper model succeeds."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "  Hello, I need help with reading.  "}

        with patch(
            "blind_assistant.voice.stt._load_model",
            return_value=mock_model,
        ):
            from blind_assistant.voice.stt import transcribe_audio

            result = await transcribe_audio(b"fake_audio_bytes")

        assert result == "Hello, I need help with reading."

    async def test_returns_none_for_empty_transcript(self):
        """Returns None when model returns empty/whitespace-only text."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "   "}

        with patch("blind_assistant.voice.stt._load_model", return_value=mock_model):
            from blind_assistant.voice.stt import transcribe_audio

            result = await transcribe_audio(b"silence_audio")

        assert result is None

    async def test_returns_none_on_model_exception(self):
        """Returns None (not raises) when the model throws during transcription."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("CUDA out of memory")

        with patch("blind_assistant.voice.stt._load_model", return_value=mock_model):
            from blind_assistant.voice.stt import transcribe_audio

            result = await transcribe_audio(b"audio_bytes")

        assert result is None

    async def test_temp_file_cleaned_up_on_success(self, tmp_path):
        """Temp audio file is deleted after successful transcription."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "hello"}

        deleted_files = []

        real_unlink = __import__("os").unlink

        def tracking_unlink(path):
            deleted_files.append(path)
            real_unlink(path)

        with patch("blind_assistant.voice.stt._load_model", return_value=mock_model), \
             patch("os.unlink", side_effect=tracking_unlink):
            from blind_assistant.voice.stt import transcribe_audio

            await transcribe_audio(b"audio_data")

        assert len(deleted_files) == 1

    async def test_temp_file_cleaned_up_on_model_failure(self):
        """Temp audio file is deleted even when model throws an exception."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("model crash")

        deleted_files = []

        real_unlink = __import__("os").unlink

        def tracking_unlink(path):
            deleted_files.append(path)
            try:
                real_unlink(path)
            except FileNotFoundError:
                pass

        with patch("blind_assistant.voice.stt._load_model", return_value=mock_model), \
             patch("os.unlink", side_effect=tracking_unlink):
            from blind_assistant.voice.stt import transcribe_audio

            await transcribe_audio(b"audio_data")

        # File should have been deleted despite model failure
        assert len(deleted_files) == 1

    async def test_passes_language_hint_to_model(self):
        """language parameter is forwarded to model.transcribe()."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "Bonjour"}

        with patch("blind_assistant.voice.stt._load_model", return_value=mock_model):
            from blind_assistant.voice.stt import transcribe_audio

            await transcribe_audio(b"audio_bytes", language="fr")

        call_kwargs = mock_model.transcribe.call_args.kwargs
        assert call_kwargs.get("language") == "fr"

    async def test_fp16_false_for_cpu_safety(self):
        """fp16=False is always set to ensure CPU compatibility."""
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "test"}

        with patch("blind_assistant.voice.stt._load_model", return_value=mock_model):
            from blind_assistant.voice.stt import transcribe_audio

            await transcribe_audio(b"audio_bytes")

        call_kwargs = mock_model.transcribe.call_args.kwargs
        assert call_kwargs.get("fp16") is False


# ─────────────────────────────────────────────────────────────
# _load_model — singleton
# ─────────────────────────────────────────────────────────────


class TestLoadModel:
    async def test_model_loaded_only_once_across_multiple_calls(self):
        """Whisper model is a singleton — loaded only once regardless of call count."""
        import blind_assistant.voice.stt as stt_module

        # Reset the module-level singleton
        original = stt_module._whisper_model
        stt_module._whisper_model = None

        try:
            mock_model = MagicMock()
            load_call_count = [0]

            def fake_load_sync(model_name):
                load_call_count[0] += 1
                return mock_model

            with patch.object(stt_module, "_load_whisper_sync", side_effect=fake_load_sync):
                await stt_module._load_model()
                await stt_module._load_model()
                await stt_module._load_model()

            # Should only load once despite three calls
            assert load_call_count[0] == 1
        finally:
            stt_module._whisper_model = original


# ─────────────────────────────────────────────────────────────
# transcribe_microphone
# ─────────────────────────────────────────────────────────────


class TestTranscribeMicrophone:
    async def test_returns_none_when_sounddevice_not_installed(self):
        """Returns None (not raises) when sounddevice is not installed."""
        import builtins
        real_import = builtins.__import__

        def block_sounddevice(name, *args, **kwargs):
            if name == "sounddevice":
                raise ImportError("No module named 'sounddevice'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=block_sounddevice):
            from blind_assistant.voice import stt as stt_module
            import importlib
            importlib.reload(stt_module)

            result = await stt_module.transcribe_microphone(duration_seconds=1.0)

        assert result is None

    async def test_returns_none_on_recording_exception(self):
        """Returns None when sounddevice raises during recording."""
        mock_sd = MagicMock()
        mock_sd.rec.side_effect = Exception("No audio device available")

        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            from blind_assistant.voice.stt import transcribe_microphone

            result = await transcribe_microphone(duration_seconds=1.0)

        assert result is None

    async def test_calls_transcribe_audio_with_wav_bytes(self):
        """transcribe_microphone passes WAV bytes to transcribe_audio."""
        import numpy as np

        mock_sd = MagicMock()
        fake_audio = np.zeros((16000, 1), dtype="int16")
        mock_sd.rec.return_value = fake_audio
        mock_sd.wait = MagicMock()

        transcribed_bytes = []

        async def mock_transcribe(audio_bytes, language=None):
            transcribed_bytes.append(audio_bytes)
            return "test transcript"

        with patch.dict("sys.modules", {"sounddevice": mock_sd}), \
             patch("blind_assistant.voice.stt.transcribe_audio", side_effect=mock_transcribe):
            from blind_assistant.voice.stt import transcribe_microphone

            result = await transcribe_microphone(duration_seconds=1.0)

        assert result == "test transcript"
        assert len(transcribed_bytes) == 1
        # Should be WAV bytes (starts with RIFF header)
        assert transcribed_bytes[0][:4] == b"RIFF"
