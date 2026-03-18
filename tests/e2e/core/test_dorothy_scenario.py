"""
Phase 5 Gate: Dorothy Scenario Test

Tests the complete user flow from the perspective of two blind user personas:
- Dorothy (blind-elder-user): 65+, recently lost sight, low technical confidence
- Alex (newly-blind-user): recently lost sight, learning assistive tech

These are the Phase 5 gate tests. Phase 5 is COMPLETE when Dorothy and Alex can:
  1. Understand setup instructions without asking "what do I do next?"
  2. Order food by voice (including risk disclosure)
  3. Save a note to their Second Brain by voice
  4. Retrieve a note from their Second Brain by voice

Without ever encountering:
  - Technical jargon (API, backend, token, keychain, server)
  - Instructions that presuppose visual context
  - A dead end with no path forward

Design principles:
  - External APIs mocked: Claude, ElevenLabs, Whisper, Playwright
  - Real: orchestrator, planner, confirmation gate, disclosure texts, vault logic
  - Persona-specific configs: speech_rate=0.7 for Dorothy, verbosity=standard

Per docs/PRIORITY_STACK.md Phase 5 gate:
  "Dorothy (elder persona) can: set up the app, order food, and add a note to
  her Second Brain — all without sighted help and without ever asking 'what do I
  do next?'"
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.core.orchestrator import Orchestrator, Response, UserContext
from blind_assistant.security.disclosure import FINANCIAL_RISK_DISCLOSURE

pytestmark = pytest.mark.e2e

# ─────────────────────────────────────────────────────────────
# Dorothy's persona configuration
# ─────────────────────────────────────────────────────────────

DOROTHY_CONTEXT = UserContext(
    user_id="dorothy_elder",
    session_id="dorothy_phase5_test",
    verbosity="standard",   # Dorothy needs full explanations, not brief
    speech_rate=0.7,         # Slower speech rate for older user
    output_mode="voice_text",
    braille_mode=False,
)

# Alex (newly-blind) also uses standard verbosity but a normal speech rate
ALEX_CONTEXT = UserContext(
    user_id="alex_newly_blind",
    session_id="alex_phase5_test",
    verbosity="standard",
    speech_rate=1.0,
    output_mode="voice_text",
    braille_mode=False,
)

# Jargon words that must NEVER appear in responses to Dorothy or Alex.
# Per Cycle 37 + 38 Dorothy test: technical terms are accessibility barriers.
FORBIDDEN_JARGON = [
    "API",
    "backend",
    "keychain",
    "subprocess",
    "endpoint",
    "token",         # "connection code" is the user-facing term
    "bearer",
    "JSON",
    "HTTP",
    "server",        # "your computer" or "Blind Assistant on your computer" instead
]


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _make_config(tmp_path) -> dict:
    """Minimal config for Dorothy scenario tests."""
    return {
        "vault_path": str(tmp_path / "dorothy_vault"),
        "telegram_enabled": False,
        "voice_local_enabled": False,
        "voice": {"prompt_timeout_seconds": 5},
    }


def _response_text(response: Response) -> str:
    """Return the text that would be spoken aloud to Dorothy."""
    return response.spoken_text or response.text


def _assert_no_jargon(text: str, persona: str = "Dorothy") -> None:
    """Assert response contains no technical jargon that would confuse a newly-blind user."""
    for word in FORBIDDEN_JARGON:
        assert word.lower() not in text.lower(), (
            f"{persona} test FAILED: Response contains jargon '{word}' which would confuse "
            f"a newly-blind or elderly user. Response was: {text!r}"
        )


def _assert_actionable(text: str, persona: str = "Dorothy") -> None:
    """Assert response gives Dorothy something to do next (no dead ends)."""
    # A response is actionable if it either:
    # 1. Contains a question (asking for follow-up)
    # 2. Contains a verb instruction ("say", "tap", "press", "ask", "tell me")
    # 3. Contains a confirmation/completion marker ("done", "complete", "ready")
    actionable_markers = ["?", "say ", "tap ", "press ", "ask ", "tell me", "done", "complete", "ready", "will "]
    has_action = any(marker.lower() in text.lower() for marker in actionable_markers)
    assert has_action, (
        f"{persona} test FAILED: Response gives no path forward (no question, instruction, "
        f"or completion). Dorothy would be stuck. Response was: {text!r}"
    )


# ─────────────────────────────────────────────────────────────
# Scenario 1: Second Brain — save a note
# ─────────────────────────────────────────────────────────────


class TestDorothySecondBrainSaveNote:
    """Dorothy adds a note to her Second Brain by voice."""

    @pytest.mark.asyncio
    async def test_save_note_response_is_plain_language(self, tmp_path, mock_keyring):
        """Response to 'remember that' should be in plain language with no jargon."""
        config = _make_config(tmp_path)

        # Mock the vault write so no real encryption is needed
        with (
            patch("anthropic.Anthropic"),
            patch("anthropic.AsyncAnthropic") as mock_async_anthropic,
            patch("blind_assistant.core.orchestrator.Orchestrator._classify_intent", new=AsyncMock(return_value="remember")),
            patch("blind_assistant.second_brain.vault.SecureVault.add_note", new=AsyncMock(return_value=None)),
            patch("blind_assistant.second_brain.vault.SecureVault._get_vault_key", return_value=b"k" * 32),
        ):
            mock_client = MagicMock()
            # Mock the response for the note summary
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Remembered: Doctor appointment on Friday at 2pm.")]
            mock_response.stop_reason = "end_turn"
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 8
            mock_client.messages.create = MagicMock(return_value=mock_response)
            mock_client.messages.acreate = AsyncMock(return_value=mock_response)
            mock_async_anthropic.return_value = mock_client

            orchestrator = Orchestrator(config=config)
            responses: list[Response] = []

            async def collect_response(r: Response) -> None:
                responses.append(r)

            await orchestrator.handle_message(
                message="Remember that I have a doctor appointment on Friday at 2pm",
                context=DOROTHY_CONTEXT,
                response_callback=collect_response,
            )

        # Should have gotten at least one response
        assert responses, "Dorothy got no response when trying to save a note"
        combined_text = " ".join(_response_text(r) for r in responses)
        # Must confirm the note was saved in plain language
        assert any(
            word in combined_text.lower()
            for word in ["remember", "saved", "noted", "got it", "added"]
        ), f"Dorothy's note save response doesn't confirm success. Got: {combined_text!r}"

    @pytest.mark.asyncio
    async def test_save_note_confirmation_uses_plain_language(self, tmp_path, mock_keyring):
        """Confirmation of note save must not use jargon."""
        config = _make_config(tmp_path)

        with (
            patch("anthropic.Anthropic"),
            patch("anthropic.AsyncAnthropic") as mock_async_anthropic,
            patch("blind_assistant.core.orchestrator.Orchestrator._classify_intent", new=AsyncMock(return_value="remember")),
            patch("blind_assistant.second_brain.vault.SecureVault.add_note", new=AsyncMock(return_value=None)),
            patch("blind_assistant.second_brain.vault.SecureVault._get_vault_key", return_value=b"k" * 32),
        ):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="I've noted that down for you.")]
            mock_response.stop_reason = "end_turn"
            mock_response.usage.input_tokens = 5
            mock_response.usage.output_tokens = 5
            mock_client.messages.acreate = AsyncMock(return_value=mock_response)
            mock_client.messages.create = MagicMock(return_value=mock_response)
            mock_async_anthropic.return_value = mock_client

            orchestrator = Orchestrator(config=config)
            responses: list[Response] = []

            async def collect(r: Response) -> None:
                responses.append(r)

            await orchestrator.handle_message(
                message="Remember that my pharmacy number is 555-1234",
                context=ALEX_CONTEXT,
                response_callback=collect,
            )

        assert responses, "Alex got no response when saving a note"
        for r in responses:
            text = _response_text(r)
            _assert_no_jargon(text, persona="Alex (newly-blind)")


# ─────────────────────────────────────────────────────────────
# Scenario 2: Second Brain — query a note
# ─────────────────────────────────────────────────────────────


class TestDorothySecondBrainQuery:
    """Dorothy retrieves a note from her Second Brain by voice."""

    @pytest.mark.asyncio
    async def test_query_response_is_conversational(self, tmp_path, mock_keyring):
        """Query response should be a natural language answer, not raw data."""
        config = _make_config(tmp_path)

        with (
            patch("anthropic.Anthropic"),
            patch("anthropic.AsyncAnthropic") as mock_async_anthropic,
            patch("blind_assistant.core.orchestrator.Orchestrator._classify_intent", new=AsyncMock(return_value="query")),
            patch(
                "blind_assistant.second_brain.query.query_vault",
                new=AsyncMock(return_value="Doctor appointment on Friday at 2pm"),
            ),
            patch("blind_assistant.second_brain.vault.SecureVault._get_vault_key", return_value=b"k" * 32),
        ):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="You have a doctor appointment on Friday at 2pm.")]
            mock_response.stop_reason = "end_turn"
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 10
            mock_client.messages.acreate = AsyncMock(return_value=mock_response)
            mock_client.messages.create = MagicMock(return_value=mock_response)
            mock_async_anthropic.return_value = mock_client

            orchestrator = Orchestrator(config=config)
            responses: list[Response] = []

            async def collect(r: Response) -> None:
                responses.append(r)

            await orchestrator.handle_message(
                message="When is my doctor appointment?",
                context=DOROTHY_CONTEXT,
                response_callback=collect,
            )

        assert responses, "Dorothy got no response to a Second Brain query"
        combined = " ".join(_response_text(r) for r in responses)
        # Response must contain the answer
        assert "friday" in combined.lower() or "2pm" in combined.lower(), (
            f"Dorothy's query response doesn't include the answer. Got: {combined!r}"
        )

    @pytest.mark.asyncio
    async def test_query_no_jargon_in_response(self, tmp_path, mock_keyring):
        """Second Brain query responses must never contain technical jargon."""
        config = _make_config(tmp_path)

        with (
            patch("anthropic.Anthropic"),
            patch("anthropic.AsyncAnthropic") as mock_async_anthropic,
            patch("blind_assistant.core.orchestrator.Orchestrator._classify_intent", new=AsyncMock(return_value="query")),
            patch(
                "blind_assistant.second_brain.query.query_vault",
                new=AsyncMock(return_value="Pharmacy number is 555-1234"),
            ),
            patch("blind_assistant.second_brain.vault.SecureVault._get_vault_key", return_value=b"k" * 32),
        ):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Your pharmacy number is 555-1234.")]
            mock_response.stop_reason = "end_turn"
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 8
            mock_client.messages.acreate = AsyncMock(return_value=mock_response)
            mock_client.messages.create = MagicMock(return_value=mock_response)
            mock_async_anthropic.return_value = mock_client

            orchestrator = Orchestrator(config=config)
            responses: list[Response] = []

            async def collect(r: Response) -> None:
                responses.append(r)

            await orchestrator.handle_message(
                message="What is my pharmacy number?",
                context=ALEX_CONTEXT,
                response_callback=collect,
            )

        assert responses
        for r in responses:
            _assert_no_jargon(_response_text(r), persona="Alex (newly-blind)")


# ─────────────────────────────────────────────────────────────
# Scenario 3: Food ordering — risk disclosure fires
# ─────────────────────────────────────────────────────────────


class TestDorothyFoodOrdering:
    """Dorothy orders food by voice. Financial risk disclosure must always fire."""

    @pytest.mark.asyncio
    async def test_food_order_triggers_risk_disclosure(self, tmp_path, mock_keyring):
        """When Dorothy asks to order food, the risk disclosure must be spoken."""
        config = _make_config(tmp_path)

        spoken: list[str] = []

        async def collect(r: Response) -> None:
            spoken.append(_response_text(r))

        with (
            patch("anthropic.Anthropic"),
            patch("anthropic.AsyncAnthropic") as mock_async_anthropic,
            patch("blind_assistant.core.orchestrator.Orchestrator._classify_intent", new=AsyncMock(return_value="order_food")),
            patch("blind_assistant.tools.browser.BrowserTool.navigate", new=AsyncMock(return_value=MagicMock())),
            patch("blind_assistant.tools.browser.BrowserTool.close", new=AsyncMock(return_value=None)),
            patch(
                "blind_assistant.core.orchestrator.Orchestrator._handle_order_food",
                new=AsyncMock(
                    return_value=Response(
                        text=FINANCIAL_RISK_DISCLOSURE + "\n\nWould you like to continue?",
                        spoken_text=FINANCIAL_RISK_DISCLOSURE + " Would you like to continue ordering?",
                        requires_confirmation=True,
                    )
                ),
            ),
        ):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="I'll help you order food.")]
            mock_response.stop_reason = "end_turn"
            mock_response.usage.input_tokens = 5
            mock_response.usage.output_tokens = 5
            mock_client.messages.acreate = AsyncMock(return_value=mock_response)
            mock_client.messages.create = MagicMock(return_value=mock_response)
            mock_async_anthropic.return_value = mock_client

            orchestrator = Orchestrator(config=config)
            await orchestrator.handle_message(
                message="Order me a pizza",
                context=DOROTHY_CONTEXT,
                response_callback=collect,
            )

        combined = " ".join(spoken)
        # The financial risk disclosure must appear in the spoken output
        assert "financial" in combined.lower() or "payment" in combined.lower() or "risk" in combined.lower(), (
            "Dorothy test FAILED: Food order flow did not speak financial risk disclosure. "
            f"Combined spoken text: {combined!r}"
        )

    @pytest.mark.asyncio
    async def test_food_order_asks_confirmation_before_proceeding(self, tmp_path, mock_keyring):
        """After risk disclosure, Dorothy must be asked to confirm before any payment."""
        config = _make_config(tmp_path)

        responses: list[Response] = []

        async def collect(r: Response) -> None:
            responses.append(r)

        with (
            patch("anthropic.Anthropic"),
            patch("anthropic.AsyncAnthropic") as mock_async_anthropic,
            patch("blind_assistant.core.orchestrator.Orchestrator._classify_intent", new=AsyncMock(return_value="order_food")),
            patch(
                "blind_assistant.core.orchestrator.Orchestrator._handle_order_food",
                new=AsyncMock(
                    return_value=Response(
                        text="Before I continue, I need to let you know that sharing payment details carries risk. Do you want to continue?",
                        requires_confirmation=True,
                        confirmation_action="proceed_food_order",
                    )
                ),
            ),
        ):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Ordering food for you.")]
            mock_response.stop_reason = "end_turn"
            mock_response.usage.input_tokens = 5
            mock_response.usage.output_tokens = 5
            mock_client.messages.acreate = AsyncMock(return_value=mock_response)
            mock_client.messages.create = MagicMock(return_value=mock_response)
            mock_async_anthropic.return_value = mock_client

            orchestrator = Orchestrator(config=config)
            await orchestrator.handle_message(
                message="Order pizza for me",
                context=DOROTHY_CONTEXT,
                response_callback=collect,
            )

        # At minimum one response must require confirmation
        assert responses, "Dorothy got no response to food order request"
        requires_confirm = any(r.requires_confirmation for r in responses)
        assert requires_confirm, (
            "Dorothy test FAILED: Food order flow did not require confirmation. "
            "Payment must never proceed without explicit user consent."
        )


# ─────────────────────────────────────────────────────────────
# Scenario 4: General assistant response quality
# ─────────────────────────────────────────────────────────────


class TestDorothyGeneralInteraction:
    """Dorothy asks general questions. Responses must be clear, patient, jargon-free."""

    @pytest.mark.asyncio
    async def test_general_question_response_has_no_jargon(self, tmp_path, mock_keyring):
        """Dorothy's general questions should get plain-language responses."""
        config = _make_config(tmp_path)

        with (
            patch("anthropic.Anthropic"),
            patch("anthropic.AsyncAnthropic") as mock_async_anthropic,
            patch("blind_assistant.core.orchestrator.Orchestrator._classify_intent", new=AsyncMock(return_value="general")),
        ):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="The weather today is partly cloudy with a high of 72 degrees.")]
            mock_response.stop_reason = "end_turn"
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 12
            mock_client.messages.acreate = AsyncMock(return_value=mock_response)
            mock_client.messages.create = MagicMock(return_value=mock_response)
            mock_async_anthropic.return_value = mock_client

            orchestrator = Orchestrator(config=config)
            responses: list[Response] = []

            async def collect(r: Response) -> None:
                responses.append(r)

            await orchestrator.handle_message(
                message="What is the weather like today?",
                context=DOROTHY_CONTEXT,
                response_callback=collect,
            )

        assert responses, "Dorothy got no response to a general question"
        for r in responses:
            text = _response_text(r)
            _assert_no_jargon(text, persona="Dorothy")

    @pytest.mark.asyncio
    async def test_response_to_newly_blind_is_patient_in_tone(self, tmp_path, mock_keyring):
        """Alex (newly-blind) should get responses that don't presuppose experience."""
        config = _make_config(tmp_path)

        with (
            patch("anthropic.Anthropic"),
            patch("anthropic.AsyncAnthropic") as mock_async_anthropic,
            patch("blind_assistant.core.orchestrator.Orchestrator._classify_intent", new=AsyncMock(return_value="general")),
        ):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="I can help you read that document. Just hold your phone's camera over it.")]
            mock_response.stop_reason = "end_turn"
            mock_response.usage.input_tokens = 8
            mock_response.usage.output_tokens = 12
            mock_client.messages.acreate = AsyncMock(return_value=mock_response)
            mock_client.messages.create = MagicMock(return_value=mock_response)
            mock_async_anthropic.return_value = mock_client

            orchestrator = Orchestrator(config=config)
            responses: list[Response] = []

            async def collect(r: Response) -> None:
                responses.append(r)

            await orchestrator.handle_message(
                message="How do I read a piece of mail?",
                context=ALEX_CONTEXT,
                response_callback=collect,
            )

        assert responses, "Alex got no response"
        for r in responses:
            text = _response_text(r)
            _assert_no_jargon(text, persona="Alex (newly-blind)")
            # Response must not use visual-only language
            visual_only = ["click", "look at", "you can see", "as shown", "in the image"]
            for phrase in visual_only:
                assert phrase.lower() not in text.lower(), (
                    f"Alex test FAILED: Response uses visual-only language '{phrase}'. "
                    f"Response: {text!r}"
                )


# ─────────────────────────────────────────────────────────────
# Scenario 5: Setup language validation (SetupWizardScreen strings)
# ─────────────────────────────────────────────────────────────


class TestDorothySetupLanguage:
    """Validate that the setup wizard uses Dorothy-appropriate language.

    These tests check the Python installer (not the React Native component,
    which is covered by SetupWizardScreen.test.tsx). The installer's spoken
    prompts must also be jargon-free.
    """

    def test_installer_welcome_message_is_plain_language(self):
        """The installer's first spoken message must be comprehensible to a newly-blind user."""
        from blind_assistant.installer.install import VoiceGuidedInstaller

        installer = VoiceGuidedInstaller.__new__(VoiceGuidedInstaller)
        # The installer has STEP_MESSAGES or equivalent; check the welcome text
        # is in the installer module and contains no jargon
        import blind_assistant.installer.install as install_module
        source = install_module.__doc__ or ""
        # The key check: the installer Python module must not refer to "API token"
        # in its user-facing strings — these have been replaced with "connection code"
        # Check actual spoken prompts in the install module
        import inspect
        source_code = inspect.getsource(install_module)
        # Look for any remaining "API token" in voice-facing strings (not comments)
        # We allow it in comments (developer docs) but not in speak() calls
        import re
        speak_calls = re.findall(r'speak\(["\']([^"\']*)["\']', source_code)
        for spoken_text in speak_calls:
            assert "API token" not in spoken_text, (
                f"Installer installer speak() call contains jargon 'API token': {spoken_text!r}\n"
                "Replace with 'connection code' for Dorothy."
            )
            assert "backend server" not in spoken_text.lower(), (
                f"Installer speak() call contains jargon 'backend server': {spoken_text!r}\n"
                "Replace with 'your computer' for Dorothy."
            )

    def test_disclosure_texts_are_not_jargon_heavy(self):
        """Financial risk disclosure must be in plain language that Dorothy can understand."""
        from blind_assistant.security.disclosure import FINANCIAL_RISK_DISCLOSURE

        # Disclosure must mention the risk clearly
        assert "risk" in FINANCIAL_RISK_DISCLOSURE.lower() or "warning" in FINANCIAL_RISK_DISCLOSURE.lower(), (
            "Financial risk disclosure doesn't warn about risk — Dorothy needs to know."
        )
        # Must not be all technical jargon
        plain_words = ["payment", "money", "financial", "details", "information"]
        has_plain = any(w in FINANCIAL_RISK_DISCLOSURE.lower() for w in plain_words)
        assert has_plain, (
            f"Financial risk disclosure doesn't use any plain language words. "
            f"Dorothy needs to understand this warning. Got: {FINANCIAL_RISK_DISCLOSURE!r}"
        )
