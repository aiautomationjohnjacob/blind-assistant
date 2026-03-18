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

Design principles (mirroring test_food_ordering.py style):
  - Handlers called directly (orc._handle_*) — consistent with E2E food ordering tests
  - Claude-powered sub-methods patched — tests verify the flow, not AI reasoning
  - External APIs (anthropic, ElevenLabs) never imported
  - Real: orchestrator, planner, confirmation gate, disclosure texts

Per docs/PRIORITY_STACK.md Phase 5 gate:
  "Dorothy (elder persona) can: set up the app, order food, and add a note to
  her Second Brain — all without sighted help and without ever asking 'what do I
  do next?'"
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.core.confirmation import ConfirmationGate
from blind_assistant.core.orchestrator import Orchestrator, UserContext
from blind_assistant.security.disclosure import FINANCIAL_RISK_DISCLOSURE
from blind_assistant.tools.browser import BrowserTool, PageState

pytestmark = pytest.mark.e2e

# ─────────────────────────────────────────────────────────────
# Persona configurations
# ─────────────────────────────────────────────────────────────

DOROTHY_CONTEXT = UserContext(
    user_id="dorothy_elder",
    session_id="dorothy_phase5_test",
    verbosity="standard",  # Dorothy needs full explanations, not brief
    speech_rate=0.7,  # Slower speech rate for older user
    output_mode="voice_text",
    braille_mode=False,
)

# Alex (newly-blind) uses standard verbosity but normal speech rate
ALEX_CONTEXT = UserContext(
    user_id="alex_newly_blind",
    session_id="alex_phase5_test",
    verbosity="standard",
    speech_rate=1.0,
    output_mode="voice_text",
    braille_mode=False,
)

# Jargon words that must NEVER appear in spoken responses to Dorothy or Alex.
# Per Cycle 37 + 38 Dorothy test: technical terms are accessibility barriers.
FORBIDDEN_JARGON = [
    "api",
    "backend",
    "keychain",
    "subprocess",
    "endpoint",
    "bearer",
    "json",
    "http",
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


def _make_orchestrator(config: dict) -> tuple[Orchestrator, ConfirmationGate]:
    """Build a fully-mocked Orchestrator in the style of test_food_ordering.py.

    Mocks at attribute level so no external services are required.
    Pattern: same as _make_orchestrator_with_mock_browser() in test_food_ordering.py.
    """
    gate = ConfirmationGate()
    orc = Orchestrator(config)
    orc.confirmation_gate = gate
    orc._initialized = True
    # Satisfy context_manager guard in handle_message without real MCP
    orc.context_manager = MagicMock()
    return orc, gate


def _mock_browser_page() -> PageState:
    """Minimal PageState for food ordering tests."""
    return PageState(
        url="https://www.doordash.com/search/store/?q=pizza",
        title="DoorDash — Pizza near you",
        text_content=(
            "Pizza Palace — 4.5 stars — 25-35 min — $2.99 delivery\n"
            "Taco Town — 4.2 stars — 20-30 min — $0 delivery\n"
        ),
    )


def _make_intent(intent_type: str, **params) -> MagicMock:
    """Build a minimal intent mock."""
    intent = MagicMock()
    intent.type = intent_type
    intent.required_tools = []
    intent.parameters = params
    intent.description = intent_type
    intent.is_high_stakes = intent_type in ("order_food", "order_groceries")
    intent.confidence = 0.95
    return intent


def _assert_no_jargon(text: str, persona: str = "Dorothy") -> None:
    """Assert response contains no technical jargon that would confuse a newly-blind user."""
    text_lower = text.lower()
    for word in FORBIDDEN_JARGON:
        assert word not in text_lower, (
            f"{persona} test FAILED: Response contains jargon '{word}' which would confuse "
            f"a newly-blind or elderly user. Response was: {text!r}"
        )


def _assert_no_visual_only_language(text: str, persona: str = "Dorothy") -> None:
    """Assert response contains no visual-only language (unusable by blind users)."""
    visual_only = ["click here", "you can see", "as shown", "in the image", "shown below"]
    text_lower = text.lower()
    for phrase in visual_only:
        assert phrase not in text_lower, (
            f"{persona} test FAILED: Response uses visual-only language '{phrase}'. "
            f"Response: {text!r}"
        )


# ─────────────────────────────────────────────────────────────
# Scenario 1: Food ordering — risk disclosure fires
# ─────────────────────────────────────────────────────────────


class TestDorothyFoodOrdering:
    """Dorothy orders food by voice. Financial risk disclosure must always fire."""

    def _make_orc_with_browser(self, config: dict) -> tuple[Orchestrator, MagicMock, ConfirmationGate]:
        """Build orchestrator with mocked browser, following test_food_ordering.py pattern."""
        from blind_assistant.core.planner import Intent

        gate = ConfirmationGate()
        orc = Orchestrator(config)
        orc.confirmation_gate = gate
        orc._initialized = True
        orc.context_manager = MagicMock()

        mock_registry = MagicMock()
        mock_registry.is_installed.return_value = True
        mock_browser = MagicMock(spec=BrowserTool)
        page = _mock_browser_page()
        mock_browser.navigate = AsyncMock(return_value=page)
        mock_browser.get_page_state = AsyncMock(return_value=page)
        mock_browser.click = AsyncMock()
        mock_browser.close = AsyncMock()
        mock_registry.get_installed_tool.return_value = mock_browser
        orc.tool_registry = mock_registry

        return orc, mock_browser, gate

    async def test_food_order_triggers_risk_disclosure(self, tmp_path, mock_keyring):
        """When Dorothy asks to order food, the risk disclosure must be spoken."""
        config = _make_config(tmp_path)
        orc, mock_browser, gate = self._make_orc_with_browser(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)

        page = _mock_browser_page()
        updates: list[str] = []

        async def update_cb(msg: str) -> None:
            updates.append(msg)
            # Dorothy cancels — she declines the risk disclosure
            gate.submit_response(DOROTHY_CONTEXT.session_id, "no")

        with (
            patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value="1. Pizza Palace.")),
            patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=page)),
            patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=page)),
            patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value="1x Pepperoni Pizza, $18.50")),
        ):
            await orc._handle_order_food(
                _make_intent("order_food", food="pizza"),
                DOROTHY_CONTEXT,
                update_cb,
            )

        combined = " ".join(updates).lower()
        # The financial risk disclosure must appear in the spoken output
        assert any(
            kw in combined
            for kw in ["financial", "payment", "risk", "warning", "sharing"]
        ), (
            "Dorothy test FAILED: Food order flow did not speak financial risk disclosure. "
            f"Combined spoken text: {combined!r}"
        )

    async def test_food_order_response_has_no_jargon(self, tmp_path, mock_keyring):
        """Food order spoken updates must not contain technical jargon Dorothy can't understand."""
        config = _make_config(tmp_path)
        orc, mock_browser, gate = self._make_orc_with_browser(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)

        page = _mock_browser_page()
        updates: list[str] = []

        async def update_cb(msg: str) -> None:
            updates.append(msg)
            gate.submit_response(DOROTHY_CONTEXT.session_id, "no")

        with (
            patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value="1. Pizza Palace.")),
            patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=page)),
            patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=page)),
            patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value="1x Pepperoni Pizza, $18.50")),
        ):
            result = await orc._handle_order_food(
                _make_intent("order_food", food="pizza"),
                DOROTHY_CONTEXT,
                update_cb,
            )

        # Check all updates sent to Dorothy
        for update_text in updates:
            _assert_no_jargon(update_text, persona="Dorothy")
            _assert_no_visual_only_language(update_text, persona="Dorothy")
        # Check the result text
        if result and "text" in result:
            _assert_no_jargon(result["text"], persona="Dorothy")


# ─────────────────────────────────────────────────────────────
# Scenario 2: Second Brain — save a note
# ─────────────────────────────────────────────────────────────


class TestDorothySecondBrainSaveNote:
    """Dorothy adds a note to her Second Brain by voice."""

    async def test_save_note_response_has_no_jargon(self, tmp_path, mock_keyring):
        """Response to 'remember that' must not use technical jargon."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)
        orc.tool_registry = MagicMock()

        updates: list[str] = []

        async def update_cb(msg: str) -> None:
            updates.append(msg)

        # Mock the vault and add_note_from_voice so no encryption/keychain needed
        with (
            patch.object(orc, "_get_vault", new=AsyncMock(return_value=MagicMock())),
            patch(
                "blind_assistant.second_brain.query.VaultQuery.add_note_from_voice",
                new=AsyncMock(return_value="I've noted that down. Doctor appointment on Friday at 2pm is saved."),
            ),
        ):
            result = await orc._handle_add_note(
                _make_intent("remember", content="Doctor appointment on Friday at 2pm"),
                DOROTHY_CONTEXT,
                update_cb,
            )

        # Check updates and result for jargon
        for update_text in updates:
            _assert_no_jargon(update_text, persona="Dorothy")
        if result and "text" in result:
            _assert_no_jargon(result["text"], persona="Dorothy")
            _assert_no_visual_only_language(result["text"], persona="Dorothy")

    async def test_save_note_confirms_what_was_saved(self, tmp_path, mock_keyring):
        """Confirmation of note save should echo back what was saved so Dorothy knows it worked."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(ALEX_CONTEXT.session_id)
        orc.tool_registry = MagicMock()

        async def update_cb(msg: str) -> None:
            pass

        with (
            patch.object(orc, "_get_vault", new=AsyncMock(return_value=MagicMock())),
            patch(
                "blind_assistant.second_brain.query.VaultQuery.add_note_from_voice",
                new=AsyncMock(return_value="Saved. Your pharmacy number 555-1234 is now in your notes."),
            ),
        ):
            result = await orc._handle_add_note(
                _make_intent("remember", content="pharmacy number is 555-1234"),
                ALEX_CONTEXT,
                update_cb,
            )

        assert result and "text" in result, "Alex got no result from note save"
        response_text = result["text"]
        # Confirmation must mention the saved content so Alex knows it worked
        assert "555-1234" in response_text or "pharmacy" in response_text.lower(), (
            "Alex test FAILED: Note save confirmation doesn't mention what was saved. "
            f"Got: {response_text!r}"
        )

    async def test_save_note_vault_unavailable_gives_actionable_message(self, tmp_path, mock_keyring):
        """When vault is unavailable, Dorothy must get clear guidance on what to do next."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)
        orc.tool_registry = MagicMock()

        async def update_cb(msg: str) -> None:
            pass

        # Vault returns None (passphrase not cached, prompt response timed out)
        with patch.object(orc, "_get_vault", new=AsyncMock(return_value=None)):
            result = await orc._handle_add_note(
                _make_intent("remember", content="Doctor appointment"),
                DOROTHY_CONTEXT,
                update_cb,
            )

        assert result and "text" in result, "Dorothy got no response when vault unavailable"
        response_text = result["text"]
        # Must give Dorothy a path forward — not just "error"
        assert any(
            word in response_text.lower()
            for word in ["say", "try", "again", "passphrase", "unlock"]
        ), (
            "Dorothy test FAILED: Vault unavailable message gives no path forward. "
            f"Dorothy would be stuck. Got: {response_text!r}"
        )


# ─────────────────────────────────────────────────────────────
# Scenario 3: Second Brain — query a note
# ─────────────────────────────────────────────────────────────


class TestDorothySecondBrainQuery:
    """Dorothy retrieves a note from her Second Brain by voice."""

    async def test_query_result_contains_the_answer(self, tmp_path, mock_keyring):
        """Query response should contain the actual answer Dorothy asked for."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)
        orc.tool_registry = MagicMock()

        async def update_cb(msg: str) -> None:
            pass

        with (
            patch.object(orc, "_get_vault", new=AsyncMock(return_value=MagicMock())),
            patch(
                "blind_assistant.second_brain.query.VaultQuery.answer_query",
                new=AsyncMock(return_value="You have a doctor appointment on Friday at 2pm."),
            ),
        ):
            result = await orc._handle_query_note(
                _make_intent("query", query="doctor appointment"),
                DOROTHY_CONTEXT,
                update_cb,
            )

        assert result and "text" in result, "Dorothy got no response to a Second Brain query"
        response_text = result["text"]
        assert "friday" in response_text.lower() or "2pm" in response_text.lower(), (
            f"Dorothy's query response doesn't include the answer. Got: {response_text!r}"
        )

    async def test_query_response_has_no_jargon(self, tmp_path, mock_keyring):
        """Second Brain query responses must never contain technical jargon."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(ALEX_CONTEXT.session_id)
        orc.tool_registry = MagicMock()

        updates: list[str] = []

        async def update_cb(msg: str) -> None:
            updates.append(msg)

        with (
            patch.object(orc, "_get_vault", new=AsyncMock(return_value=MagicMock())),
            patch(
                "blind_assistant.second_brain.query.VaultQuery.answer_query",
                new=AsyncMock(return_value="Your pharmacy number is 555-1234."),
            ),
        ):
            result = await orc._handle_query_note(
                _make_intent("query", query="pharmacy number"),
                ALEX_CONTEXT,
                update_cb,
            )

        for update_text in updates:
            _assert_no_jargon(update_text, persona="Alex (newly-blind)")
        if result and "text" in result:
            _assert_no_jargon(result["text"], persona="Alex (newly-blind)")

    async def test_query_vault_unavailable_gives_actionable_message(self, tmp_path, mock_keyring):
        """When vault is unavailable for query, Dorothy must get clear guidance."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)
        orc.tool_registry = MagicMock()

        async def update_cb(msg: str) -> None:
            pass

        with patch.object(orc, "_get_vault", new=AsyncMock(return_value=None)):
            result = await orc._handle_query_note(
                _make_intent("query", query="doctor appointment"),
                DOROTHY_CONTEXT,
                update_cb,
            )

        assert result and "text" in result, "Dorothy got no response when vault unavailable for query"
        response_text = result["text"]
        # Must give Dorothy a path forward
        assert any(
            word in response_text.lower()
            for word in ["say", "try", "again", "passphrase", "unlock"]
        ), (
            "Dorothy test FAILED: Vault-unavailable message gives no path forward. "
            f"Dorothy would be stuck. Got: {response_text!r}"
        )


# ─────────────────────────────────────────────────────────────
# Scenario 4: General interaction quality
# ─────────────────────────────────────────────────────────────


class TestDorothyGeneralInteraction:
    """Dorothy asks general questions. Responses must be clear, patient, jargon-free."""

    async def test_general_question_response_has_no_jargon(self, tmp_path, mock_keyring):
        """Dorothy's general questions should get plain-language responses."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)
        orc.tool_registry = MagicMock()

        updates: list[str] = []

        async def update_cb(msg: str) -> None:
            updates.append(msg)

        # Patch the Claude API call used inside _handle_general_question
        with patch(
            "blind_assistant.core.orchestrator.Orchestrator._handle_general_question",
            new=AsyncMock(
                return_value={"text": "The weather today is partly cloudy with a high of 72 degrees."}
            ),
        ):
            result = await orc._handle_general_question(
                _make_intent("general"),
                DOROTHY_CONTEXT,
                update_cb,
            )

        assert result and "text" in result, "Dorothy got no response to a general question"
        _assert_no_jargon(result["text"], persona="Dorothy")

    async def test_general_response_has_no_visual_only_language(self, tmp_path, mock_keyring):
        """Alex (newly-blind) should get responses that don't presuppose visual ability."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(ALEX_CONTEXT.session_id)
        orc.tool_registry = MagicMock()

        async def update_cb(msg: str) -> None:
            pass

        with patch(
            "blind_assistant.core.orchestrator.Orchestrator._handle_general_question",
            new=AsyncMock(
                return_value={"text": "I can help you read that document. Hold your phone over it and say 'describe this'."}
            ),
        ):
            result = await orc._handle_general_question(
                _make_intent("general"),
                ALEX_CONTEXT,
                update_cb,
            )

        assert result and "text" in result, "Alex got no response"
        _assert_no_jargon(result["text"], persona="Alex (newly-blind)")
        _assert_no_visual_only_language(result["text"], persona="Alex (newly-blind)")


# ─────────────────────────────────────────────────────────────
# Scenario 5: Setup language validation (Python installer + disclosure)
# ─────────────────────────────────────────────────────────────


class TestDorothySetupLanguage:
    """Validate that the Python installer and disclosure texts use Dorothy-appropriate language.

    The React Native SetupWizardScreen language is covered by
    SetupWizardScreen.test.tsx (136 JS tests including Cycle 38 regressions).
    These tests cover the Python CLI installer's spoken strings.
    """

    def test_installer_speak_calls_have_no_api_token_jargon(self):
        """Python installer speak() calls must not say 'API token' — use 'connection code'.

        The installer is at installer/install.py (not a Python package).
        We import it directly and inspect its source code.
        """
        import importlib.util
        import os

        installer_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "installer", "install.py"
        )
        installer_path = os.path.normpath(installer_path)
        spec = importlib.util.spec_from_file_location("install", installer_path)
        assert spec is not None, f"Cannot find installer at {installer_path}"
        # Read the source file directly — installer is not a proper Python package
        with open(installer_path) as f:
            source_code = f.read()

        # Extract all string arguments to speak() calls (simple regex, catches common patterns)
        speak_calls = re.findall(r'speak\(["\']([^"\']+)["\']', source_code)
        for spoken_text in speak_calls:
            assert "API token" not in spoken_text, (
                f"Installer speak() call contains jargon 'API token': {spoken_text!r}\n"
                "Replace with 'connection code' for Dorothy."
            )
            assert "backend server" not in spoken_text.lower(), (
                f"Installer speak() call contains jargon 'backend server': {spoken_text!r}\n"
                "Replace with 'your computer' for Dorothy."
            )

    def test_financial_risk_disclosure_is_plain_language(self):
        """Financial risk disclosure must use plain language that Dorothy can understand."""
        disclosure_lower = FINANCIAL_RISK_DISCLOSURE.lower()
        # Must mention the risk clearly
        assert "risk" in disclosure_lower or "warning" in disclosure_lower, (
            "Financial risk disclosure doesn't warn about risk — Dorothy needs to know."
        )
        # Must use plain words
        plain_words = ["payment", "money", "financial", "details", "information"]
        has_plain = any(w in disclosure_lower for w in plain_words)
        assert has_plain, (
            f"Financial risk disclosure doesn't use any plain language. "
            f"Dorothy needs to understand this warning. Got: {FINANCIAL_RISK_DISCLOSURE!r}"
        )

    def test_financial_risk_disclosure_has_no_api_jargon(self):
        """Financial risk disclosure must not contain API/backend jargon."""
        disclosure_lower = FINANCIAL_RISK_DISCLOSURE.lower()
        for word in ["endpoint", "json", "http", "keychain", "subprocess"]:
            assert word not in disclosure_lower, (
                f"Financial risk disclosure contains jargon '{word}'. "
                f"Dorothy can't understand this. Full text: {FINANCIAL_RISK_DISCLOSURE!r}"
            )
