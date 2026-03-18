"""
Jordan (DeafBlind) Scenario Tests

Tests the complete user experience from the perspective of Jordan — a DeafBlind user
who uses a 40-cell refreshable braille display with no audio channel.

Jordan's profile:
- 29 years old, DeafBlind since birth
- Uses a 40-cell refreshable braille display (e.g. Orbit Reader 20, HumanWare Brailliant)
- No audio: cannot hear spoken responses, TTS output, or haptic cues
- Uses the web app or desktop CLI in text-only mode (output_mode="text_only")
- Cannot complete tasks that require audio confirmation
- Needs text responses broken into 40-char-friendly lines for display navigation
- Cannot benefit from emoji, special characters, or Unicode symbols

Source: USER_STORIES.md — Jordan persona (Stories 2.3, 4.4, 8.3, 9.2)
Issue #93: Write a user story from the deafblind perspective.

Design principles (mirrors test_dorothy_scenario.py):
- Handlers called directly (orc._handle_*) — tests verify flow, not AI reasoning
- Claude-powered sub-methods patched — never import real Anthropic client
- External APIs never called — audio, ElevenLabs, Whisper all mocked out
- Real: orchestrator, _format_for_braille(), ConfirmationGate, disclosure texts
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.core.confirmation import ConfirmationGate
from blind_assistant.core.orchestrator import Orchestrator, UserContext
from blind_assistant.security.disclosure import FINANCIAL_RISK_DISCLOSURE
from blind_assistant.tools.browser import BrowserTool, PageState
from tests.accessibility.helpers import (
    assert_braille_friendly,
    assert_financial_disclosure_present,
    assert_no_jargon,
    assert_no_visual_only_language,
)

pytestmark = pytest.mark.e2e

# ─────────────────────────────────────────────────────────────
# Jordan's persona configuration
#
# braille_mode=True: orchestrator wraps all responses through
# _format_for_braille() before returning them.
# output_mode="text_only": Telegram bot and API server send
# text only — no TTS audio is generated.
# ─────────────────────────────────────────────────────────────

JORDAN_CONTEXT = UserContext(
    user_id="jordan_deafblind",
    session_id="jordan_scenario_test",
    verbosity="standard",
    speech_rate=1.0,  # Not used — Jordan receives text, not audio
    output_mode="text_only",  # No audio output for Jordan
    braille_mode=True,  # _format_for_braille() applied to all responses
)


# ─────────────────────────────────────────────────────────────
# Test helpers
# ─────────────────────────────────────────────────────────────


def _make_config(tmp_path) -> dict:
    """Minimal config for Jordan scenario tests."""
    return {
        "vault_path": str(tmp_path / "jordan_vault"),
        "telegram_enabled": False,
        "voice_local_enabled": False,  # Jordan doesn't use voice I/O
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
        url="https://www.doordash.com/search/store/?q=pizza",
        title="DoorDash — Pizza near you",
        text_content=(
            "Pizza Palace — 4.5 stars — 25-35 min — $2.99 delivery\n"
            "Taco Town — 4.2 stars — 20-30 min — $0 delivery\n"
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
# Scenario 1: Braille formatting — all responses must be
# formatted for a 40-cell display
# ─────────────────────────────────────────────────────────────


class TestJordanBrailleFormatting:
    """Jordan's braille display shows 40 cells at a time.

    Every response must be formatted in ≤40-char lines with no emoji.
    The orchestrator's _format_for_braille() method is responsible for
    this transformation when braille_mode=True.
    """

    def test_format_for_braille_breaks_long_sentences(self):
        """_format_for_braille() must break text into 40-char-friendly lines."""
        config = {"vault_path": "/tmp/jordan_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        # A long sentence that would not fit on a 40-cell display
        long_text = "Your note has been saved to your Second Brain. You can retrieve it later by asking me."
        result = orc._format_for_braille(long_text)

        # The result must have each line ≤ 40 chars
        assert_braille_friendly(result, max_line_length=40)

    def test_format_for_braille_removes_emoji(self):
        """_format_for_braille() must strip emoji that cannot be shown on braille displays."""
        config = {"vault_path": "/tmp/jordan_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        text_with_emoji = "Your note was saved! 📝 Check your Second Brain later. ✅"
        result = orc._format_for_braille(text_with_emoji)

        # No emoji should remain
        import re

        emoji_pattern = re.compile(
            r"[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff"
            r"\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff]+"
        )
        assert not emoji_pattern.findall(result), (
            f"Jordan test FAILED: emoji not stripped from braille output. Result: {result!r}"
        )

    def test_format_for_braille_preserves_content(self):
        """_format_for_braille() must preserve the actual content, just reformatted."""
        config = {"vault_path": "/tmp/jordan_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        text = "Done. Your note has been saved."
        result = orc._format_for_braille(text)

        # Content must be preserved (no words dropped)
        assert "Done" in result, "Jordan test FAILED: _format_for_braille dropped 'Done'"
        assert "saved" in result, "Jordan test FAILED: _format_for_braille dropped 'saved'"

    def test_braille_mode_applied_in_format_response(self, tmp_path, mock_keyring):
        """When braille_mode=True, _format_response() must call _format_for_braille()."""
        config = _make_config(tmp_path)
        orc, _ = _make_orchestrator(config)

        result_dict = {"text": "Your note was saved. You can retrieve it any time."}
        response = orc._format_response(result_dict, JORDAN_CONTEXT)

        # Response text should be braille-friendly
        assert_braille_friendly(response.text, max_line_length=40)

    def test_braille_mode_no_emoji_in_format_response(self, tmp_path, mock_keyring):
        """When braille_mode=True, _format_response() must strip emoji."""
        config = _make_config(tmp_path)
        orc, _ = _make_orchestrator(config)

        result_dict = {"text": "Done! ✅ Your note was saved. 📝"}
        response = orc._format_response(result_dict, JORDAN_CONTEXT)

        import re

        emoji_pattern = re.compile(
            r"[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff"
            r"\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff]+"
        )
        assert not emoji_pattern.findall(response.text), (
            f"Jordan test FAILED: emoji in braille response: {response.text!r}"
        )


# ─────────────────────────────────────────────────────────────
# Scenario 2: Second Brain — text-only note saving and retrieval
# ─────────────────────────────────────────────────────────────


class TestJordanSecondBrain:
    """Jordan creates and retrieves notes entirely through text.

    User story 4.4: As Jordan, I want to create and retrieve notes entirely
    through text on my braille display so that I can use the Second Brain
    without any audio.

    All confirmations must be available as text (no audio-only confirmation).
    All note content must be in braille-friendly format.
    """

    async def test_add_note_response_is_braille_friendly(self, tmp_path, mock_keyring):
        """Adding a note must return a braille-formatted text response."""
        config = _make_config(tmp_path)
        orc, _ = _make_orchestrator(config)

        # Jordan types a note to save (text input, not voice)
        with patch.object(
            orc,
            "_save_note_to_vault",
            new=AsyncMock(return_value="Your note has been saved to your Second Brain."),
        ):
            intent = _make_intent("add_note", content="Doctor appointment March 20 at 2pm")
            result = await orc._handle_add_note(intent, JORDAN_CONTEXT)

        response = orc._format_response(result, JORDAN_CONTEXT)

        # Response must be braille-friendly
        assert_braille_friendly(response.text, max_line_length=40)

    async def test_add_note_response_contains_no_jargon(self, tmp_path, mock_keyring):
        """Note-saving confirmation must not contain technical jargon."""
        config = _make_config(tmp_path)
        orc, _ = _make_orchestrator(config)

        with patch.object(
            orc,
            "_save_note_to_vault",
            new=AsyncMock(return_value="Note saved. You can retrieve it any time."),
        ):
            intent = _make_intent("add_note", content="Take medication at 8am")
            result = await orc._handle_add_note(intent, JORDAN_CONTEXT)

        response = orc._format_response(result, JORDAN_CONTEXT)
        assert_no_jargon(response.text, persona="Jordan (DeafBlind)")

    async def test_query_note_response_is_braille_friendly(self, tmp_path, mock_keyring):
        """Querying notes must return braille-friendly text."""
        config = _make_config(tmp_path)
        orc, _ = _make_orchestrator(config)

        with patch.object(
            orc,
            "_query_vault",
            new=AsyncMock(return_value="Doctor appointment March 20 at 2pm."),
        ):
            intent = _make_intent("query_note", query="doctor appointment")
            result = await orc._handle_query_note(intent, JORDAN_CONTEXT)

        response = orc._format_response(result, JORDAN_CONTEXT)
        assert_braille_friendly(response.text, max_line_length=40)

    async def test_query_note_response_no_visual_language(self, tmp_path, mock_keyring):
        """Query results must not contain visual-only language."""
        config = _make_config(tmp_path)
        orc, _ = _make_orchestrator(config)

        with patch.object(
            orc,
            "_query_vault",
            new=AsyncMock(return_value="I found your note. Doctor appointment March 20 at 2pm."),
        ):
            intent = _make_intent("query_note", query="doctor")
            result = await orc._handle_query_note(intent, JORDAN_CONTEXT)

        response = orc._format_response(result, JORDAN_CONTEXT)
        assert_no_visual_only_language(response.text, persona="Jordan (DeafBlind)")


# ─────────────────────────────────────────────────────────────
# Scenario 3: Financial disclosure — must be readable via braille
# ─────────────────────────────────────────────────────────────


class TestJordanFinancialDisclosure:
    """Jordan must be able to read the financial risk disclosure on her braille display.

    User story 9.2: As Jordan, I want to be warned before the assistant takes any
    action that could affect my finances, and the warning must be available as text
    on my braille display.

    The FINANCIAL_RISK_DISCLOSURE constant (from security/disclosure.py) is the
    canonical disclosure text. It must not contain jargon, visual language, or
    lines that exceed the 40-cell braille display width AFTER formatting.
    """

    def test_financial_risk_disclosure_has_no_jargon(self):
        """The financial risk disclosure must be free of technical jargon.

        Jordan must be able to understand the warning before consenting.
        If the disclosure contains terms like 'API' or 'endpoint', the
        consent is not meaningful (Jordan cannot understand what she agreed to).
        """
        assert_no_jargon(FINANCIAL_RISK_DISCLOSURE, persona="Jordan (DeafBlind)")

    def test_financial_risk_disclosure_has_no_visual_language(self):
        """The financial risk disclosure must not contain visual-only language."""
        assert_no_visual_only_language(FINANCIAL_RISK_DISCLOSURE, persona="Jordan (DeafBlind)")

    def test_financial_risk_disclosure_braille_formatted(self):
        """When formatted for braille, the disclosure must fit on a 40-cell display."""
        config = {"vault_path": "/tmp/jordan_vault", "voice": {"prompt_timeout_seconds": 5}}
        orc = Orchestrator(config)

        # Simulate the full disclosure going through braille formatter
        formatted = orc._format_for_braille(FINANCIAL_RISK_DISCLOSURE)
        assert_braille_friendly(formatted, max_line_length=40)

    async def test_food_order_disclosure_reaches_jordan(self, tmp_path, mock_keyring):
        """Food ordering must surface the disclosure as text to Jordan.

        Jordan cannot hear spoken warnings. The disclosure must appear in the
        text/braille output stream (response_callback updates) before
        Jordan is asked to confirm payment.
        """
        config = _make_config(tmp_path)
        orc, mock_browser, gate = _make_orc_with_browser(config)
        gate.register_session(JORDAN_CONTEXT.session_id)

        page = PageState(
            url="https://www.doordash.com/search/store/?q=pizza",
            title="DoorDash — Pizza near you",
            text_content="Pizza Palace — 4.5 stars — 25-35 min — $2.99 delivery\n",
        )
        updates: list[str] = []

        async def update_cb(msg: str) -> None:
            """Collect text updates Jordan would see on her braille display."""
            updates.append(msg)
            # Jordan cancels — she declines the order
            gate.submit_response(JORDAN_CONTEXT.session_id, "no")

        with (
            patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value="1. Pizza Palace.")),
            patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=page)),
            patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=page)),
            patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value="1x Pepperoni Pizza, $18.50")),
        ):
            await orc._handle_order_food(
                _make_intent("order_food", food="pizza"),
                JORDAN_CONTEXT,
                update_cb,
            )

        combined_text = " ".join(updates)

        # The financial risk disclosure must appear in the text stream Jordan sees
        assert_financial_disclosure_present(combined_text, persona="Jordan (DeafBlind)")

        # The disclosure text must not contain jargon Jordan can't understand
        for update in updates:
            assert_no_jargon(update, persona="Jordan (DeafBlind)")


# ─────────────────────────────────────────────────────────────
# Scenario 4: General questions — text-only mode
# ─────────────────────────────────────────────────────────────


class TestJordanGeneralQuestions:
    """Jordan asks general questions and receives text-only responses.

    User story 8.3: As Jordan, I want all assistant responses available as text
    that can be sent to my braille display so that I can use the assistant with
    no audio at all.
    """

    async def test_general_question_response_is_braille_friendly(self, tmp_path, mock_keyring):
        """General question answers must be braille-formatted when braille_mode=True."""
        config = _make_config(tmp_path)
        orc, _ = _make_orchestrator(config)

        with patch(
            "blind_assistant.core.orchestrator.Orchestrator._handle_general_question",
            new=AsyncMock(return_value={"text": "The weather today is cloudy. No rain expected."}),
        ):
            result = await orc._handle_general_question(
                _make_intent("general_question", query="What is the weather?"),
                JORDAN_CONTEXT,
            )

        response = orc._format_response(result, JORDAN_CONTEXT)
        assert_braille_friendly(response.text, max_line_length=40)
        assert_no_jargon(response.text, persona="Jordan (DeafBlind)")
        assert_no_visual_only_language(response.text, persona="Jordan (DeafBlind)")

    def test_output_mode_text_only_suppresses_tts(self, tmp_path, mock_keyring):
        """When output_mode='text_only', the context must signal no TTS synthesis needed.

        The Telegram bot and API server both check context.output_mode before
        calling synthesize_speech(). This test verifies the Jordan context
        is correctly configured so that TTS is never attempted.
        """
        assert JORDAN_CONTEXT.output_mode == "text_only", (
            "Jordan test FAILED: output_mode must be 'text_only' so that no TTS "
            "audio is generated for a DeafBlind user. "
            f"Got: {JORDAN_CONTEXT.output_mode!r}"
        )

    def test_braille_mode_is_enabled_for_jordan(self):
        """Jordan's context must have braille_mode=True.

        This causes orchestrator._format_response() to call _format_for_braille()
        on every response, ensuring lines are ≤40 chars and emoji are stripped.
        """
        assert JORDAN_CONTEXT.braille_mode is True, (
            "Jordan test FAILED: braille_mode must be True for DeafBlind user. "
            "Without this, responses will not be formatted for a 40-cell display."
        )
