"""
Unit tests for blind_assistant.core.orchestrator and .confirmation

Covers:
- Orchestrator message handling (with mocked planner + tools)
- ConfirmationGate: registration, submission, wait, timeout
- Financial confirmation flow (two-step: disclosure + order confirm)
- Response formatting (braille mode, brief mode, preamble trimming)
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
        "vault_path": "/tmp/test_vault",
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

        with patch("blind_assistant.core.planner.Planner", return_value=mock_planner), \
             patch("blind_assistant.tools.registry.ToolRegistry", return_value=mock_registry), \
             patch("blind_assistant.core.confirmation.ConfirmationGate", return_value=mock_gate), \
             patch("blind_assistant.core.context.ContextManager", return_value=mock_ctx):
            # Override the import mechanism by patching the builtins import
            # Simpler: just patch the modules that initialize() imports

            await orch.initialize()

        assert orch._initialized

    async def test_handle_message_raises_if_not_initialized(
        self, minimal_config, standard_context
    ):
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

    @pytest.mark.parametrize("preamble", [
        "Certainly! ",
        "Of course! ",
        "Great question! ",
        "Sure! ",
        "Absolutely! ",
    ])
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
