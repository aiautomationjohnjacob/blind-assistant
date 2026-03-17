"""
Unit tests for TelegramBot — interfaces/telegram_bot.py

Tests cover:
- User allowlist loading and enforcement (whitelist)
- _is_allowed checks (positive and negative)
- _handle_text: non-whitelisted user silently dropped
- _handle_text: whitelisted user message routed through orchestrator
- _handle_voice: non-whitelisted user silently dropped
- _handle_voice: transcription failure handled gracefully
- _handle_voice: successful voice message routed through orchestrator
- _send_response: always sends text; sends voice when not text_only mode
- _send_response: TTS failure non-fatal (text still sent)
- start(): loads users, builds app, calls run_polling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.interfaces.telegram_bot import TelegramBot


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _make_bot(allowed_ids: list[int] | None = None) -> TelegramBot:
    """Build a TelegramBot with a mock orchestrator and config."""
    orchestrator = MagicMock()
    orchestrator.confirmation_gate = MagicMock()
    orchestrator.confirmation_gate.submit_response = MagicMock()
    orchestrator.context_manager = MagicMock()
    orchestrator.context_manager.load_user_context = AsyncMock(return_value=_make_user_context())
    orchestrator.handle_message = AsyncMock(return_value=_make_response("Here is your answer."))

    bot = TelegramBot(orchestrator=orchestrator, config={})
    if allowed_ids is not None:
        bot._allowed_user_ids = set(allowed_ids)
    return bot


def _make_user_context(braille_mode: bool = False, output_mode: str = "voice") -> MagicMock:
    ctx = MagicMock()
    ctx.braille_mode = braille_mode
    ctx.output_mode = output_mode
    ctx.speech_rate = 1.0
    return ctx


def _make_response(text: str, spoken_text: str | None = None) -> MagicMock:
    r = MagicMock()
    r.text = text
    r.spoken_text = spoken_text
    return r


def _make_update(user_id: int = 12345, text: str = "Hello", chat_id: int = 99) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat.id = chat_id
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.message.reply_voice = AsyncMock()
    update.message.voice = None
    return update


def _make_voice_update(user_id: int = 12345, file_id: str = "file_abc", chat_id: int = 99) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_chat.id = chat_id
    update.message.voice.file_id = file_id
    update.message.reply_text = AsyncMock()
    update.message.reply_voice = AsyncMock()
    return update


def _make_tg_context(audio_bytes: bytes = b"fake_ogg") -> MagicMock:
    """Fake python-telegram-bot CallbackContext."""
    ctx = MagicMock()
    voice_file = MagicMock()
    voice_file.download_as_bytearray = AsyncMock(return_value=bytearray(audio_bytes))
    ctx.bot.get_file = AsyncMock(return_value=voice_file)
    return ctx


# ─────────────────────────────────────────────────────────────
# _is_allowed
# ─────────────────────────────────────────────────────────────


def test_is_allowed_returns_true_for_whitelisted_user():
    bot = _make_bot(allowed_ids=[111, 222])
    assert bot._is_allowed(111) is True


def test_is_allowed_returns_true_for_second_allowed_user():
    bot = _make_bot(allowed_ids=[111, 222])
    assert bot._is_allowed(222) is True


def test_is_allowed_returns_false_for_unknown_user():
    bot = _make_bot(allowed_ids=[111])
    assert bot._is_allowed(999) is False


def test_is_allowed_returns_false_when_allowlist_empty():
    bot = _make_bot(allowed_ids=[])
    assert bot._is_allowed(12345) is False


# ─────────────────────────────────────────────────────────────
# _load_allowed_users
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_load_allowed_users_parses_comma_separated_ids():
    bot = _make_bot()
    with patch("blind_assistant.security.credentials.get_credential", return_value="111, 222, 333"):
        await bot._load_allowed_users()
    assert bot._allowed_user_ids == {111, 222, 333}


@pytest.mark.asyncio
async def test_load_allowed_users_ignores_non_digit_entries():
    bot = _make_bot()
    with patch("blind_assistant.security.credentials.get_credential", return_value="111, abc, 222"):
        await bot._load_allowed_users()
    assert bot._allowed_user_ids == {111, 222}


@pytest.mark.asyncio
async def test_load_allowed_users_empty_when_no_credential():
    bot = _make_bot()
    with patch("blind_assistant.security.credentials.get_credential", return_value=None):
        await bot._load_allowed_users()
    assert bot._allowed_user_ids == set()


# ─────────────────────────────────────────────────────────────
# _handle_text
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_text_drops_non_whitelisted_user_silently():
    bot = _make_bot(allowed_ids=[111])
    update = _make_update(user_id=999)
    ctx = MagicMock()

    await bot._handle_text(update, ctx)

    # No reply sent to stranger
    update.message.reply_text.assert_not_called()
    # Orchestrator never invoked
    bot.orchestrator.handle_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_text_routes_whitelisted_user_to_orchestrator():
    bot = _make_bot(allowed_ids=[12345])
    update = _make_update(user_id=12345, text="what's on my screen?")
    ctx = MagicMock()

    await bot._handle_text(update, ctx)

    bot.orchestrator.handle_message.assert_awaited_once()
    call_kwargs = bot.orchestrator.handle_message.call_args.kwargs
    assert call_kwargs["text"] == "what's on my screen?"


@pytest.mark.asyncio
async def test_handle_text_submits_to_confirmation_gate():
    """Text messages are forwarded to the confirmation gate for pending actions."""
    bot = _make_bot(allowed_ids=[12345])
    update = _make_update(user_id=12345, text="yes")
    ctx = MagicMock()

    await bot._handle_text(update, ctx)

    bot.orchestrator.confirmation_gate.submit_response.assert_called_once()


@pytest.mark.asyncio
async def test_handle_text_sends_reply_after_orchestrator():
    bot = _make_bot(allowed_ids=[12345])
    bot.orchestrator.handle_message = AsyncMock(return_value=_make_response("Got it."))
    update = _make_update(user_id=12345, text="remind me")
    ctx = MagicMock()

    await bot._handle_text(update, ctx)

    # reply_text called at least once (the final response)
    assert update.message.reply_text.call_count >= 1


# ─────────────────────────────────────────────────────────────
# _handle_voice
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_voice_drops_non_whitelisted_user():
    bot = _make_bot(allowed_ids=[111])
    update = _make_voice_update(user_id=999)
    ctx = _make_tg_context()

    await bot._handle_voice(update, ctx)

    update.message.reply_text.assert_not_called()
    bot.orchestrator.handle_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_voice_sends_listening_acknowledgment_first():
    bot = _make_bot(allowed_ids=[12345])
    update = _make_voice_update(user_id=12345)
    ctx = _make_tg_context()

    with patch("blind_assistant.voice.stt.transcribe_audio", new_callable=AsyncMock, return_value="order me food"):
        await bot._handle_voice(update, ctx)

    # First call should be "Listening..."
    first_call = update.message.reply_text.call_args_list[0]
    assert "listening" in first_call.args[0].lower() or "Listening" in first_call.args[0]


@pytest.mark.asyncio
async def test_handle_voice_routes_transcription_to_orchestrator():
    bot = _make_bot(allowed_ids=[12345])
    update = _make_voice_update(user_id=12345)
    ctx = _make_tg_context()

    with patch("blind_assistant.voice.stt.transcribe_audio", new_callable=AsyncMock, return_value="what time is it"):
        await bot._handle_voice(update, ctx)

    bot.orchestrator.handle_message.assert_awaited_once()
    call_kwargs = bot.orchestrator.handle_message.call_args.kwargs
    assert call_kwargs["text"] == "what time is it"


@pytest.mark.asyncio
async def test_handle_voice_returns_error_when_transcript_empty():
    bot = _make_bot(allowed_ids=[12345])
    update = _make_voice_update(user_id=12345)
    ctx = _make_tg_context()

    with patch("blind_assistant.voice.stt.transcribe_audio", new_callable=AsyncMock, return_value=""):
        await bot._handle_voice(update, ctx)

    # Should tell user we couldn't hear them
    texts_sent = [call.args[0] for call in update.message.reply_text.call_args_list]
    assert any("couldn't" in t.lower() or "try again" in t.lower() for t in texts_sent)
    bot.orchestrator.handle_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_voice_handles_download_exception_gracefully():
    bot = _make_bot(allowed_ids=[12345])
    update = _make_voice_update(user_id=12345)
    ctx = MagicMock()
    ctx.bot.get_file = AsyncMock(side_effect=RuntimeError("download failed"))

    await bot._handle_voice(update, ctx)

    # Should send an error message, not crash
    texts_sent = [call.args[0] for call in update.message.reply_text.call_args_list]
    assert any("trouble" in t.lower() or "problem" in t.lower() or "type" in t.lower() for t in texts_sent)


# ─────────────────────────────────────────────────────────────
# _send_response
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_response_always_sends_text():
    bot = _make_bot()
    update = _make_update()
    user_context = _make_user_context(output_mode="voice")
    response = _make_response("Here is your answer.")

    with patch("blind_assistant.voice.tts.synthesize_speech", new_callable=AsyncMock, return_value=b"audio"):
        await bot._send_response(update, response, user_context)

    update.message.reply_text.assert_awaited_once_with("Here is your answer.")


@pytest.mark.asyncio
async def test_send_response_sends_voice_in_voice_mode():
    bot = _make_bot()
    update = _make_update()
    user_context = _make_user_context(output_mode="voice")
    response = _make_response("Hello.", spoken_text=None)

    with patch("blind_assistant.voice.tts.synthesize_speech", new_callable=AsyncMock, return_value=b"fake_audio"):
        await bot._send_response(update, response, user_context)

    update.message.reply_voice.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_response_uses_spoken_text_for_tts_when_provided():
    """spoken_text takes precedence over text for TTS."""
    bot = _make_bot()
    update = _make_update()
    user_context = _make_user_context(output_mode="voice")
    response = _make_response(text="Short display text.", spoken_text="Expanded spoken version.")

    captured = {}

    async def fake_tts(text, speed):
        captured["text"] = text
        return b"audio"

    with patch("blind_assistant.voice.tts.synthesize_speech", side_effect=fake_tts):
        await bot._send_response(update, response, user_context)

    assert captured["text"] == "Expanded spoken version."


@pytest.mark.asyncio
async def test_send_response_skips_voice_in_text_only_mode():
    bot = _make_bot()
    update = _make_update()
    user_context = _make_user_context(output_mode="text_only")
    response = _make_response("Text response.")

    with patch("blind_assistant.voice.tts.synthesize_speech", new_callable=AsyncMock) as mock_tts:
        await bot._send_response(update, response, user_context)

    mock_tts.assert_not_called()
    update.message.reply_voice.assert_not_called()
    update.message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_response_tts_failure_is_non_fatal():
    """TTS exception must not prevent text response from being sent."""
    bot = _make_bot()
    update = _make_update()
    user_context = _make_user_context(output_mode="voice")
    response = _make_response("Still got this.")

    with patch("blind_assistant.voice.tts.synthesize_speech", new_callable=AsyncMock, side_effect=RuntimeError("TTS down")):
        await bot._send_response(update, response, user_context)

    # Text was still sent
    update.message.reply_text.assert_awaited_once_with("Still got this.")
    # No voice reply attempted
    update.message.reply_voice.assert_not_called()


@pytest.mark.asyncio
async def test_send_response_no_voice_when_tts_returns_none():
    """If synthesize_speech returns None, no voice message is sent."""
    bot = _make_bot()
    update = _make_update()
    user_context = _make_user_context(output_mode="voice")
    response = _make_response("OK.")

    with patch("blind_assistant.voice.tts.synthesize_speech", new_callable=AsyncMock, return_value=None):
        await bot._send_response(update, response, user_context)

    update.message.reply_voice.assert_not_called()


# ─────────────────────────────────────────────────────────────
# start()
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_loads_users_before_polling(mock_keyring, mock_telegram_application):
    """start() must load allowed users from keychain before beginning to poll."""
    bot = _make_bot()

    with (
        patch("blind_assistant.security.credentials.get_credential", return_value="12345"),
        patch("blind_assistant.security.credentials.require_credential", return_value="fake_token"),
    ):
        await bot.start()

    # allowed users should be populated
    assert 12345 in bot._allowed_user_ids


@pytest.mark.asyncio
async def test_start_calls_run_polling(mock_keyring, mock_telegram_application):
    """start() calls run_polling() on the Application."""
    bot = _make_bot()

    with (
        patch("blind_assistant.security.credentials.get_credential", return_value="111"),
        patch("blind_assistant.security.credentials.require_credential", return_value="fake_token"),
    ):
        await bot.start()

    mock_telegram_application.run_polling.assert_called_once()
