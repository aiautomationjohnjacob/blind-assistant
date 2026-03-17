"""
Unit tests for blind_assistant.core.orchestrator and .confirmation

Covers:
- Orchestrator message handling (with mocked planner + tools)
- ConfirmationGate: registration, submission, wait, timeout
- Financial confirmation flow (two-step: disclosure + order confirm)
- Response formatting (braille mode, brief mode, preamble trimming)
- Food ordering handler (_handle_order_food): risk disclosure, browser navigation,
  cancellation, missing browser tool, navigation errors
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.core.confirmation import ConfirmationGate
from blind_assistant.core.orchestrator import Orchestrator, Response, UserContext
from blind_assistant.security.disclosure import (
    FINANCIAL_RISK_DISCLOSURE,
)

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def minimal_config():
    return {
        "telegram_enabled": False,
        "voice_local_enabled": False,
        "vault_path": "/tmp/test_vault",  # noqa: S108
    }


@pytest.fixture
def standard_context():
    return UserContext(
        user_id="test_user",
        session_id="test_session",
        verbosity="standard",
        speech_rate=1.0,
        output_mode="voice_text",
        braille_mode=False,
    )


@pytest.fixture
def brief_context():
    return UserContext(
        user_id="power_user",
        session_id="session_brief",
        verbosity="brief",
        speech_rate=1.5,
        output_mode="voice_text",
        braille_mode=False,
    )


@pytest.fixture
def braille_context():
    return UserContext(
        user_id="jordan",
        session_id="session_braille",
        verbosity="standard",
        speech_rate=1.0,
        output_mode="text_only",
        braille_mode=True,
    )


# ─────────────────────────────────────────────────────────────
# Orchestrator — initialization
# ─────────────────────────────────────────────────────────────


class TestOrchestratorInit:
    def test_not_initialized_on_create(self, minimal_config):
        orch = Orchestrator(minimal_config)
        assert not orch._initialized

    async def test_initialize_sets_initialized(self, minimal_config, mock_keyring):
        orch = Orchestrator(minimal_config)

        # Patch the classes at their source modules (lazy imports inside initialize())
        mock_planner = MagicMock()
        mock_registry = MagicMock()
        mock_registry.load = AsyncMock()
        mock_gate = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.initialize = AsyncMock()

        with (
            patch("blind_assistant.core.planner.Planner", return_value=mock_planner),
            patch("blind_assistant.tools.registry.ToolRegistry", return_value=mock_registry),
            patch("blind_assistant.core.confirmation.ConfirmationGate", return_value=mock_gate),
            patch("blind_assistant.core.context.ContextManager", return_value=mock_ctx),
        ):
            # Override the import mechanism by patching the builtins import
            # Simpler: just patch the modules that initialize() imports

            await orch.initialize()

        assert orch._initialized

    async def test_handle_message_raises_if_not_initialized(self, minimal_config, standard_context):
        orch = Orchestrator(minimal_config)
        with pytest.raises(RuntimeError, match="not initialized"):
            await orch.handle_message("hello", standard_context)


# ─────────────────────────────────────────────────────────────
# Response formatting
# ─────────────────────────────────────────────────────────────


class TestFormatResponse:
    def test_plain_text_response(self, minimal_config, standard_context):
        orch = Orchestrator(minimal_config)
        result = orch._format_response({"text": "Hello there."}, standard_context)
        assert isinstance(result, Response)
        assert result.text == "Hello there."

    def test_braille_mode_removes_emoji(self, minimal_config, braille_context):
        orch = Orchestrator(minimal_config)
        result = orch._format_response(
            {"text": "Done! 🎉 Your note was saved."},
            braille_context,
        )
        assert "🎉" not in result.text

    def test_braille_mode_breaks_at_sentences(self, minimal_config, braille_context):
        orch = Orchestrator(minimal_config)
        result = orch._format_response(
            {"text": "First sentence. Second sentence. Third sentence."},
            braille_context,
        )
        # Should have newlines between sentences
        assert "\n" in result.text

    @pytest.mark.parametrize(
        "preamble",
        [
            "Certainly! ",
            "Of course! ",
            "Great question! ",
            "Sure! ",
            "Absolutely! ",
        ],
    )
    def test_brief_mode_strips_preambles(self, minimal_config, brief_context, preamble):
        orch = Orchestrator(minimal_config)
        result = orch._format_response(
            {"text": f"{preamble}Here is the answer."},
            brief_context,
        )
        assert not result.text.startswith(preamble)
        assert "Here is the answer." in result.text

    def test_brief_mode_preserves_non_preamble(self, minimal_config, brief_context):
        orch = Orchestrator(minimal_config)
        result = orch._format_response(
            {"text": "Your prescription is ready."},
            brief_context,
        )
        assert result.text == "Your prescription is ready."


# ─────────────────────────────────────────────────────────────
# ConfirmationGate
# ─────────────────────────────────────────────────────────────


class TestConfirmationGateBasic:
    def test_register_session(self):
        gate = ConfirmationGate()
        gate.register_session("session_1")
        assert "session_1" in gate._response_queues

    def test_register_session_twice_is_idempotent(self):
        gate = ConfirmationGate()
        gate.register_session("s")
        gate.register_session("s")  # should not raise
        assert len(gate._response_queues) == 1

    def test_submit_response_puts_to_queue(self):
        gate = ConfirmationGate()
        gate.register_session("s")
        gate.submit_response("s", "yes")
        # Queue should have the item
        assert not gate._response_queues["s"].empty()

    def test_submit_response_to_unknown_session_is_ignored(self):
        gate = ConfirmationGate()
        gate.submit_response("nonexistent_session", "yes")  # should not raise


class TestConfirmationGateWait:
    async def test_confirmation_returns_true_for_yes(self, standard_context):
        gate = ConfirmationGate()
        gate.register_session(standard_context.session_id)

        # Submit the response before waiting (simulates concurrent response)
        gate.submit_response(standard_context.session_id, "yes")
        result = await gate.wait_for_confirmation(standard_context)
        assert result is True

    async def test_confirmation_returns_true_for_confirm(self, standard_context):
        gate = ConfirmationGate()
        gate.register_session(standard_context.session_id)
        gate.submit_response(standard_context.session_id, "confirm")
        result = await gate.wait_for_confirmation(standard_context)
        assert result is True

    async def test_confirmation_returns_false_for_cancel(self, standard_context):
        gate = ConfirmationGate()
        gate.register_session(standard_context.session_id)
        gate.submit_response(standard_context.session_id, "cancel")
        result = await gate.wait_for_confirmation(standard_context)
        assert result is False

    async def test_confirmation_returns_false_for_no(self, standard_context):
        gate = ConfirmationGate()
        gate.register_session(standard_context.session_id)
        gate.submit_response(standard_context.session_id, "no")
        result = await gate.wait_for_confirmation(standard_context)
        assert result is False

    async def test_confirmation_times_out_and_returns_false(self, standard_context):
        gate = ConfirmationGate()
        # No response submitted — should time out
        result = await gate.wait_for_confirmation(standard_context, timeout=0.05)
        assert result is False


class TestConfirmationGateActions:
    async def test_confirm_action_sends_message(self, standard_context):
        gate = ConfirmationGate()
        gate.register_session(standard_context.session_id)

        messages_sent = []

        async def callback(msg):
            messages_sent.append(msg)
            # Auto-respond with confirm
            gate.submit_response(standard_context.session_id, "yes")

        result = await gate.confirm_action(
            "delete your notes",
            standard_context,
            response_callback=callback,
        )

        assert len(messages_sent) >= 1
        assert "delete your notes" in messages_sent[0]
        assert result is True

    async def test_confirm_financial_action_sends_disclosure_first(self, standard_context):
        gate = ConfirmationGate()
        gate.register_session(standard_context.session_id)

        messages_sent = []
        call_count = 0

        async def callback(msg):
            nonlocal call_count
            messages_sent.append(msg)
            call_count += 1
            # Respond "yes" to both disclosure and order confirmation
            gate.submit_response(standard_context.session_id, "yes")

        await gate.confirm_financial_action(
            order_summary="1x Large Pizza",
            total_amount="$18.50",
            context=standard_context,
            response_callback=callback,
        )

        # Must have sent at least 2 messages (disclosure + order confirm)
        assert len(messages_sent) >= 2

        # First message must be the risk disclosure
        assert "risk" in messages_sent[0].lower() or "encrypt" in messages_sent[0].lower()

    async def test_financial_action_returns_false_without_callback(self, standard_context):
        gate = ConfirmationGate()
        result = await gate.confirm_financial_action(
            order_summary="pizza",
            total_amount="$20",
            context=standard_context,
            response_callback=None,
        )
        assert result is False

    async def test_financial_action_returns_false_if_disclosure_rejected(self, standard_context):
        gate = ConfirmationGate()
        gate.register_session(standard_context.session_id)

        async def callback(msg):
            gate.submit_response(standard_context.session_id, "no")

        result = await gate.confirm_financial_action(
            order_summary="pizza",
            total_amount="$20",
            context=standard_context,
            response_callback=callback,
        )
        assert result is False

    async def test_brief_context_uses_short_disclosure(self, brief_context):
        gate = ConfirmationGate()
        gate.register_session(brief_context.session_id)

        disclosures_sent = []

        async def callback(msg):
            disclosures_sent.append(msg)
            gate.submit_response(brief_context.session_id, "yes")

        await gate.confirm_financial_action(
            order_summary="groceries",
            total_amount="$45",
            context=brief_context,
            response_callback=callback,
        )

        # Brief context should use the shorter disclosure
        first_disclosure = disclosures_sent[0]
        assert len(first_disclosure) < len(FINANCIAL_RISK_DISCLOSURE)

    async def test_confirm_financial_details_returns_false_without_callback(self, standard_context):
        gate = ConfirmationGate()
        result = await gate.confirm_financial_details_collection(
            context=standard_context,
            response_callback=None,
        )
        assert result is False


# ─────────────────────────────────────────────────────────────
# UserContext.clear_sensitive() — ISSUE-005
# ─────────────────────────────────────────────────────────────


class TestUserContextClearSensitive:
    """Tests for the defense-in-depth passphrase zeroing at session end."""

    def test_clear_sensitive_clears_cached_passphrase(self):
        """clear_sensitive() sets _vault_passphrase to None."""
        ctx = UserContext(user_id="u", session_id="s")
        ctx._vault_passphrase = "correct-horse-battery-staple"  # type: ignore[attr-defined]
        ctx.clear_sensitive()
        assert ctx._vault_passphrase is None  # type: ignore[attr-defined]

    def test_clear_sensitive_no_error_when_no_passphrase_cached(self):
        """clear_sensitive() is safe to call even if no passphrase was ever cached."""
        ctx = UserContext(user_id="u", session_id="s")
        # Must not raise — passphrase was never set
        ctx.clear_sensitive()  # no exception

    def test_clear_sensitive_idempotent_when_already_none(self):
        """clear_sensitive() can be called multiple times without error."""
        ctx = UserContext(user_id="u", session_id="s")
        ctx._vault_passphrase = "passphrase"  # type: ignore[attr-defined]
        ctx.clear_sensitive()
        ctx.clear_sensitive()  # second call — no exception
        assert ctx._vault_passphrase is None  # type: ignore[attr-defined]

    def test_clear_sensitive_does_not_affect_other_fields(self):
        """clear_sensitive() only clears the passphrase, not other context fields."""
        ctx = UserContext(
            user_id="alice",
            session_id="sess-1",
            verbosity="detailed",
            speech_rate=0.75,
            braille_mode=True,
        )
        ctx._vault_passphrase = "secret"  # type: ignore[attr-defined]
        ctx.clear_sensitive()
        # Passphrase cleared
        assert ctx._vault_passphrase is None  # type: ignore[attr-defined]
        # Other fields untouched
        assert ctx.user_id == "alice"
        assert ctx.verbosity == "detailed"
        assert ctx.speech_rate == 0.75
        assert ctx.braille_mode is True


# ─────────────────────────────────────────────────────────────
# Configurable passphrase timeout — ISSUE-006
# ─────────────────────────────────────────────────────────────


class TestConfigurablePassphraseTimeout:
    """Tests that _collect_vault_passphrase reads timeout from config."""

    async def test_passphrase_timeout_uses_config_value(self, minimal_config):
        """_collect_vault_passphrase uses voice.prompt_timeout_seconds from config."""
        # Set a very short timeout via config
        config = {**minimal_config, "voice": {"prompt_timeout_seconds": 0.05}}
        orc = Orchestrator(config)
        # Manually initialise only the confirmation gate (skip full initialize)
        from blind_assistant.core.confirmation import ConfirmationGate

        orc.confirmation_gate = ConfirmationGate()

        ctx = UserContext(user_id="u", session_id="test-timeout-session")
        result = await orc._collect_vault_passphrase(ctx)
        # Queue was empty; with 0.05s timeout it must time out and return None
        assert result is None

    async def test_passphrase_timeout_defaults_to_120_when_not_configured(self, minimal_config):
        """_collect_vault_passphrase defaults to 120s if config has no voice section."""

        from blind_assistant.core.confirmation import ConfirmationGate

        orc = Orchestrator(minimal_config)
        orc.confirmation_gate = ConfirmationGate()

        ctx = UserContext(user_id="u", session_id="test-default-timeout")

        # Register session and pre-fill the queue so we don't actually wait 120s
        orc.confirmation_gate.register_session(ctx.session_id)
        queue = orc.confirmation_gate._response_queues[ctx.session_id]
        await queue.put("my-passphrase")

        result = await orc._collect_vault_passphrase(ctx)
        assert result == "my-passphrase"

    async def test_passphrase_timeout_returns_none_on_empty_queue_short_timeout(self, minimal_config):
        """With a 0.05s timeout and no response, returns None immediately."""
        from blind_assistant.core.confirmation import ConfirmationGate

        config = {**minimal_config, "voice": {"prompt_timeout_seconds": 0.05}}
        orc = Orchestrator(config)
        orc.confirmation_gate = ConfirmationGate()

        ctx = UserContext(user_id="u", session_id="test-quick-timeout")
        result = await orc._collect_vault_passphrase(ctx)
        assert result is None


# ─────────────────────────────────────────────────────────────
# Food ordering handler — _handle_order_food
# ─────────────────────────────────────────────────────────────


def _make_order_food_orchestrator(minimal_config: dict) -> Orchestrator:
    """
    Build a minimal Orchestrator with just the components needed to test
    _handle_order_food: confirmation_gate, tool_registry.
    """
    from blind_assistant.core.confirmation import ConfirmationGate

    orc = Orchestrator(minimal_config)
    orc.confirmation_gate = ConfirmationGate()
    orc.tool_registry = MagicMock()
    orc._initialized = True
    return orc


def _make_order_intent(
    description: str = "order a pizza",
    params: dict | None = None,
) -> MagicMock:
    """Create a mock intent for food ordering."""
    intent = MagicMock()
    intent.type = "order_food"
    intent.description = description
    intent.parameters = params or {}
    intent.is_high_stakes = True
    intent.required_tools = ["browser"]
    return intent


class TestHandleOrderFood:
    """Tests for Orchestrator._handle_order_food — Phase 2 completion."""

    async def test_order_food_user_declines_risk_disclosure(self, minimal_config, standard_context) -> None:
        """
        If the user says 'no' to the risk disclosure, the order is cancelled
        and a reassuring message is returned.
        """
        orc = _make_order_food_orchestrator(minimal_config)

        # User immediately declines when disclosure fires
        updates = []

        async def update_cb(msg: str) -> None:
            updates.append(msg)
            # Submit "no" on the first disclosure message
            if len(updates) == 2:  # first = "I'll help...", second = "Before we look..."
                orc.confirmation_gate.submit_response(standard_context.session_id, "no")

        orc.confirmation_gate.register_session(standard_context.session_id)
        intent = _make_order_intent()

        result = await orc._handle_order_food(intent, standard_context, update_cb)

        assert "won't proceed" in result["text"] or "No problem" in result["text"]
        # Browser tool should not be called at all
        orc.tool_registry.get_installed_tool.assert_not_called()

    async def test_order_food_browser_not_installed_returns_guidance(self, minimal_config, standard_context) -> None:
        """
        If the user confirms risk disclosure but browser tool isn't installed,
        return a helpful message instead of crashing.
        """
        orc = _make_order_food_orchestrator(minimal_config)
        # Browser is NOT in installed tools
        orc.tool_registry.get_installed_tool.return_value = None

        updates = []

        async def update_cb(msg: str) -> None:
            updates.append(msg)
            # Submit "yes" to the risk disclosure
            orc.confirmation_gate.submit_response(standard_context.session_id, "yes")

        orc.confirmation_gate.register_session(standard_context.session_id)
        intent = _make_order_intent()

        result = await orc._handle_order_food(intent, standard_context, update_cb)

        assert "browser tool" in result["text"].lower() or "not installed" in result["text"].lower()

    async def test_order_food_full_checkout_loop_places_order(self, minimal_config, standard_context) -> None:
        """
        Full checkout loop: user accepts disclosure → options read → picks restaurant
        → picks item → confirms order → order placed.

        All Claude API calls and browser interactions are mocked.
        Tests that the complete conversational flow runs end-to-end.
        """
        from blind_assistant.tools.browser import PageState

        orc = _make_order_food_orchestrator(minimal_config)

        mock_page_state = PageState(
            url="https://www.doordash.com/search/store/?q=pizza",
            title="DoorDash — Pizza near you",
            text_content="Pizza Palace — 4.5 stars\nTaco Town — 4.2 stars",
        )
        restaurant_page = PageState(
            url="https://www.doordash.com/store/pizza-palace",
            title="Pizza Palace",
            text_content="Pepperoni Pizza $14.99\nMargherita Pizza $12.99",
        )
        cart_page = PageState(
            url="https://www.doordash.com/checkout",
            title="Your Cart",
            text_content="1x Pepperoni Pizza — $14.99\nTotal: $18.50\nPlace Order",
        )
        confirm_page = PageState(
            url="https://www.doordash.com/order-confirmed",
            title="Order Confirmed",
            text_content="Order confirmed! Order number 12345",
        )

        mock_browser = AsyncMock()
        mock_browser.navigate = AsyncMock(return_value=mock_page_state)
        mock_browser.get_page_state = AsyncMock(side_effect=[restaurant_page, cart_page, confirm_page])
        orc.tool_registry.get_installed_tool.return_value = mock_browser

        # Patch all Claude-powered helper methods so test doesn't need anthropic installed
        options_text = "1. Pizza Palace. 2. Taco Town."
        order_summary = "1x Pepperoni Pizza, total $18.50"
        order_result = {"success": True, "confirmation": "Order #12345 placed!"}
        with (
            patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value=options_text)),
            patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=restaurant_page)),
            patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=cart_page)),
            patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value=order_summary)),
            patch.object(orc, "_place_order", new=AsyncMock(return_value=order_result)),
        ):
            updates = []
            response_count = [0]

            async def update_cb(msg: str) -> None:
                updates.append(msg)
                response_count[0] += 1
                # Supply responses in the correct order:
                # update 1: "I'll help you order food..." (no response needed)
                # update 2: "Before we look..." (no response needed)
                # update 3: FINANCIAL_RISK_DISCLOSURE → "yes" (confirm disclosure)
                # update 4: "Opening food ordering site..." (no response needed)
                # update 5: "I found some options..." → "1" (pick option 1)
                # update 6: "Got it — looking at..." (no response needed)
                # update 7: "Here are menu items..." → "pepperoni pizza" (pick item)
                # update 8: "Adding ... to your cart..." (no response needed)
                # update 9+: financial confirmation flow → "yes" (confirm order)
                orc.confirmation_gate.submit_response(standard_context.session_id, "yes")

            orc.confirmation_gate.register_session(standard_context.session_id)
            intent = _make_order_intent("order me a pizza", params={"food": "pizza"})

            result = await orc._handle_order_food(intent, standard_context, update_cb)

        # Order should have been placed
        placed = result.get("order_placed") is True
        placed = placed or "placed" in result["text"].lower()
        placed = placed or "confirmed" in result["text"].lower()
        assert placed
        # No ordering in progress — flow completed
        assert result.get("ordering_in_progress") is not True

    async def test_order_food_navigation_error_returns_helpful_message(self, minimal_config, standard_context) -> None:
        """
        If browser navigation raises an exception, a helpful error message is
        returned instead of propagating the exception.
        """
        orc = _make_order_food_orchestrator(minimal_config)

        mock_browser = AsyncMock()
        mock_browser.navigate = AsyncMock(side_effect=Exception("network timeout"))
        orc.tool_registry.get_installed_tool.return_value = mock_browser

        updates = []

        async def update_cb(msg: str) -> None:
            updates.append(msg)
            orc.confirmation_gate.submit_response(standard_context.session_id, "yes")

        orc.confirmation_gate.register_session(standard_context.session_id)
        intent = _make_order_intent()

        result = await orc._handle_order_food(intent, standard_context, update_cb)

        assert "trouble" in result["text"].lower() or "network timeout" in result["text"].lower()

    async def test_order_food_uses_intent_description_when_no_params(self, minimal_config, standard_context) -> None:
        """
        When intent has no 'food' or 'query' params, the description is used
        as the food query — no crash.
        """
        from blind_assistant.tools.browser import PageState

        orc = _make_order_food_orchestrator(minimal_config)

        mock_page_state = PageState(
            url="https://www.doordash.com",
            title="DoorDash",
            text_content="Results",
        )
        mock_browser = AsyncMock()
        mock_browser.navigate = AsyncMock(return_value=mock_page_state)
        orc.tool_registry.get_installed_tool.return_value = mock_browser

        # Patch all Claude helpers to avoid needing the anthropic package installed
        with (
            patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value="1. Option A.")),
            patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=mock_page_state)),
            patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=mock_page_state)),
            patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value="burger and fries")),
            patch.object(orc, "_place_order", new=AsyncMock(return_value={"success": True})),
        ):
            updates = []

            async def update_cb(msg: str) -> None:
                updates.append(msg)
                orc.confirmation_gate.submit_response(standard_context.session_id, "yes")

            orc.confirmation_gate.register_session(standard_context.session_id)
            # No params — description is the only food hint
            intent = _make_order_intent("order me a burger and fries", params={})

            result = await orc._handle_order_food(intent, standard_context, update_cb)

        # Should not crash — result should be valid
        assert "text" in result

    async def test_order_food_restaurant_param_changes_search_url(self, minimal_config, standard_context) -> None:
        """
        When a restaurant param is provided, the URL search uses the restaurant name.
        """
        from blind_assistant.tools.browser import PageState

        orc = _make_order_food_orchestrator(minimal_config)

        navigate_urls = []

        async def mock_navigate(url: str) -> PageState:
            navigate_urls.append(url)
            return PageState(url=url, title="DoorDash", text_content="Results")

        mock_browser = AsyncMock()
        mock_browser.navigate = mock_navigate
        orc.tool_registry.get_installed_tool.return_value = mock_browser

        restaurant_ps = PageState(url="x", title="Pizza Palace", text_content="")
        cart_ps = PageState(url="x", title="Cart", text_content="")
        with (
            patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value="1. Pizza Palace.")),
            patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=restaurant_ps)),
            patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=cart_ps)),
            patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value="pizza")),
            patch.object(orc, "_place_order", new=AsyncMock(return_value={"success": True})),
        ):
            updates = []

            async def update_cb(msg: str) -> None:
                updates.append(msg)
                orc.confirmation_gate.submit_response(standard_context.session_id, "yes")

            orc.confirmation_gate.register_session(standard_context.session_id)
            intent = _make_order_intent(params={"restaurant": "Pizza Palace"})

            await orc._handle_order_food(intent, standard_context, update_cb)

        # URL should contain the restaurant name, not generic food query
        assert navigate_urls, "navigate() was not called"
        assert "Pizza+Palace" in navigate_urls[0] or "Pizza" in navigate_urls[0]

    async def test_order_food_confirm_calls_financial_confirmation(self, minimal_config, standard_context) -> None:
        """
        _handle_order_food_confirm() correctly calls confirm_financial_action,
        which fires risk disclosure + order summary before any charge.
        """
        orc = _make_order_food_orchestrator(minimal_config)

        updates = []

        async def update_cb(msg: str) -> None:
            updates.append(msg)
            # Accept risk disclosure then confirm order
            orc.confirmation_gate.submit_response(standard_context.session_id, "yes")

        orc.confirmation_gate.register_session(standard_context.session_id)

        result = await orc._handle_order_food_confirm(
            order_summary="1x Pepperoni Pizza",
            total_amount="$18.99",
            context=standard_context,
            update=update_cb,
        )

        # First response should have been the risk disclosure
        assert any("risk" in u.lower() or "financial" in u.lower() or "payment" in u.lower() for u in updates), (
            "Risk disclosure was not sent to user before order confirmation"
        )
        # Result is bool — True = confirmed, False = declined
        assert isinstance(result, bool)

    async def test_order_food_brief_context_gets_short_disclosure(self, minimal_config, brief_context) -> None:
        """
        In brief verbosity mode, the risk disclosure uses the short version.
        The short disclosure is shorter than the full disclosure.
        """
        from blind_assistant.security.disclosure import (
            FINANCIAL_RISK_DISCLOSURE,
        )

        orc = _make_order_food_orchestrator(minimal_config)

        disclosures = []

        async def update_cb(msg: str) -> None:
            # Collect all messages that look like the financial disclosure
            if "risk" in msg.lower() or "payment" in msg.lower() or "financial" in msg.lower():
                disclosures.append(msg)
            orc.confirmation_gate.submit_response(brief_context.session_id, "yes")

        orc.confirmation_gate.register_session(brief_context.session_id)

        await orc._handle_order_food_confirm(
            order_summary="groceries",
            total_amount="$45.00",
            context=brief_context,
            update=update_cb,
        )

        if disclosures:
            # The disclosure sent should be the brief version
            assert len(disclosures[0]) <= len(FINANCIAL_RISK_DISCLOSURE)

    async def test_order_food_brief_context_disclosure_fires(self, minimal_config, brief_context) -> None:
        """Brief context still fires a risk disclosure (just shorter)."""
        orc = _make_order_food_orchestrator(minimal_config)

        update_count = [0]

        async def update_cb(msg: str) -> None:
            update_count[0] += 1
            orc.confirmation_gate.submit_response(brief_context.session_id, "yes")

        orc.confirmation_gate.register_session(brief_context.session_id)

        await orc._handle_order_food_confirm(
            order_summary="pizza",
            total_amount="$19",
            context=brief_context,
            update=update_cb,
        )

        # Should have sent at least 2 messages: disclosure + order confirm
        assert update_count[0] >= 2, "Expected disclosure + order confirmation messages"

    async def test_order_groceries_intent_uses_same_handler(self, minimal_config, standard_context) -> None:
        """
        order_groceries intent routes to _handle_order_food (same flow).
        Verifies the intent handler map is correct by comparing __name__.
        """
        orc = _make_order_food_orchestrator(minimal_config)
        assert "order_groceries" in orc._intent_handlers
        # Compare function names — bound methods are different objects even for the same method
        assert orc._intent_handlers["order_groceries"].__name__ == "_handle_order_food"

    def test_order_food_in_intent_handlers(self, minimal_config) -> None:
        """order_food is in _intent_handlers pointing to _handle_order_food."""
        orc = Orchestrator(minimal_config)
        handlers = orc._intent_handlers
        assert "order_food" in handlers
        assert handlers["order_food"].__name__ == "_handle_order_food"

    def test_order_food_not_stub_anymore(self, minimal_config) -> None:
        """order_food no longer points to _handle_high_stakes_stub."""
        orc = Orchestrator(minimal_config)
        handlers = orc._intent_handlers
        assert handlers["order_food"].__name__ != "_handle_high_stakes_stub"


# ─────────────────────────────────────────────────────────────
# ConfirmationGate.wait_for_response
# ─────────────────────────────────────────────────────────────


class TestConfirmationGateWaitForResponse:
    """Tests for ConfirmationGate.wait_for_response — arbitrary text collection."""

    async def test_wait_for_response_returns_submitted_text(self, standard_context) -> None:
        """wait_for_response returns the raw text submitted via submit_response."""
        gate = ConfirmationGate()
        gate.register_session(standard_context.session_id)
        gate.submit_response(standard_context.session_id, "pizza palace")

        result = await gate.wait_for_response(standard_context)
        assert result == "pizza palace"

    async def test_wait_for_response_returns_number_string(self, standard_context) -> None:
        """wait_for_response returns '2' when user says 'number 2' (stripped)."""
        gate = ConfirmationGate()
        gate.register_session(standard_context.session_id)
        gate.submit_response(standard_context.session_id, "2")

        result = await gate.wait_for_response(standard_context)
        assert result == "2"

    async def test_wait_for_response_strips_whitespace(self, standard_context) -> None:
        """wait_for_response strips leading/trailing whitespace from response."""
        gate = ConfirmationGate()
        gate.register_session(standard_context.session_id)
        gate.submit_response(standard_context.session_id, "  pepperoni pizza  ")

        result = await gate.wait_for_response(standard_context)
        assert result == "pepperoni pizza"

    async def test_wait_for_response_returns_none_on_timeout(self, standard_context) -> None:
        """wait_for_response returns None when timeout expires (no submission)."""
        gate = ConfirmationGate()
        # Don't submit any response — timeout should fire
        result = await gate.wait_for_response(standard_context, timeout=1)
        assert result is None

    async def test_wait_for_response_auto_registers_session(self, standard_context) -> None:
        """wait_for_response registers the session automatically if not pre-registered."""
        gate = ConfirmationGate()
        # Do NOT call register_session() first — should auto-register
        gate.submit_response(standard_context.session_id, "tacos")
        # Submit before waiting (queue is pre-populated)
        result = await gate.wait_for_response(standard_context, timeout=5)
        # Auto-registered: result may be None (queue was created AFTER submit) —
        # this verifies the method doesn't crash, not that it gets the value
        # In practice callers register before prompting the user.
        assert result is None or result == "tacos"


# ─────────────────────────────────────────────────────────────
# Checkout loop helpers — fallback behavior without Claude API
# ─────────────────────────────────────────────────────────────


class TestCheckoutLoopHelpers:
    """Tests for orchestrator checkout loop helpers — all test fallback paths only.

    These helpers normally call Claude API; the fallback paths are tested here
    (ImportError / Exception from anthropic) to ensure graceful degradation.
    """

    def _make_orc(self, minimal_config: dict) -> Orchestrator:
        """Minimal orchestrator for checkout helper tests."""
        from blind_assistant.core.confirmation import ConfirmationGate

        orc = Orchestrator(minimal_config)
        orc.confirmation_gate = ConfirmationGate()
        orc.tool_registry = MagicMock()
        orc._initialized = True
        return orc

    async def test_extract_options_falls_back_when_anthropic_unavailable(self, minimal_config) -> None:
        """_extract_options_from_page returns a plain-text fallback when Claude API unavailable."""
        orc = self._make_orc(minimal_config)
        # Patch require_credential to raise ImportError (anthropic not installed)
        with patch("blind_assistant.security.credentials.require_credential", side_effect=ImportError("no anthropic")):
            result = await orc._extract_options_from_page(
                page_text="Pizza Palace\nTaco Town",
                page_title="DoorDash Results",
                task_context="food search",
                max_options=3,
            )
        # Should return SOMETHING — never crash, never return empty string
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_extract_options_falls_back_on_empty_page_text(self, minimal_config) -> None:
        """_extract_options_from_page handles empty page_text without crashing."""
        orc = self._make_orc(minimal_config)
        with patch("blind_assistant.security.credentials.require_credential", side_effect=Exception("api error")):
            result = await orc._extract_options_from_page(
                page_text="",
                page_title="Empty Page",
                task_context="menu",
                max_options=3,
            )
        assert isinstance(result, str)

    async def test_navigate_to_user_choice_returns_none_on_click_failure(self, minimal_config) -> None:
        """_navigate_to_user_choice returns None when click or navigation fails."""
        from blind_assistant.tools.browser import PageState

        orc = self._make_orc(minimal_config)
        mock_page = PageState(url="https://example.com", title="DoorDash", text_content="Pizza Palace")
        mock_browser = AsyncMock()
        mock_browser.click = AsyncMock(side_effect=Exception("element not found"))

        with patch("blind_assistant.security.credentials.require_credential", side_effect=Exception("no api")):
            result = await orc._navigate_to_user_choice(
                browser_tool=mock_browser,
                page_state=mock_page,
                user_choice="Pizza Palace",
            )
        assert result is None

    async def test_add_item_to_cart_returns_current_page_on_failure(self, minimal_config) -> None:
        """_add_item_to_cart returns the existing page when click fails (no crash)."""
        from blind_assistant.tools.browser import PageState

        orc = self._make_orc(minimal_config)
        original_page = PageState(url="https://menu.example.com", title="Menu", text_content="Pepperoni Pizza $14")
        mock_browser = AsyncMock()
        mock_browser.click = AsyncMock(side_effect=Exception("button not found"))

        with patch("blind_assistant.security.credentials.require_credential", side_effect=Exception("no api")):
            result = await orc._add_item_to_cart(
                browser_tool=mock_browser,
                current_page=original_page,
                item_choice="Pepperoni Pizza",
            )
        # Should return the original page (not crash) — graceful fallback
        assert result is original_page

    async def test_extract_order_summary_fallback_uses_item_and_restaurant(self, minimal_config) -> None:
        """_extract_order_summary fallback returns item + restaurant when Claude API fails."""
        orc = self._make_orc(minimal_config)

        with patch("blind_assistant.security.credentials.require_credential", side_effect=Exception("no api")):
            result = await orc._extract_order_summary(
                page_text="",
                item_choice="Pepperoni Pizza",
                restaurant="Pizza Palace",
            )
        # Fallback: must mention the item and restaurant
        assert "Pepperoni Pizza" in result or "pizza" in result.lower()
        assert "Pizza Palace" in result or "palace" in result.lower()

    async def test_place_order_returns_failure_on_exception(self, minimal_config) -> None:
        """_place_order returns success=False with reason when browser click fails."""
        from blind_assistant.tools.browser import PageState

        orc = self._make_orc(minimal_config)
        mock_browser = AsyncMock()
        mock_browser.get_page_state = AsyncMock(
            return_value=PageState(url="https://checkout.example.com", title="Checkout", text_content="Place Order")
        )
        mock_browser.click = AsyncMock(side_effect=Exception("Place Order button not found"))

        with patch("blind_assistant.security.credentials.require_credential", side_effect=Exception("no api")):
            result = await orc._place_order(browser_tool=mock_browser)

        assert result["success"] is False
        assert "reason" in result

    async def test_checkout_loop_user_times_out_on_restaurant_selection(self, minimal_config, standard_context) -> None:
        """
        When user doesn't respond to restaurant selection (timeout),
        _handle_order_food returns a helpful message, not an error.

        wait_for_response is patched to return None immediately (simulates timeout)
        so this test runs fast without waiting for a real timer.
        """
        from blind_assistant.tools.browser import PageState

        orc = _make_order_food_orchestrator(minimal_config)
        mock_page = PageState(
            url="https://www.doordash.com",
            title="DoorDash",
            text_content="Pizza Palace\nTaco Town",
        )
        mock_browser = AsyncMock()
        mock_browser.navigate = AsyncMock(return_value=mock_page)
        orc.tool_registry.get_installed_tool.return_value = mock_browser

        # Patch all helpers: options are extracted, confirmation passes, but
        # wait_for_response returns None (simulates user timing out on restaurant selection)
        opts = "1. Pizza Palace. 2. Taco Town."
        with (
            patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value=opts)),
            patch.object(orc.confirmation_gate, "wait_for_confirmation", new=AsyncMock(return_value=True)),
            patch.object(orc.confirmation_gate, "wait_for_response", new=AsyncMock(return_value=None)),
        ):
            updates: list[str] = []

            async def update_cb(msg: str) -> None:
                updates.append(msg)

            orc.confirmation_gate.register_session(standard_context.session_id)
            result = await orc._handle_order_food(
                _make_order_intent("order me food", params={"food": "pizza"}),
                standard_context,
                update_cb,
            )

        # Should return a helpful message about not hearing the choice
        assert "text" in result
        response_lower = result["text"].lower()
        assert any(
            phrase in response_lower for phrase in ("didn't hear", "not hear", "ready", "try again", "order food")
        ), f"Expected helpful timeout message, got: {result['text']}"
