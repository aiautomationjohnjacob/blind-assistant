"""
Shared pytest fixtures for Blind Assistant test suite.

All external I/O is mocked here so unit tests run fast and offline.
Integration tests that need real I/O should import from this module
but override fixtures with `autouse=False`.

Fixture hierarchy:
  - mock_keyring          — OS keychain (keyring library)
  - mock_claude_client    — Anthropic Claude API
  - mock_telegram_bot     — python-telegram-bot
  - mock_elevenlabs       — ElevenLabs TTS API
  - mock_whisper          — OpenAI Whisper STT (local model)
  - temp_vault_dir        — temporary directory for vault files
  - suppress_audio        — prevents speaker/microphone access
"""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────
# EVENT LOOP (asyncio)
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.DefaultEventLoopPolicy:
    return asyncio.DefaultEventLoopPolicy()


# ─────────────────────────────────────────────────────────────
# OS KEYCHAIN
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_keyring() -> Generator[MagicMock, None, None]:
    """
    Replace OS keychain with an in-memory dict.
    Prevents tests from reading/writing real OS credentials.
    """
    store: dict[tuple[str, str], str] = {}

    def fake_set(service: str, key: str, value: str) -> None:
        store[(service, key)] = value

    def fake_get(service: str, key: str) -> str | None:
        return store.get((service, key))

    def fake_delete(service: str, key: str) -> None:
        if (service, key) not in store:
            import keyring.errors
            raise keyring.errors.PasswordDeleteError(key)
        del store[(service, key)]

    with patch("keyring.set_password", side_effect=fake_set), \
         patch("keyring.get_password", side_effect=fake_get), \
         patch("keyring.delete_password", side_effect=fake_delete):
        yield MagicMock(store=store)


# ─────────────────────────────────────────────────────────────
# CLAUDE API
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_claude_response() -> MagicMock:
    """A minimal fake Claude API message response."""
    msg = MagicMock()
    msg.content = [MagicMock(text="I can help you with that.")]
    msg.stop_reason = "end_turn"
    msg.usage.input_tokens = 10
    msg.usage.output_tokens = 8
    return msg


@pytest.fixture
def mock_claude_client(mock_claude_response: MagicMock) -> Generator[MagicMock, None, None]:
    """Mock the Anthropic client so no real API calls are made."""
    client = MagicMock()
    client.messages.create = MagicMock(return_value=mock_claude_response)
    client.messages.acreate = AsyncMock(return_value=mock_claude_response)

    with patch("anthropic.Anthropic", return_value=client), \
         patch("anthropic.AsyncAnthropic", return_value=client):
        yield client


# ─────────────────────────────────────────────────────────────
# TELEGRAM BOT
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_telegram_update() -> MagicMock:
    """Fake Telegram Update with a text message."""
    update = MagicMock()
    update.effective_user.id = 12345678
    update.effective_user.first_name = "TestUser"
    update.message.text = "Hello"
    update.message.voice = None
    update.message.reply_text = AsyncMock()
    update.message.reply_voice = AsyncMock()
    return update


@pytest.fixture
def mock_telegram_context() -> MagicMock:
    """Fake Telegram CallbackContext."""
    ctx = MagicMock()
    ctx.bot.send_message = AsyncMock()
    ctx.bot.send_voice = AsyncMock()
    return ctx


@pytest.fixture
def mock_telegram_application() -> Generator[MagicMock, None, None]:
    """Mock the full Telegram Application so no real bot token is needed."""
    app = MagicMock()
    app.run_polling = MagicMock()
    app.run_webhook = MagicMock()
    app.add_handler = MagicMock()

    with patch("telegram.ext.ApplicationBuilder") as builder_cls:
        builder = MagicMock()
        builder.token.return_value = builder
        builder.build.return_value = app
        builder_cls.return_value = builder
        yield app


# ─────────────────────────────────────────────────────────────
# TEXT-TO-SPEECH (ElevenLabs + pyttsx3)
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_elevenlabs() -> Generator[MagicMock, None, None]:
    """Mock ElevenLabs so no real audio is generated."""
    with patch("elevenlabs.generate", return_value=b"fake_audio_bytes"), \
         patch("elevenlabs.play"):
        yield


@pytest.fixture
def mock_pyttsx3() -> Generator[MagicMock, None, None]:
    """Mock pyttsx3 local TTS."""
    engine = MagicMock()
    engine.say = MagicMock()
    engine.runAndWait = MagicMock()
    engine.save_to_file = MagicMock()

    with patch("pyttsx3.init", return_value=engine):
        yield engine


# ─────────────────────────────────────────────────────────────
# SPEECH-TO-TEXT (Whisper)
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_whisper() -> Generator[MagicMock, None, None]:
    """Mock Whisper STT so no model download or GPU is needed in tests."""
    model = MagicMock()
    model.transcribe.return_value = {"text": "test transcription", "language": "en"}

    with patch("whisper.load_model", return_value=model):
        yield model


# ─────────────────────────────────────────────────────────────
# FILE SYSTEM
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def temp_vault_dir() -> Generator[Path, None, None]:
    """Temporary directory for Second Brain vault tests. Cleaned up after each test."""
    with tempfile.TemporaryDirectory(prefix="ba_vault_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """General-purpose temporary directory."""
    with tempfile.TemporaryDirectory(prefix="ba_test_") as tmpdir:
        yield Path(tmpdir)


# ─────────────────────────────────────────────────────────────
# AUDIO I/O (sounddevice)
# ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def suppress_audio() -> Generator[None, None, None]:
    """
    Auto-used: prevents any real microphone or speaker access during tests.
    Applied to ALL tests automatically — no test should produce sound.
    """
    with patch("sounddevice.rec", return_value=MagicMock()), \
         patch("sounddevice.play"), \
         patch("sounddevice.wait"):
        yield


# ─────────────────────────────────────────────────────────────
# SAMPLE DATA
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_user_id() -> int:
    return 12345678


@pytest.fixture
def sample_passphrase() -> str:
    return "correct-horse-battery-staple"  # NIST test passphrase


@pytest.fixture
def sample_note_content() -> str:
    return "Meeting with Dr. Smith on Thursday at 2pm. Prescription renewal needed."
