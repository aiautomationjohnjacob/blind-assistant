"""
Core Orchestrator

The main loop: receive user input → classify intent → select tools → confirm →
execute → respond.

This is the central coordinator for all user interactions.
"""

import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class UserContext:
    """Everything the orchestrator knows about the current user and session."""
    user_id: str
    session_id: str
    verbosity: str = "standard"       # "brief" | "standard" | "detailed"
    speech_rate: float = 1.0          # 1.0 = normal; 0.7 = slower (Dorothy)
    output_mode: str = "voice_text"   # "voice_text" | "text_only" (Jordan)
    braille_mode: bool = False        # True = format for 40-char braille display
    preferences: dict = field(default_factory=dict)
    conversation_history: list = field(default_factory=list)


@dataclass
class Response:
    """The orchestrator's response to a user message."""
    text: str                          # Always present (for braille display)
    spoken_text: str | None = None  # If different from text (e.g., shorter)
    follow_up_prompt: str | None = None  # What to ask the user next
    requires_confirmation: bool = False
    confirmation_action: str | None = None


class Orchestrator:
    """
    Central coordinator for all user interactions.

    Responsibilities:
    - Intent classification via Claude API
    - Tool selection and self-expanding capability
    - Confirmation gate for high-stakes actions
    - Context management (Second Brain, memory, preferences)
    - Response formatting for different output modes
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        self._initialized = False

        # These are set during initialize()
        self.planner = None
        self.tool_registry = None
        self.confirmation_gate = None
        self.context_manager = None

    async def initialize(self) -> None:
        """Initialize all sub-components. Call once at startup."""
        logger.info("Initializing orchestrator...")

        # Import here to avoid circular imports
        from blind_assistant.core.confirmation import ConfirmationGate
        from blind_assistant.core.context import ContextManager
        from blind_assistant.core.planner import Planner
        from blind_assistant.tools.registry import ToolRegistry

        self.planner = Planner(self.config)
        self.tool_registry = ToolRegistry()
        self.confirmation_gate = ConfirmationGate()
        self.context_manager = ContextManager(self.config)

        await self.context_manager.initialize()
        await self.tool_registry.load()

        self._initialized = True
        logger.info("Orchestrator ready.")

    async def handle_message(
        self,
        text: str,
        context: UserContext,
        response_callback=None,
    ) -> Response:
        """
        Handle a user message end-to-end.

        Args:
            text: The user's message (already transcribed from voice if needed)
            context: Current user context
            response_callback: Optional async callable for streaming interim updates
                               Signature: async (message: str) -> None

        Returns:
            Final response to send to the user
        """
        if not self._initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

        # Progress callback helper
        async def update(message: str) -> None:
            if response_callback:
                await response_callback(message)

        logger.info(f"Handling message from {context.user_id}: {text[:50]}...")

        try:
            # 1. Classify intent
            await update("Let me think about that...")
            intent = await self.planner.classify_intent(text, context)
            logger.debug(f"Intent: {intent.type} | Tools needed: {intent.required_tools}")

            # 2. Check if any needed tools need to be installed
            for tool_name in intent.required_tools:
                if not self.tool_registry.is_installed(tool_name):
                    tool_info = self.tool_registry.get_available_tool(tool_name)
                    if tool_info:
                        installed = await self._offer_tool_install(
                            tool_name, tool_info, context, update
                        )
                        if not installed:
                            return Response(
                                text=f"Okay, I won't install {tool_name}. "
                                     "Let me know if there's another way I can help."
                            )

            # 3. Execute the intent
            result = await self._execute_intent(intent, context, update)

            # 4. Format response for user's output mode
            return self._format_response(result, context)

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return Response(
                text=(
                    "I ran into a problem and couldn't complete that. "
                    f"Here's what happened: {str(e)}. "
                    "Would you like to try again or do something different?"
                )
            )

    async def _offer_tool_install(
        self,
        tool_name: str,
        tool_info: dict,
        context: UserContext,
        update,
    ) -> bool:
        """
        Offer to install a missing tool. Returns True if installed, False if declined.

        Per ETHICS_REQUIREMENTS.md: always tell the user what's being installed and why.
        Per SECURITY_MODEL.md: only install from curated registry.
        """
        from blind_assistant.security.disclosure import INSTALL_CONSENT_TEMPLATE

        message = INSTALL_CONSENT_TEMPLATE.format(
            task_description=tool_info.get("task_description", "complete this task"),
            package_name=tool_name,
            package_description=tool_info.get("description", "a helper tool"),
        )

        await update(message)

        confirmed = await self.confirmation_gate.wait_for_confirmation(context)
        if confirmed:
            await update(f"Installing {tool_name}...")
            success = await self.tool_registry.install_tool(tool_name, tool_info)
            if success:
                await update(f"{tool_name} is now ready.")
                return True
            await update(
                f"I wasn't able to install {tool_name}. "
                "Let me try a different approach."
            )
            return False
        return False

    async def _execute_intent(self, intent, context: UserContext, update) -> dict:
        """
        Execute a classified intent using the appropriate tools.

        Routes to the correct handler based on intent type.
        """
        handler = self._intent_handlers.get(intent.type)
        if handler:
            return await handler(intent, context, update)

        # Unknown intent — try to answer as a general question
        return await self._handle_general_question(intent, context, update)

    async def _handle_screen_description(self, intent, context: UserContext, update) -> dict:
        """Capture and describe the current screen."""
        await update("Taking a look at your screen...")
        from blind_assistant.vision.screen_observer import ScreenObserver
        observer = ScreenObserver(self.config)
        description = await observer.describe_screen()
        return {"text": description}

    async def _handle_add_note(self, intent, context: UserContext, update) -> dict:
        """Add a note to the Second Brain vault."""
        await update("Saving that to your notes...")
        vault = await self._get_vault(context, response_callback=update)
        if vault is None:
            return {
                "text": (
                    "I couldn't access your notes vault. "
                    "Say 'unlock my notes' and provide your passphrase to try again."
                )
            }
        from blind_assistant.second_brain.query import VaultQuery
        q = VaultQuery(vault)
        # The note content is in the intent parameters or the raw description
        content = intent.parameters.get("content") or intent.description
        response_text = await q.add_note_from_voice(content=content, context=context)
        return {"text": response_text}

    async def _handle_query_note(self, intent, context: UserContext, update) -> dict:
        """Query the Second Brain vault for matching notes."""
        await update("Searching your notes...")
        vault = await self._get_vault(context, response_callback=update)
        if vault is None:
            return {
                "text": (
                    "I couldn't access your notes vault. "
                    "Say 'unlock my notes' and provide your passphrase to try again."
                )
            }
        from blind_assistant.second_brain.query import VaultQuery
        q = VaultQuery(vault)
        query_text = intent.parameters.get("query") or intent.description
        response_text = await q.answer_query(query=query_text, context=context)
        return {"text": response_text}

    async def _handle_general_question(self, intent, context: UserContext, update) -> dict:
        """Answer a general question using Claude."""
        await update("Let me think about that...")
        try:
            import anthropic

            from blind_assistant.security.credentials import CLAUDE_API_KEY, require_credential
            api_key = require_credential(CLAUDE_API_KEY)
            client = anthropic.AsyncAnthropic(api_key=api_key)

            system_prompt = (
                "You are Blind Assistant, a helpful AI companion for blind and visually "
                "impaired users. Give clear, concise answers. Avoid visual descriptions "
                "unless explaining something to the user. No emoji."
            )

            response = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=400,
                system=system_prompt,
                messages=[{"role": "user", "content": intent.description}],
            )
            return {"text": response.content[0].text}
        except Exception as e:
            logger.error(f"General question failed: {e}", exc_info=True)
            return {
                "text": (
                    "I wasn't able to answer that right now. "
                    f"Error: {str(e)}"
                )
            }

    async def _handle_high_stakes_stub(self, intent, context: UserContext, update) -> dict:
        """Placeholder for high-stakes intents not yet fully implemented."""
        return {
            "text": (
                f"I understand you want to {intent.description}. "
                "This feature is coming soon. "
                "I'll need to walk you through it step by step when it's ready."
            )
        }

    async def _get_vault(self, context: UserContext, response_callback=None):
        """
        Get or initialize the vault for this user.

        Tries OS keychain first. If keychain has no key, prompts the user for their
        passphrase via the active interface (voice or Telegram).

        Returns None only if the user cannot or does not provide a passphrase, or if
        the passphrase is wrong. Always tells the user what is happening — never silent.

        Per ISSUE-001: silent vault failure left blind users unable to access notes with
        no explanation. This fix speaks a passphrase prompt so they can self-recover.
        """
        import os
        from pathlib import Path

        from blind_assistant.second_brain.encryption import VaultKey
        from blind_assistant.second_brain.vault import EncryptedVault

        vault_path = Path(
            self.config.get("vault_path", os.path.expanduser("~/.blind-assistant/vault"))
        )

        key = VaultKey()

        # Try OS keychain first (no user interaction needed)
        if key.unlock_from_keychain():
            vault = EncryptedVault(vault_path=vault_path, vault_key=key)
            await vault.initialize()
            return vault

        # Keychain has no key — prompt the user for their passphrase
        logger.warning("Vault key not in keychain — prompting user for passphrase")

        if response_callback is None:
            # No interface available to ask the user — log but cannot self-recover
            logger.error(
                "Cannot unlock vault: keychain has no key and no response_callback "
                "available to prompt user for passphrase."
            )
            return None

        # Check if passphrase was collected earlier in this session
        session_passphrase: str | None = getattr(context, "_vault_passphrase", None)

        if session_passphrase is None:
            # Register the response queue BEFORE sending the prompt so that if the
            # user responds instantly (e.g. automated tests), the response is captured.
            self.confirmation_gate.register_session(context.session_id)
            await response_callback(
                "To access your notes, I need your vault passphrase. "
                "Please say or type your passphrase now. "
                "Your passphrase will not be stored — it only unlocks your notes for this session."
            )
            session_passphrase = await self._collect_vault_passphrase(context)

            if session_passphrase is None:
                await response_callback(
                    "I did not receive a passphrase. Your notes remain locked. "
                    "Say 'unlock my notes' any time to try again."
                )
                return None

            # Cache in context so we don't prompt again during the same session
            context._vault_passphrase = session_passphrase  # type: ignore[attr-defined]

        # Derive vault key from passphrase + stored salt
        salt_path = vault_path / ".salt"
        if not salt_path.exists():
            # First time: create vault directory and generate salt
            vault_path.mkdir(parents=True, exist_ok=True)
            from blind_assistant.second_brain.encryption import generate_salt
            salt = generate_salt()
            salt_path.write_bytes(salt)
            logger.info("New vault initialised: generated and stored salt.")
        else:
            salt = salt_path.read_bytes()

        try:
            key.unlock(session_passphrase, salt)
        except Exception as e:
            logger.error(f"Vault key derivation failed: {e}")
            await response_callback(
                "I could not unlock your notes with that passphrase. "
                "Please check your passphrase and say 'unlock my notes' to try again."
            )
            # Clear the cached wrong passphrase so next attempt can re-prompt
            if hasattr(context, "_vault_passphrase"):
                del context._vault_passphrase  # type: ignore[attr-defined]
            return None

        vault = EncryptedVault(vault_path=vault_path, vault_key=key)
        await vault.initialize()

        # Let the user know notes are unlocked, and offer to remember for next session
        await response_callback(
            "Notes unlocked. "
            "Say 'remember my passphrase' to store it securely so you "
            "don't need to enter it next time."
        )
        return vault

    async def _collect_vault_passphrase(self, context: UserContext) -> str | None:
        """
        Wait for the user to provide their vault passphrase.

        Reuses the confirmation gate's response queue so Telegram messages and
        local voice input are both routed here automatically.
        Returns None on timeout (120 seconds).
        """
        self.confirmation_gate.register_session(context.session_id)
        queue = self.confirmation_gate._response_queues[context.session_id]
        try:
            response = await asyncio.wait_for(queue.get(), timeout=120)
            return response.strip() if response and response.strip() else None
        except asyncio.TimeoutError:
            logger.info("Vault passphrase prompt timed out after 120 seconds")
            return None

    @property
    def _intent_handlers(self) -> dict:
        """Map of intent type → handler method."""
        return {
            "screen_description": self._handle_screen_description,
            "navigate_app": self._handle_screen_description,  # Starts with screen look
            "add_note": self._handle_add_note,
            "query_note": self._handle_query_note,
            "general_question": self._handle_general_question,
            # High-stakes intents — stubs until ordering/travel tools built
            "order_food": self._handle_high_stakes_stub,
            "order_groceries": self._handle_high_stakes_stub,
            "book_travel": self._handle_high_stakes_stub,
            "fill_form": self._handle_high_stakes_stub,
            "smart_home": self._handle_high_stakes_stub,
            "search_web": self._handle_high_stakes_stub,
        }

    def _format_response(self, result: dict, context: UserContext) -> Response:
        """Format a result dict into a Response appropriate for the user's output mode."""
        text = result.get("text", "Done.")

        # For braille mode (Jordan): format in 40-char friendly chunks
        if context.braille_mode:
            text = self._format_for_braille(text)

        # For brief mode (Marcus): trim preamble
        if context.verbosity == "brief":
            text = self._trim_preamble(text)

        return Response(text=text)

    def _format_for_braille(self, text: str) -> str:
        """
        Format text for a 40-cell braille display.
        Break at sentence boundaries; avoid emoji and special chars.
        """
        import re
        # Remove emoji
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "]+",
            flags=re.UNICODE,
        )
        text = emoji_pattern.sub("", text)

        # Break into sentences for navigable chunks
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return "\n".join(sentences)

    def _trim_preamble(self, text: str) -> str:
        """Remove common AI preambles for brief mode."""
        preambles = [
            "Certainly! ",
            "Of course! ",
            "Great question! ",
            "Sure! ",
            "I'd be happy to help with that. ",
            "Absolutely! ",
        ]
        for preamble in preambles:
            if text.startswith(preamble):
                text = text[len(preamble):]
        return text
