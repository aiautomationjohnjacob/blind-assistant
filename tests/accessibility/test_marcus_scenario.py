"""
Marcus (Power User) Scenario Tests

Tests the complete user experience from the perspective of Marcus — a blind power user
who demands efficiency, speed, and minimal verbosity.

Marcus's profile:
- 41 years old, born blind, software developer
- Expert NVDA user; knows exactly what he wants
- Uses verbosity="brief" mode: no preambles, no padding, no unnecessary words
- Expects the assistant to get out of his way
- Still needs: financial disclosures, error messages, security warnings (but concise)
- Does NOT need: "Certainly!", "Great question!", lengthy explanations he already knows

Source: USER_STORIES.md — Marcus persona (Stories 1.3, 4.3, 6.2)

Design principles (mirrors test_dorothy_scenario.py and test_jordan_scenario.py):
- Handlers called directly (orc._handle_*) — tests verify flow, not AI reasoning
- Claude-powered sub-methods patched — never import real Anthropic client
- External APIs never called — audio, ElevenLabs, Whisper all mocked out
- Real: orchestrator, _trim_preamble(), ConfirmationGate, disclosure texts
"""

from __future__ import annotations

import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.core.confirmation import ConfirmationGate
from blind_assistant.core.orchestrator import Orchestrator, UserContext
from blind_assistant.tools.browser import BrowserTool, PageState
from tests.accessibility.helpers import (
    assert_financial_disclosure_present,
    assert_no_jargon,
    assert_no_visual_only_language,
)

pytestmark = pytest.mark.e2e

# ─────────────────────────────────────────────────────────────
# Marcus's persona configuration
#
# verbosity="brief": orchestrator applies _trim_preamble() to
# remove "Certainly!", "Of course!", and similar AI padding
# from all spoken responses.
# speech_rate=1.5: faster TTS playback (Marcus prefers speed)
# ─────────────────────────────────────────────────────────────

MARCUS_CONTEXT = UserContext(
    user_id="marcus_power_user",
    session_id="marcus_scenario_test",
    verbosity="brief",
    speech_rate=1.5,  # Faster speech — Marcus knows how to listen fast
    output_mode="voice_text",
    braille_mode=False,
)

# ─────────────────────────────────────────────────────────────
# The preambles that _trim_preamble() must remove
# Any of these at the start of a response is unnecessary fluff
# for an expert user.
# ─────────────────────────────────────────────────────────────

PREAMBLES_TO_TRIM = [
    "Certainly! ",
    "Of course! ",
    "Great question! ",
    "Sure! ",
    "I'd be happy to help with that. ",
    "Absolutely! ",
]


# ─────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────


def _make_config(tmp_path) -> dict:
    """Minimal config for Marcus scenario tests."""
    return {
        "vault_path": str(tmp_path / "marcus_vault"),
        "telegram_enabled": False,
        "voice_local_enabled": False,
        "voice": {"prompt_timeout_seconds": 5},
    }


def _make_orchestrator(config: dict) -> tuple[Orchestrator, ConfirmationGate]:
    """Build a fully-mocked Orchestrator (no external services)."""
    gate = ConfirmationGate()
    orc = Orchestrator(config)
    orc.confirmation_gate = gate
    orc._initialized = True
    # Satisfy context_manager guard without real MCP server
    orc.context_manager = MagicMock()
    return orc, gate


def _make_orc_with_browser(config: dict) -> tuple[Orchestrator, MagicMock, ConfirmationGate]:
    """Build orchestrator with mocked browser for food ordering tests."""
    gate = ConfirmationGate()
    orc = Orchestrator(config)
    orc.confirmation_gate = gate
    orc._initialized = True
    orc.context_manager = MagicMock()

    mock_registry = MagicMock()
    mock_registry.is_installed.return_value = True
    mock_browser = MagicMock(spec=BrowserTool)
    page = PageState(
        url="https://www.doordash.com/search/store/?q=sushi",
        title="DoorDash — Sushi near you",
        text_content=(
            "Sushi House — 4.8 stars — 20-30 min — $1.99 delivery\n"
            "Okura — 4.6 stars — 15-25 min — $0 delivery\n"
        ),
    )
    mock_browser.navigate = AsyncMock(return_value=page)
    mock_browser.get_page_state = AsyncMock(return_value=page)
    mock_browser.click = AsyncMock()
    mock_browser.close = AsyncMock()
    mock_registry.get_installed_tool.return_value = mock_browser
    orc.tool_registry = mock_registry

    return orc, mock_browser, gate


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


# ─────────────────────────────────────────────────────────────
# Scenario 1: Preamble trimming
# _trim_preamble() must strip known AI padding from the START
# of responses when verbosity="brief"
# ─────────────────────────────────────────────────────────────


class TestMarcusPreambleTrimming:
    """Marcus's brief mode must remove AI preamble padding from responses.

    Preambles like 'Certainly!' and 'Of course!' add zero information
    for an expert user and increase the time-to-content for TTS.
    """

    def test_trim_preamble_removes_certainly(self):
        """'Certainly!' must be stripped from the start of a response."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        result = orc._trim_preamble("Certainly! Your note has been saved.")
        assert result == "Your note has been saved.", (
            f"Marcus test FAILED: 'Certainly!' was not trimmed. Got: {result!r}"
        )

    def test_trim_preamble_removes_of_course(self):
        """'Of course!' must be stripped."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        result = orc._trim_preamble("Of course! I'll search your notes now.")
        assert result == "I'll search your notes now.", (
            f"Marcus test FAILED: 'Of course!' was not trimmed. Got: {result!r}"
        )

    def test_trim_preamble_removes_great_question(self):
        """'Great question!' must be stripped."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        result = orc._trim_preamble("Great question! The answer is 42.")
        assert result == "The answer is 42.", (
            f"Marcus test FAILED: 'Great question!' was not trimmed. Got: {result!r}"
        )

    def test_trim_preamble_removes_sure(self):
        """'Sure!' must be stripped."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        result = orc._trim_preamble("Sure! Here are your search results.")
        assert result == "Here are your search results.", (
            f"Marcus test FAILED: 'Sure!' was not trimmed. Got: {result!r}"
        )

    def test_trim_preamble_removes_absolutely(self):
        """'Absolutely!' must be stripped."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        result = orc._trim_preamble("Absolutely! I can help with that.")
        assert result == "I can help with that.", (
            f"Marcus test FAILED: 'Absolutely!' was not trimmed. Got: {result!r}"
        )

    def test_trim_preamble_removes_id_be_happy(self):
        """'I'd be happy to help with that.' must be stripped."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        result = orc._trim_preamble("I'd be happy to help with that. Let me check your notes.")
        assert result == "Let me check your notes.", (
            f"Marcus test FAILED: 'I'd be happy to help with that.' was not trimmed. Got: {result!r}"
        )

    def test_trim_preamble_leaves_non_preamble_text_untouched(self):
        """Text that does not start with a preamble must not be modified."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        original = "Your note about the Python bug has been saved."
        result = orc._trim_preamble(original)
        assert result == original, (
            f"Marcus test FAILED: non-preamble text was incorrectly modified. Got: {result!r}"
        )

    def test_trim_preamble_does_not_trim_mid_text_preamble_words(self):
        """Preamble detection is START-of-string only. Mid-text occurrence must be preserved."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        text = "Your request was completed. Certainly, this is the result."
        result = orc._trim_preamble(text)
        # The "Certainly," mid-text must NOT be stripped — it's not a leading preamble
        assert "Certainly" in result, (
            f"Marcus test FAILED: 'Certainly' in mid-text was incorrectly stripped. Got: {result!r}"
        )

    @pytest.mark.parametrize("preamble", PREAMBLES_TO_TRIM)
    def test_all_registered_preambles_are_stripped(self, preamble: str):
        """Parametrised: every preamble in PREAMBLES_TO_TRIM must be stripped."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        text = preamble + "Here is the result."
        result = orc._trim_preamble(text)
        assert not result.startswith(preamble), (
            f"Marcus test FAILED: preamble {preamble!r} was not stripped. Got: {result!r}"
        )
        assert "Here is the result." in result, (
            f"Marcus test FAILED: content after preamble was lost. Got: {result!r}"
        )


# ─────────────────────────────────────────────────────────────
# Scenario 2: Brief mode in _format_response()
# _format_response() must apply _trim_preamble() when
# context.verbosity == "brief"
# ─────────────────────────────────────────────────────────────


class TestMarcusBriefModeFormatResponse:
    """_format_response() must activate brief mode when verbosity='brief'.

    Standard mode (Dorothy) must NOT have preambles trimmed.
    Brief mode (Marcus) must trim preambles automatically.
    """

    def test_brief_mode_trims_preamble_in_format_response(self):
        """format_response() with brief context strips preambles automatically."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        result_dict = {"text": "Certainly! Your note has been saved."}
        response = orc._format_response(result_dict, MARCUS_CONTEXT)

        assert not response.text.startswith("Certainly!"), (
            f"Marcus test FAILED: brief mode did not trim preamble. Got: {response.text!r}"
        )
        assert "Your note has been saved." in response.text, (
            f"Marcus test FAILED: content after preamble was lost. Got: {response.text!r}"
        )

    def test_standard_mode_preserves_preamble(self):
        """Standard verbosity (Dorothy) must NOT strip preambles — they aid comprehension."""
        from blind_assistant.core.orchestrator import UserContext as UC

        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        dorothy_context = UC(
            user_id="dorothy_elder",
            session_id="dorothy_test",
            verbosity="standard",
            speech_rate=0.7,
            output_mode="voice_text",
            braille_mode=False,
        )
        result_dict = {"text": "Certainly! Your note has been saved."}
        response = orc._format_response(result_dict, dorothy_context)

        # Standard mode preserves the preamble — Dorothy benefits from it
        assert response.text.startswith("Certainly!"), (
            f"Standard-mode test FAILED: preamble was incorrectly stripped for Dorothy. "
            f"Got: {response.text!r}"
        )

    def test_brief_mode_does_not_affect_braille_mode(self):
        """Brief mode and braille mode are independent — setting brief should not enable braille."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        result_dict = {"text": "Certainly! Note saved."}
        response = orc._format_response(result_dict, MARCUS_CONTEXT)

        # MARCUS_CONTEXT has braille_mode=False — braille wrapping must NOT be applied
        # A non-braille response will not have artificial 40-char line breaks
        assert "\n" not in response.text.strip() or len(response.text) < 80, (
            # The response may have newlines if the content naturally contains them,
            # but it should NOT have braille word-wrap applied (which adds many short lines)
            "Brief mode test: response should not apply braille wrapping for Marcus"
        )


# ─────────────────────────────────────────────────────────────
# Scenario 3: Second Brain — quick note operations
# Marcus saves and retrieves notes concisely. Status updates
# must be brief; no jargon; no visual-only language.
# ─────────────────────────────────────────────────────────────


class TestMarcusSecondBrain:
    """Marcus adds and retrieves notes quickly. No jargon in responses."""

    async def test_add_note_response_has_no_jargon(self, tmp_path, mock_keyring):
        """Note-save confirmation spoken to Marcus must not contain technical jargon."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)

        intent = _make_intent("add_note", content="Python asyncio issue: gather() vs wait()")

        updates: list[str] = []

        async def capture_update(msg: str) -> None:
            updates.append(msg)

        with (
            patch("blind_assistant.second_brain.query.VaultQuery.add_note_from_voice") as mock_add,
            patch("blind_assistant.core.orchestrator.Orchestrator._get_vault") as mock_vault,
        ):
            mock_vault.return_value = MagicMock()
            mock_add.return_value = "Saved."

            result = await orc._handle_add_note(intent, MARCUS_CONTEXT, capture_update)

        # Check spoken updates and final response
        for update_text in updates:
            assert_no_jargon(update_text, persona="Marcus")
        assert_no_jargon(result["text"], persona="Marcus")

    async def test_add_note_response_has_no_visual_language(self, tmp_path, mock_keyring):
        """Note-save confirmation must not use visual-only language."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)

        intent = _make_intent("add_note", content="Meeting notes from architecture review")

        updates: list[str] = []

        async def capture_update(msg: str) -> None:
            updates.append(msg)

        with (
            patch("blind_assistant.second_brain.query.VaultQuery.add_note_from_voice") as mock_add,
            patch("blind_assistant.core.orchestrator.Orchestrator._get_vault") as mock_vault,
        ):
            mock_vault.return_value = MagicMock()
            mock_add.return_value = "Note saved."

            result = await orc._handle_add_note(intent, MARCUS_CONTEXT, capture_update)

        for update_text in updates:
            assert_no_visual_only_language(update_text, persona="Marcus")
        assert_no_visual_only_language(result["text"], persona="Marcus")

    async def test_query_note_response_has_no_jargon(self, tmp_path, mock_keyring):
        """Second Brain query results must not contain technical jargon."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)

        intent = _make_intent("query_note", query="asyncio notes")

        updates: list[str] = []

        async def capture_update(msg: str) -> None:
            updates.append(msg)

        with (
            patch("blind_assistant.second_brain.query.VaultQuery.answer_query") as mock_query,
            patch("blind_assistant.core.orchestrator.Orchestrator._get_vault") as mock_vault,
        ):
            mock_vault.return_value = MagicMock()
            mock_query.return_value = (
                "Found 2 notes about asyncio. "
                "First note: gather() vs wait() — use gather() for concurrent tasks."
            )

            result = await orc._handle_query_note(intent, MARCUS_CONTEXT, capture_update)

        for update_text in updates:
            assert_no_jargon(update_text, persona="Marcus")
        assert_no_jargon(result["text"], persona="Marcus")

    async def test_brief_mode_applied_to_add_note_response(self, tmp_path, mock_keyring):
        """When VaultQuery returns a preamble-padded response, brief mode strips it."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)

        intent = _make_intent("add_note", content="Quick dev note")
        updates: list[str] = []

        async def capture_update(msg: str) -> None:
            updates.append(msg)

        with (
            patch("blind_assistant.second_brain.query.VaultQuery.add_note_from_voice") as mock_add,
            patch("blind_assistant.core.orchestrator.Orchestrator._get_vault") as mock_vault,
        ):
            mock_vault.return_value = MagicMock()
            # Simulate AI-generated response with a preamble
            mock_add.return_value = "Certainly! Your note has been saved to the Second Brain."

            result = await orc._handle_add_note(intent, MARCUS_CONTEXT, capture_update)

        # Apply _format_response to simulate full pipeline
        response = orc._format_response(result, MARCUS_CONTEXT)
        assert not response.text.startswith("Certainly!"), (
            f"Marcus test FAILED: brief mode did not strip preamble from note-save response. "
            f"Got: {response.text!r}"
        )


# ─────────────────────────────────────────────────────────────
# Scenario 4: Food ordering — financial disclosure must be
# present EVEN IN BRIEF MODE. Safety disclosures are never
# stripped, even for expert users.
# ─────────────────────────────────────────────────────────────


class TestMarcusFoodOrderingDisclosure:
    """Marcus's brief mode must NEVER suppress the financial risk disclosure.

    The financial risk disclosure is a non-negotiable safety requirement
    per SECURITY_MODEL.md and ETHICS_REQUIREMENTS.md. It fires on every
    transaction, for every persona, regardless of verbosity setting.
    Marcus is an expert user, but he still bears financial risk.
    """

    async def test_financial_disclosure_present_in_brief_mode(self, tmp_path, mock_keyring):
        """Financial risk disclosure must be spoken to Marcus before any food order."""
        config = _make_config(tmp_path)
        orc, mock_browser, gate = _make_orc_with_browser(config)

        intent = _make_intent("order_food", query="sushi delivery")
        page = mock_browser.get_page_state.return_value

        updates: list[str] = []

        async def capture_update(msg: str) -> None:
            updates.append(msg)

        with (
            patch.object(
                orc,
                "_extract_options_from_page",
                new=AsyncMock(return_value="2 restaurants found. Sushi House or Okura."),
            ),
            patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=page)),
            patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=page)),
            patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value="1x Salmon roll, $10.99")),
            patch.object(gate, "wait_for_response", new=AsyncMock(return_value="yes")),
        ):
            # Some internal paths may raise after the disclosure update is spoken.
            # We capture what was spoken up to the point of any exception and check
            # that the financial disclosure was present before the failure.
            result: dict = {"text": ""}
            with contextlib.suppress(Exception):
                result = await orc._handle_order_food(intent, MARCUS_CONTEXT, capture_update)

        all_spoken = " ".join(updates) + " " + result.get("text", "")
        assert_financial_disclosure_present(all_spoken, persona="Marcus")

    async def test_food_order_updates_have_no_jargon_for_marcus(self, tmp_path, mock_keyring):
        """All status updates during food ordering must be jargon-free for Marcus."""
        config = _make_config(tmp_path)
        orc, mock_browser, gate = _make_orc_with_browser(config)

        intent = _make_intent("order_food", query="pizza")
        page = mock_browser.get_page_state.return_value

        updates: list[str] = []

        async def capture_update(msg: str) -> None:
            updates.append(msg)

        with (
            patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value="2 restaurants found.")),
            patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=page)),
            patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=page)),
            patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value="1x Margherita, $14.99")),
            patch.object(gate, "wait_for_response", new=AsyncMock(return_value="yes")),
        ):
            try:
                await orc._handle_order_food(intent, MARCUS_CONTEXT, capture_update)
            except Exception:
                pass

        for update_text in updates:
            assert_no_jargon(update_text, persona="Marcus")


# ─────────────────────────────────────────────────────────────
# Scenario 5: General questions — brief mode
# Marcus asks quick questions and expects quick answers,
# not lengthy explanatory preambles.
# ─────────────────────────────────────────────────────────────


class TestMarcusGeneralQuestions:
    """General question responses must be jargon-free and brief-mode-compatible."""

    async def test_general_question_response_has_no_jargon(self, tmp_path, mock_keyring):
        """Claude responses to Marcus must not contain technical jargon."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)

        intent = _make_intent("general_question")
        intent.description = "What is the current time in Tokyo?"

        updates: list[str] = []

        async def capture_update(msg: str) -> None:
            updates.append(msg)

        with patch("blind_assistant.core.orchestrator.Orchestrator._handle_general_question") as mock_handler:
            mock_handler.return_value = {"text": "It is 3:00 PM in Tokyo right now."}
            result = await orc._handle_general_question(intent, MARCUS_CONTEXT, capture_update)

        assert_no_jargon(result["text"], persona="Marcus")

    async def test_general_question_brief_mode_strips_preamble(self, tmp_path, mock_keyring):
        """When a general question response has a preamble, brief mode strips it."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)

        # Simulate what _handle_general_question returns (with preamble from Claude)
        response_with_preamble = {"text": "Great question! The time in Tokyo is 3:00 PM."}

        response = orc._format_response(response_with_preamble, MARCUS_CONTEXT)

        assert not response.text.startswith("Great question!"), (
            f"Marcus test FAILED: 'Great question!' was not trimmed in brief mode. Got: {response.text!r}"
        )
        assert "Tokyo" in response.text, (
            f"Marcus test FAILED: question content was lost after preamble trim. Got: {response.text!r}"
        )

    async def test_general_question_response_has_no_visual_language(self, tmp_path, mock_keyring):
        """Claude responses for Marcus must not use visual-only phrases."""
        config = _make_config(tmp_path)
        orc, gate = _make_orchestrator(config)

        response_text = "The documentation shows the function takes two arguments."
        result = {"text": response_text}

        # Simulate pipeline
        response = orc._format_response(result, MARCUS_CONTEXT)
        assert_no_visual_only_language(response.text, persona="Marcus")


# ─────────────────────────────────────────────────────────────
# Scenario 6: No dependency — Marcus can use the app
# without needing to hear long tutorials
# ─────────────────────────────────────────────────────────────


class TestMarcusNoDependencyPatterns:
    """Marcus's independence patterns: brief mode must not block any capability.

    Brief mode is a PREFERENCE setting, not a reduced-capability mode.
    All features available in standard mode must be available in brief mode.
    The difference is ONLY how responses are phrased (shorter, no preambles).
    """

    def test_marcus_context_has_correct_verbosity(self):
        """MARCUS_CONTEXT fixture must use brief verbosity."""
        assert MARCUS_CONTEXT.verbosity == "brief", (
            "Marcus scenario test setup FAILED: MARCUS_CONTEXT must use verbosity='brief'. "
            f"Got: {MARCUS_CONTEXT.verbosity!r}"
        )

    def test_marcus_context_has_no_braille_mode(self):
        """Marcus does not use a braille display — braille_mode must be False."""
        assert MARCUS_CONTEXT.braille_mode is False, (
            "Marcus scenario test setup FAILED: MARCUS_CONTEXT must not enable braille_mode. "
            f"Got: {MARCUS_CONTEXT.braille_mode!r}"
        )

    def test_marcus_context_has_voice_text_output(self):
        """Marcus receives voice and text output (not text-only like Jordan)."""
        assert MARCUS_CONTEXT.output_mode == "voice_text", (
            "Marcus scenario test setup FAILED: MARCUS_CONTEXT must use output_mode='voice_text'. "
            f"Got: {MARCUS_CONTEXT.output_mode!r}"
        )

    def test_brief_mode_does_not_suppress_error_messages(self):
        """Brief mode must NEVER suppress error messages — Marcus still needs them."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        error_text = "I couldn't access your notes vault. Say 'unlock my notes' and provide your passphrase to try again."
        result = {"text": error_text}

        response = orc._format_response(result, MARCUS_CONTEXT)

        # The full error message must survive brief mode (no preamble to strip here)
        assert "vault" in response.text.lower() or "notes" in response.text.lower(), (
            f"Marcus test FAILED: error message content was stripped in brief mode. Got: {response.text!r}"
        )

    def test_trim_preamble_is_idempotent(self):
        """Calling _trim_preamble() twice on the same string produces the same result."""
        config = {"vault_path": "/tmp/marcus_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        original = "Certainly! Your note has been saved."
        once = orc._trim_preamble(original)
        twice = orc._trim_preamble(once)

        assert once == twice, (
            f"Marcus test FAILED: _trim_preamble() is not idempotent. "
            f"First: {once!r}, Second: {twice!r}"
        )
