"""
Telegram Bot Interface — Secondary / Super-User Channel

Telegram is an OPTIONAL interface for power users who want remote access to the assistant
from another device (e.g. phone while away from desktop). It is NOT the primary interface.

Primary interfaces are the native standalone apps (Android, iOS, Desktop, Web) which
are voice-guided from first launch and require zero visual setup. Telegram requires
visual setup (QR scanning, phone verification) that blind users cannot complete
independently — so it is never the default, never required, and never the demo target.

This interface is disabled by default. Enable it by setting `telegram_enabled: true`
in config.yaml after manually completing Telegram setup.

Security: Only whitelisted Telegram user IDs can interact with the bot.
All others are silently ignored (do not acknowledge the bot's existence to strangers).

Accessibility requirements:
- All responses available as text (for braille display users)
- Voice messages are transcribed and processed
- Responses can be sent as both text and voice
- No emoji in responses unless user explicitly requests them
- Responses structured for 40-char braille display in braille_mode
"""

import io
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram.ext import Application

logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Telegram bot interface.
    Receives text and voice messages; responds with text and optionally voice.
    """

    def __init__(self, orchestrator, config: dict) -> None:
        self.orchestrator = orchestrator
        self.config = config
        self._app: "Application | None" = None
        self._allowed_user_ids: set[int] = set()

    async def _load_allowed_users(self) -> None:
        """Load whitelisted Telegram user IDs from OS keychain."""
        from blind_assistant.security.credentials import (
            TELEGRAM_ALLOWED_USER_IDS,
            get_credential,
        )

        raw = get_credential(TELEGRAM_ALLOWED_USER_IDS)
        if raw:
            ids = [int(uid.strip()) for uid in raw.split(",") if uid.strip().isdigit()]
            self._allowed_user_ids = set(ids)
            logger.info(f"Loaded {len(ids)} allowed Telegram user(s)")
        else:
            logger.warning(
                "No allowed Telegram user IDs configured. "
                "Bot will not respond to anyone. "
                "Run setup to configure: python installer/install.py --setup"
            )

    def _is_allowed(self, user_id: int) -> bool:
        """Check if a Telegram user ID is allowed to interact with the bot."""
        return user_id in self._allowed_user_ids

    async def start(self) -> None:
        """Start the Telegram bot and begin polling for messages."""
        from telegram.ext import (
            Application,
            MessageHandler,
            filters,
        )

        from blind_assistant.security.credentials import (
            TELEGRAM_BOT_TOKEN,
            require_credential,
        )

        await self._load_allowed_users()

        token = require_credential(TELEGRAM_BOT_TOKEN)
        self._app = Application.builder().token(token).build()

        # Handle text messages
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))

        # Handle voice messages
        self._app.add_handler(MessageHandler(filters.VOICE, self._handle_voice))

        logger.info("Telegram bot starting...")
        await self._app.run_polling()

    async def _get_user_context(self, user_id: int, chat_id: int):
        """Get or create context for a Telegram user."""
        return await self.orchestrator.context_manager.load_user_context(
            user_id=str(user_id),
            session_id=f"telegram_{user_id}_{chat_id}",
        )

    async def _handle_text(self, update, context) -> None:
        """Handle an incoming text message."""
        user_id = update.effective_user.id

        # Security: silently drop messages from non-whitelisted users
        if not self._is_allowed(user_id):
            logger.debug(f"Ignored message from non-whitelisted user {user_id}")
            return

        # Check if this is a confirmation response to a pending action
        self.orchestrator.confirmation_gate.submit_response(
            session_id=f"telegram_{user_id}_{update.effective_chat.id}",
            response=update.message.text,
        )

        # Also process as a new message if not mid-confirmation
        user_context = await self._get_user_context(user_id, update.effective_chat.id)

        async def send_update(message: str) -> None:
            """Send an interim update to the user."""
            await update.message.reply_text(message)

        response = await self.orchestrator.handle_message(
            text=update.message.text,
            context=user_context,
            response_callback=send_update,
        )

        await self._send_response(update, response, user_context)

    async def _handle_voice(self, update, context) -> None:
        """
        Handle an incoming voice message.
        Transcribes audio via Whisper, then processes as text.
        """
        user_id = update.effective_user.id

        if not self._is_allowed(user_id):
            return

        user_context = await self._get_user_context(user_id, update.effective_chat.id)

        # Send acknowledgment immediately so user knows we received it
        await update.message.reply_text("Listening...")

        try:
            # Download and transcribe the voice message
            voice_file = await context.bot.get_file(update.message.voice.file_id)
            audio_bytes = await voice_file.download_as_bytearray()

            from blind_assistant.voice.stt import transcribe_audio

            transcript = await transcribe_audio(bytes(audio_bytes))

            if not transcript:
                await update.message.reply_text("I couldn't make out what you said. Could you try again?")
                return

            logger.info(f"Transcribed: {transcript[:60]}...")

            # Process the transcribed text
            async def send_update(message: str) -> None:
                await update.message.reply_text(message)

            response = await self.orchestrator.handle_message(
                text=transcript,
                context=user_context,
                response_callback=send_update,
            )

            await self._send_response(update, response, user_context)

        except Exception as e:
            logger.error(f"Voice message handling failed: {e}", exc_info=True)
            await update.message.reply_text(
                "I had trouble processing your voice message. You can also type your message if that's easier."
            )

    async def _send_response(self, update, response, user_context) -> None:
        """
        Send a response to the user.
        Always sends text. Optionally also sends voice.
        """
        # Always send text (required for braille display users)
        await update.message.reply_text(response.text)

        # Optionally send voice (if user hasn't disabled it)
        if user_context.output_mode != "text_only":
            try:
                from blind_assistant.voice.tts import synthesize_speech

                spoken = response.spoken_text or response.text
                audio_bytes = await synthesize_speech(
                    text=spoken,
                    speed=user_context.speech_rate,
                )
                if audio_bytes:
                    await update.message.reply_voice(voice=io.BytesIO(audio_bytes))
            except Exception as e:
                # TTS failure is not fatal — text was already sent
                logger.warning(f"TTS failed, text-only response sent: {e}")
