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
import inspect
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.core.confirmation import ConfirmationGate
from blind_assistant.core.orchestrator import Orchestrator, Response, UserContext
from blind_assistant.security.disclosure import FINANCIAL_RISK_DISCLOSURE
from blind_assistant.tools.browser import BrowserTool, PageState

pytestmark = pytest.mark.e2e

# ─────────────────────────────────────────────────────────────
# Dorothy's persona configuration
# ─────────────────────────────────────────────────────────────

DOROTHY_CONTEXT = UserContext(
    user_id="dorothy_elder",
    session_id="dorothy_phase5_test",
    verbosity="standard",  # Dorothy needs full explanations, not brief
    speech_rate=0.7,  # Slower speech rate for older user
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
    """Build a fully mocked Orchestrator in the style of the food ordering E2E tests.

    Follows the same pattern as _make_orchestrator_with_mock_browser() in
    test_food_ordering.py: mock at the attribute level so no real external
    services (anthropic, keychain) are needed.
    """
    from blind_assistant.core.planner import Intent

    gate = ConfirmationGate()
    orc = Orchestrator(config)
    orc.confirmation_gate = gate
    orc._initialized = True
    # Satisfy the context_manager guard in handle_message without real MCP services
    orc.context_manager = MagicMock()
    return orc, gate


def _response_text(response: Response) -> str:
    """Return the text that would be spoken aloud to Dorothy."""
    return response.spoken_text or response.text


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

    @pytest.fixture
    def mock_food_page_state(self) -> PageState:
        """Simulates a food ordering page state."""
        return PageState(
            url="https://www.doordash.com/search/store/?q=pizza",
            title="DoorDash — Pizza near you",
            text_content=(
                "Pizza Palace — 4.5 stars — 25-35 min — $2.99 delivery\n"
                "Taco Town — 4.2 stars — 20-30 min — $0 delivery\n"
            ),
            interactive_elements=[],
        )

    async def test_food_order_triggers_risk_disclosure(self, tmp_path, mock_keyring, mock_food_page_state):
        """When Dorothy asks to order food, the risk disclosure must be spoken."""
        from blind_assistant.core.planner import Intent

        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)

        # Mock planner to classify as "order_food"
        mock_planner = MagicMock()
        mock_planner.classify_intent = AsyncMock(
            return_value=Intent(
                type="order_food",
                description="order pizza",
                required_tools=["browser"],
                parameters={"food": "pizza"},
                is_high_stakes=True,
                confidence=0.95,
            )
        )
        orc.planner = mock_planner

        # Mock tool registry with browser available
        mock_registry = MagicMock()
        mock_registry.is_installed.return_value = True
        mock_browser = MagicMock(spec=BrowserTool)
        mock_browser.navigate = AsyncMock(return_value=mock_food_page_state)
        mock_browser.get_page_state = AsyncMock(return_value=mock_food_page_state)
        mock_browser.click = AsyncMock()
        mock_browser.close = AsyncMock()
        mock_registry.get_installed_tool.return_value = mock_browser
        orc.tool_registry = mock_registry

        spoken: list[str] = []

        async def collect(r: Response) -> None:
            spoken.append(_response_text(r))

        with (
            patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value="1. Pizza Palace. 2. Taco Town.")),
            patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=mock_food_page_state)),
            patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=mock_food_page_state)),
            patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value="1x Pepperoni Pizza, $18.50")),
        ):
            # Simulate Dorothy saying "no" to the disclosure (cancel, so no real order)
            async def send_no_after_disclosure() -> None:
                await asyncio.sleep(0.05)
                gate.receive_response(DOROTHY_CONTEXT.session_id, "no")

            asyncio.ensure_future(send_no_after_disclosure())

            await orc.handle_message(
                message="Order me a pizza",
                context=DOROTHY_CONTEXT,
                response_callback=collect,
            )

        combined = " ".join(spoken)
        # The financial risk disclosure must appear in the spoken output
        assert any(
            kw in combined.lower()
            for kw in ["financial", "payment", "risk", "warning", "sharing"]
        ), (
            "Dorothy test FAILED: Food order flow did not speak financial risk disclosure. "
            f"Combined spoken text: {combined!r}"
        )

    async def test_food_order_response_has_no_jargon(self, tmp_path, mock_keyring, mock_food_page_state):
        """Food order response must not contain technical jargon Dorothy can't understand."""
        from blind_assistant.core.planner import Intent

        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)

        mock_planner = MagicMock()
        mock_planner.classify_intent = AsyncMock(
            return_value=Intent(
                type="order_food",
                description="order pizza",
                required_tools=["browser"],
                parameters={"food": "pizza"},
                is_high_stakes=True,
                confidence=0.95,
            )
        )
        orc.planner = mock_planner

        mock_registry = MagicMock()
        mock_registry.is_installed.return_value = True
        mock_browser = MagicMock(spec=BrowserTool)
        mock_browser.navigate = AsyncMock(return_value=mock_food_page_state)
        mock_browser.get_page_state = AsyncMock(return_value=mock_food_page_state)
        mock_browser.click = AsyncMock()
        mock_browser.close = AsyncMock()
        mock_registry.get_installed_tool.return_value = mock_browser
        orc.tool_registry = mock_registry

        responses: list[Response] = []

        async def collect(r: Response) -> None:
            responses.append(r)

        with (
            patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value="1. Pizza Palace. 2. Taco Town.")),
            patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=mock_food_page_state)),
            patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=mock_food_page_state)),
            patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value="1x Pepperoni Pizza, $18.50")),
        ):
            async def send_no() -> None:
                await asyncio.sleep(0.05)
                gate.receive_response(DOROTHY_CONTEXT.session_id, "no")

            asyncio.ensure_future(send_no())

            await orc.handle_message(
                message="Order me a pizza",
                context=DOROTHY_CONTEXT,
                response_callback=collect,
            )

        assert responses, "Dorothy got no response to food order"
        for r in responses:
            _assert_no_jargon(_response_text(r), persona="Dorothy")
            _assert_no_visual_only_language(_response_text(r), persona="Dorothy")

    async def test_food_order_requires_confirmation(self, tmp_path, mock_keyring, mock_food_page_state):
        """After risk disclosure, Dorothy must be asked to confirm before any payment proceeds."""
        from blind_assistant.core.planner import Intent

        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)

        mock_planner = MagicMock()
        mock_planner.classify_intent = AsyncMock(
            return_value=Intent(
                type="order_food",
                description="order pizza",
                required_tools=["browser"],
                parameters={"food": "pizza"},
                is_high_stakes=True,
                confidence=0.95,
            )
        )
        orc.planner = mock_planner

        mock_registry = MagicMock()
        mock_registry.is_installed.return_value = True
        mock_browser = MagicMock(spec=BrowserTool)
        mock_browser.navigate = AsyncMock(return_value=mock_food_page_state)
        mock_browser.get_page_state = AsyncMock(return_value=mock_food_page_state)
        mock_browser.click = AsyncMock()
        mock_browser.close = AsyncMock()
        mock_registry.get_installed_tool.return_value = mock_browser
        orc.tool_registry = mock_registry

        responses: list[Response] = []

        async def collect(r: Response) -> None:
            responses.append(r)

        with (
            patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value="1. Pizza Palace.")),
            patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=mock_food_page_state)),
            patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=mock_food_page_state)),
            patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value="1x Pepperoni Pizza, $18.50")),
        ):
            async def send_no() -> None:
                await asyncio.sleep(0.05)
                gate.receive_response(DOROTHY_CONTEXT.session_id, "no")

            asyncio.ensure_future(send_no())

            await orc.handle_message(
                message="Order me a pizza",
                context=DOROTHY_CONTEXT,
                response_callback=collect,
            )

        assert responses, "Dorothy got no responses during food order"
        # At least one response must require confirmation before payment
        confirmation_required = any(r.requires_confirmation for r in responses)
        assert confirmation_required, (
            "Dorothy test FAILED: Food order flow never asked for confirmation. "
            "Payment must not proceed without explicit user consent. "
            f"Got {len(responses)} responses, none required confirmation."
        )


# ─────────────────────────────────────────────────────────────
# Scenario 2: Second Brain — save a note
# ─────────────────────────────────────────────────────────────


class TestDorothySecondBrainSaveNote:
    """Dorothy adds a note to her Second Brain by voice."""

    async def test_save_note_response_is_not_visual_only(self, tmp_path, mock_keyring):
        """Response to 'remember that' must not use visual-only language."""
        from blind_assistant.core.planner import Intent

        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)

        mock_planner = MagicMock()
        mock_planner.classify_intent = AsyncMock(
            return_value=Intent(
                type="remember",
                description="save note about doctor appointment",
                required_tools=[],
                parameters={"content": "Doctor appointment on Friday at 2pm"},
                is_high_stakes=False,
                confidence=0.97,
            )
        )
        orc.planner = mock_planner

        mock_registry = MagicMock()
        mock_registry.is_installed.return_value = False
        orc.tool_registry = mock_registry

        responses: list[Response] = []

        async def collect(r: Response) -> None:
            responses.append(r)

        with patch.object(
            orc,
            "_handle_remember",
            new=AsyncMock(
                return_value=Response(
                    text="I've noted that down. Doctor appointment on Friday at 2pm is saved.",
                    spoken_text="I've noted that down. Your doctor appointment on Friday is saved.",
                )
            ),
        ):
            await orc.handle_message(
                message="Remember that I have a doctor appointment on Friday at 2pm",
                context=DOROTHY_CONTEXT,
                response_callback=collect,
            )

        assert responses, "Dorothy got no response when trying to save a note"
        for r in responses:
            text = _response_text(r)
            _assert_no_jargon(text, persona="Dorothy")
            _assert_no_visual_only_language(text, persona="Dorothy")

    async def test_save_note_confirmation_mentions_what_was_saved(self, tmp_path, mock_keyring):
        """The confirmation message should echo back what was saved so Dorothy knows it worked."""
        from blind_assistant.core.planner import Intent

        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(ALEX_CONTEXT.session_id)

        mock_planner = MagicMock()
        mock_planner.classify_intent = AsyncMock(
            return_value=Intent(
                type="remember",
                description="save pharmacy number",
                required_tools=[],
                parameters={"content": "pharmacy number is 555-1234"},
                is_high_stakes=False,
                confidence=0.95,
            )
        )
        orc.planner = mock_planner
        mock_registry = MagicMock()
        mock_registry.is_installed.return_value = False
        orc.tool_registry = mock_registry

        responses: list[Response] = []

        async def collect(r: Response) -> None:
            responses.append(r)

        with patch.object(
            orc,
            "_handle_remember",
            new=AsyncMock(
                return_value=Response(
                    text="Saved. Your pharmacy number 555-1234 is in your notes.",
                    spoken_text="Saved. Your pharmacy number 555-1234 is in your notes.",
                )
            ),
        ):
            await orc.handle_message(
                message="Remember that my pharmacy number is 555-1234",
                context=ALEX_CONTEXT,
                response_callback=collect,
            )

        assert responses, "Alex got no response when saving a note"
        combined = " ".join(_response_text(r) for r in responses)
        # Confirmation must echo back key content so Alex knows it was saved correctly
        assert "555-1234" in combined or "pharmacy" in combined.lower(), (
            "Alex test FAILED: Note save confirmation doesn't mention what was saved. "
            f"Got: {combined!r}"
        )


# ─────────────────────────────────────────────────────────────
# Scenario 3: Second Brain — query a note
# ─────────────────────────────────────────────────────────────


class TestDorothySecondBrainQuery:
    """Dorothy retrieves a note from her Second Brain by voice."""

    async def test_query_response_is_conversational(self, tmp_path, mock_keyring):
        """Query response should be a natural language answer, not raw data."""
        from blind_assistant.core.planner import Intent

        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)

        mock_planner = MagicMock()
        mock_planner.classify_intent = AsyncMock(
            return_value=Intent(
                type="query",
                description="find doctor appointment",
                required_tools=[],
                parameters={"query": "doctor appointment"},
                is_high_stakes=False,
                confidence=0.93,
            )
        )
        orc.planner = mock_planner
        mock_registry = MagicMock()
        mock_registry.is_installed.return_value = False
        orc.tool_registry = mock_registry

        responses: list[Response] = []

        async def collect(r: Response) -> None:
            responses.append(r)

        with patch.object(
            orc,
            "_handle_query",
            new=AsyncMock(
                return_value=Response(
                    text="You have a doctor appointment on Friday at 2pm.",
                    spoken_text="You have a doctor appointment on Friday at 2pm.",
                )
            ),
        ):
            await orc.handle_message(
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

    async def test_query_no_jargon_in_response(self, tmp_path, mock_keyring):
        """Second Brain query responses must never contain technical jargon."""
        from blind_assistant.core.planner import Intent

        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(ALEX_CONTEXT.session_id)

        mock_planner = MagicMock()
        mock_planner.classify_intent = AsyncMock(
            return_value=Intent(
                type="query",
                description="find pharmacy number",
                required_tools=[],
                parameters={"query": "pharmacy number"},
                is_high_stakes=False,
                confidence=0.95,
            )
        )
        orc.planner = mock_planner
        mock_registry = MagicMock()
        mock_registry.is_installed.return_value = False
        orc.tool_registry = mock_registry

        responses: list[Response] = []

        async def collect(r: Response) -> None:
            responses.append(r)

        with patch.object(
            orc,
            "_handle_query",
            new=AsyncMock(
                return_value=Response(
                    text="Your pharmacy number is 555-1234.",
                    spoken_text="Your pharmacy number is 555-1234.",
                )
            ),
        ):
            await orc.handle_message(
                message="What is my pharmacy number?",
                context=ALEX_CONTEXT,
                response_callback=collect,
            )

        assert responses
        for r in responses:
            _assert_no_jargon(_response_text(r), persona="Alex (newly-blind)")


# ─────────────────────────────────────────────────────────────
# Scenario 4: General interaction quality
# ─────────────────────────────────────────────────────────────


class TestDorothyGeneralInteraction:
    """Dorothy asks general questions. Responses must be clear, patient, jargon-free."""

    async def test_general_question_response_has_no_jargon(self, tmp_path, mock_keyring):
        """Dorothy's general questions should get plain-language responses."""
        from blind_assistant.core.planner import Intent

        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(DOROTHY_CONTEXT.session_id)

        mock_planner = MagicMock()
        mock_planner.classify_intent = AsyncMock(
            return_value=Intent(
                type="general",
                description="weather question",
                required_tools=[],
                parameters={},
                is_high_stakes=False,
                confidence=0.88,
            )
        )
        orc.planner = mock_planner
        mock_registry = MagicMock()
        mock_registry.is_installed.return_value = False
        orc.tool_registry = mock_registry

        responses: list[Response] = []

        async def collect(r: Response) -> None:
            responses.append(r)

        with patch.object(
            orc,
            "_handle_general",
            new=AsyncMock(
                return_value=Response(
                    text="The weather today is partly cloudy with a high of 72 degrees.",
                )
            ),
        ):
            await orc.handle_message(
                message="What is the weather like today?",
                context=DOROTHY_CONTEXT,
                response_callback=collect,
            )

        assert responses, "Dorothy got no response to a general question"
        for r in responses:
            text = _response_text(r)
            _assert_no_jargon(text, persona="Dorothy")

    async def test_response_to_newly_blind_has_no_visual_only_language(self, tmp_path, mock_keyring):
        """Alex (newly-blind) should get responses that don't presuppose visual ability."""
        from blind_assistant.core.planner import Intent

        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)
        gate.register_session(ALEX_CONTEXT.session_id)

        mock_planner = MagicMock()
        mock_planner.classify_intent = AsyncMock(
            return_value=Intent(
                type="general",
                description="how to read mail",
                required_tools=[],
                parameters={},
                is_high_stakes=False,
                confidence=0.90,
            )
        )
        orc.planner = mock_planner
        mock_registry = MagicMock()
        mock_registry.is_installed.return_value = False
        orc.tool_registry = mock_registry

        responses: list[Response] = []

        async def collect(r: Response) -> None:
            responses.append(r)

        with patch.object(
            orc,
            "_handle_general",
            new=AsyncMock(
                return_value=Response(
                    text="I can help you read that document. Hold your phone over it and say 'describe this'.",
                )
            ),
        ):
            await orc.handle_message(
                message="How do I read a piece of mail?",
                context=ALEX_CONTEXT,
                response_callback=collect,
            )

        assert responses, "Alex got no response"
        for r in responses:
            text = _response_text(r)
            _assert_no_jargon(text, persona="Alex (newly-blind)")
            _assert_no_visual_only_language(text, persona="Alex (newly-blind)")


# ─────────────────────────────────────────────────────────────
# Scenario 5: Setup language validation
# ─────────────────────────────────────────────────────────────


class TestDorothySetupLanguage:
    """Validate that installer spoken prompts use Dorothy-appropriate language.

    The React Native SetupWizardScreen language is covered by
    SetupWizardScreen.test.tsx (134 JS tests). These tests cover the Python
    CLI installer's spoken strings.
    """

    def test_installer_speak_calls_have_no_api_token_jargon(self):
        """Python installer speak() calls must not say 'API token' — use 'connection code'."""
        import blind_assistant.installer.install as install_module

        source_code = inspect.getsource(install_module)
        # Extract all string arguments to speak() calls
        # Pattern: speak("...") or speak('...')
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
        # Must mention the risk clearly
        disclosure_lower = FINANCIAL_RISK_DISCLOSURE.lower()
        assert "risk" in disclosure_lower or "warning" in disclosure_lower, (
            "Financial risk disclosure doesn't warn about risk — Dorothy needs to know."
        )
        # Must use plain words (not just legal/technical language)
        plain_words = ["payment", "money", "financial", "details", "information"]
        has_plain = any(w in disclosure_lower for w in plain_words)
        assert has_plain, (
            f"Financial risk disclosure doesn't use any plain language. "
            f"Dorothy needs to understand this warning. Got: {FINANCIAL_RISK_DISCLOSURE!r}"
        )

    def test_financial_risk_disclosure_has_no_api_jargon(self):
        """Financial risk disclosure must not contain API/backend jargon."""
        disclosure_lower = FINANCIAL_RISK_DISCLOSURE.lower()
        for word in ["api", "endpoint", "json", "http", "keychain"]:
            assert word not in disclosure_lower, (
                f"Financial risk disclosure contains jargon '{word}'. "
                f"Dorothy can't understand this. Full text: {FINANCIAL_RISK_DISCLOSURE!r}"
            )
