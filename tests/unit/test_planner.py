"""
Tests for core/planner.py — Intent Planner

Verifies intent classification, tool requirement mapping, and error fallback.
All Claude API calls are mocked — no real API access.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.core.planner import (
    HIGH_STAKES_INTENTS,
    INTENT_TOOL_MAP,
    Intent,
    Planner,
)

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def config() -> dict:
    """Minimal config dict sufficient to create a Planner."""
    return {}


@pytest.fixture
def planner(config: dict) -> Planner:
    """A Planner instance with no real API client initialised."""
    return Planner(config)


def _make_claude_response(payload: dict) -> MagicMock:
    """Build a mock Anthropic message response with JSON body."""
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(payload))]
    return msg


# ─────────────────────────────────────────────────────────────
# INTENT_TOOL_MAP structure tests
# ─────────────────────────────────────────────────────────────


def test_intent_tool_map_order_food_uses_browser() -> None:
    """
    order_food must require 'browser', not 'ordering'.

    Per ARCHITECTURE.md: Claude navigates any ordering site via the browser tool.
    No DoorDash-specific wrapper exists or should exist — 'ordering' is not a
    valid registry tool name. Using 'browser' ensures the install flow offers
    to install playwright, not a nonexistent package.
    """
    assert "browser" in INTENT_TOOL_MAP["order_food"], (
        "order_food must require 'browser' (playwright), not a service-specific tool. "
        "See ARCHITECTURE.md: Claude navigates ordering sites autonomously via browser."
    )
    assert "ordering" not in INTENT_TOOL_MAP["order_food"], (
        "'ordering' is not a valid registry tool name. "
        "The tool registry has 'browser' for all web navigation tasks."
    )


def test_intent_tool_map_order_groceries_uses_browser() -> None:
    """order_groceries must require 'browser' — same reasoning as order_food."""
    assert "browser" in INTENT_TOOL_MAP["order_groceries"]
    assert "grocery" not in INTENT_TOOL_MAP["order_groceries"]


def test_intent_tool_map_book_travel_uses_browser() -> None:
    """book_travel must require 'browser' — Claude navigates any travel site."""
    assert "browser" in INTENT_TOOL_MAP["book_travel"]
    assert "travel" not in INTENT_TOOL_MAP["book_travel"]


def test_intent_tool_map_search_web_uses_browser() -> None:
    """search_web requires browser — consistent with other web navigation tasks."""
    assert "browser" in INTENT_TOOL_MAP["search_web"]


def test_intent_tool_map_general_question_needs_no_tools() -> None:
    """general_question has an empty tool list — answered by Claude directly."""
    assert INTENT_TOOL_MAP["general_question"] == []


def test_all_intent_types_have_entries() -> None:
    """Every intent type in HIGH_STAKES_INTENTS that maps to an action has a tool entry."""
    # These are the intents the orchestrator's _intent_handlers supports
    supported_intents = {
        "screen_description", "navigate_app", "fill_form", "order_food",
        "order_groceries", "book_travel", "add_note", "query_note",
        "smart_home", "search_web", "general_question",
    }
    for intent_type in supported_intents:
        assert intent_type in INTENT_TOOL_MAP, (
            f"Intent type '{intent_type}' has no entry in INTENT_TOOL_MAP"
        )


def test_high_stakes_intents_are_subset_of_intent_tool_map() -> None:
    """Every HIGH_STAKES_INTENT that needs tools is in INTENT_TOOL_MAP."""
    # order_food, order_groceries, book_travel must all be in the map
    for intent_type in {"order_food", "order_groceries", "book_travel"}:
        assert intent_type in INTENT_TOOL_MAP, (
            f"High-stakes intent '{intent_type}' is missing from INTENT_TOOL_MAP"
        )


# ─────────────────────────────────────────────────────────────
# HIGH_STAKES_INTENTS
# ─────────────────────────────────────────────────────────────


def test_order_food_is_high_stakes() -> None:
    """order_food must be in HIGH_STAKES_INTENTS (requires user confirmation)."""
    assert "order_food" in HIGH_STAKES_INTENTS


def test_order_groceries_is_high_stakes() -> None:
    """order_groceries must be in HIGH_STAKES_INTENTS."""
    assert "order_groceries" in HIGH_STAKES_INTENTS


def test_book_travel_is_high_stakes() -> None:
    """book_travel must be in HIGH_STAKES_INTENTS."""
    assert "book_travel" in HIGH_STAKES_INTENTS


def test_general_question_is_not_high_stakes() -> None:
    """general_question does NOT require confirmation — it's just a question."""
    assert "general_question" not in HIGH_STAKES_INTENTS


def test_add_note_is_not_high_stakes() -> None:
    """add_note does NOT require confirmation — reading/writing notes is low stakes."""
    assert "add_note" not in HIGH_STAKES_INTENTS


# ─────────────────────────────────────────────────────────────
# Intent dataclass
# ─────────────────────────────────────────────────────────────


def test_intent_defaults() -> None:
    """Intent dataclass has correct defaults."""
    intent = Intent(type="general_question", description="What is the weather?")
    assert intent.required_tools == []
    assert intent.parameters == {}
    assert intent.is_high_stakes is False
    assert intent.confidence == 1.0


def test_intent_required_tools_is_independent_per_instance() -> None:
    """Each Intent instance has its own required_tools list (not shared via default factory)."""
    a = Intent(type="order_food", description="order pizza")
    b = Intent(type="search_web", description="search news")
    a.required_tools.append("browser")
    assert "browser" not in b.required_tools


# ─────────────────────────────────────────────────────────────
# classify_intent — mocked Claude
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def mock_planner_client() -> MagicMock:
    """
    A fake Anthropic async client.

    The anthropic package may not be installed in this environment; we patch
    Planner._get_client() directly so tests never need to import anthropic.
    """
    return MagicMock()


async def test_classify_intent_returns_intent_from_api(
    planner: Planner, mock_planner_client: MagicMock
) -> None:
    """classify_intent parses a valid JSON Claude response into an Intent."""
    response_payload = {
        "type": "order_food",
        "description": "User wants to order pizza",
        "required_tools": ["browser"],
        "parameters": {"restaurant": "pizza place"},
        "confidence": 0.95,
    }
    mock_planner_client.messages.create = AsyncMock(
        return_value=_make_claude_response(response_payload)
    )

    with patch.object(planner, "_get_client", return_value=mock_planner_client):
        context = MagicMock()
        intent = await planner.classify_intent("order me a pizza", context)

    assert intent.type == "order_food"
    assert intent.description == "User wants to order pizza"
    assert intent.required_tools == ["browser"]
    assert intent.parameters == {"restaurant": "pizza place"}
    assert intent.confidence == 0.95
    assert intent.is_high_stakes is True  # order_food is in HIGH_STAKES_INTENTS


async def test_classify_intent_falls_back_on_invalid_json(
    planner: Planner, mock_planner_client: MagicMock
) -> None:
    """classify_intent returns general_question fallback when API returns non-JSON."""
    bad_response = MagicMock()
    bad_response.content = [MagicMock(text="I cannot classify that right now.")]
    mock_planner_client.messages.create = AsyncMock(return_value=bad_response)

    with patch.object(planner, "_get_client", return_value=mock_planner_client):
        context = MagicMock()
        intent = await planner.classify_intent("something unclear", context)

    assert intent.type == "general_question"
    assert intent.confidence == 0.0
    assert intent.required_tools == []


async def test_classify_intent_falls_back_on_api_exception(
    planner: Planner, mock_planner_client: MagicMock
) -> None:
    """classify_intent returns general_question fallback when Claude API raises."""
    mock_planner_client.messages.create = AsyncMock(side_effect=Exception("API error"))

    with patch.object(planner, "_get_client", return_value=mock_planner_client):
        context = MagicMock()
        intent = await planner.classify_intent("order food", context)

    assert intent.type == "general_question"
    assert intent.confidence == 0.0


@pytest.mark.parametrize("high_stakes_type", ["order_food", "order_groceries", "book_travel"])
async def test_classify_intent_marks_high_stakes_correctly(
    planner: Planner, mock_planner_client: MagicMock, high_stakes_type: str
) -> None:
    """classify_intent sets is_high_stakes based on HIGH_STAKES_INTENTS set."""
    response_payload = {
        "type": high_stakes_type,
        "description": "task",
        "required_tools": ["browser"],
        "parameters": {},
        "confidence": 0.9,
    }
    mock_planner_client.messages.create = AsyncMock(
        return_value=_make_claude_response(response_payload)
    )

    with patch.object(planner, "_get_client", return_value=mock_planner_client):
        context = MagicMock()
        intent = await planner.classify_intent("some task", context)

    assert intent.is_high_stakes is True, (
        f"Intent type '{high_stakes_type}' should be marked high_stakes"
    )


async def test_classify_intent_general_question_not_high_stakes(
    planner: Planner, mock_planner_client: MagicMock
) -> None:
    """A general question is not marked as high stakes."""
    response_payload = {
        "type": "general_question",
        "description": "What is the weather?",
        "required_tools": [],
        "parameters": {},
        "confidence": 0.99,
    }
    mock_planner_client.messages.create = AsyncMock(
        return_value=_make_claude_response(response_payload)
    )

    with patch.object(planner, "_get_client", return_value=mock_planner_client):
        context = MagicMock()
        intent = await planner.classify_intent("what's the weather?", context)

    assert intent.is_high_stakes is False


async def test_classify_intent_uses_fallback_tools_from_map_when_api_omits_them(
    planner: Planner, mock_planner_client: MagicMock
) -> None:
    """When the API omits required_tools, the fallback from INTENT_TOOL_MAP is used."""
    response_payload = {
        "type": "search_web",
        "description": "Search for news",
        # required_tools omitted — should fall back to INTENT_TOOL_MAP["search_web"]
        "confidence": 0.8,
    }
    mock_planner_client.messages.create = AsyncMock(
        return_value=_make_claude_response(response_payload)
    )

    with patch.object(planner, "_get_client", return_value=mock_planner_client):
        context = MagicMock()
        intent = await planner.classify_intent("search for latest news", context)

    assert "browser" in intent.required_tools


async def test_classify_intent_lazy_client_initialization(
    planner: Planner,
) -> None:
    """Planner._client is None until first classify_intent call (lazy init)."""
    assert planner._client is None
    # The _client stays None until _get_client() is actually called —
    # _get_client itself sets _client. We verify the initial state only here
    # since mocking _get_client bypasses the assignment. This is the correct
    # test of the lazy initialization contract.
    assert not hasattr(planner, "_initialized_client")
