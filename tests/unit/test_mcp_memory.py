"""
Unit tests for MCPMemoryClient and ContextManager (MCP integration).

Tests cover:
- Local fallback behavior when MCP is unavailable
- MCP-connected read/write paths
- Default preference merging
- Entity name formatting
- Observation parsing
- Error resilience (MCP errors should not raise to callers)
- Context manager integration with MCPMemoryClient
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from blind_assistant.memory.mcp_memory import (
    DEFAULT_PREFERENCES,
    PREF_BRAILLE_MODE,
    PREF_VERBOSITY,
    PREF_VOICE_SPEED,
    MCPMemoryClient,
)

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────


def _make_mcp_result(observations: list[str]) -> dict:
    """Build a minimal MCP open_nodes result containing the given observations."""
    return {
        "entities": [
            {
                "name": "blind_assistant_user_u1",
                "entityType": "UserPreferences",
                "observations": observations,
            }
        ]
    }


async def _make_available_client() -> MCPMemoryClient:
    """Return an MCPMemoryClient backed by a mock MCP that reports as available."""
    mcp = MagicMock()
    mcp.call_tool = AsyncMock(return_value={"entities": []})
    client = MCPMemoryClient(mcp_client=mcp)
    await client.initialize()
    assert client.is_available is True
    return client


# ─────────────────────────────────────────────────────────────
# INITIALIZATION
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_initialize_no_mcp_client_sets_unavailable():
    """Without an MCP client, is_available must be False after initialize."""
    client = MCPMemoryClient(mcp_client=None)
    await client.initialize()
    assert client.is_available is False


@pytest.mark.asyncio
async def test_initialize_mcp_available_sets_flag():
    """A successful probe read_graph marks the client as available."""
    mcp = MagicMock()
    mcp.call_tool = AsyncMock(return_value={})
    client = MCPMemoryClient(mcp_client=mcp)
    await client.initialize()
    assert client.is_available is True


@pytest.mark.asyncio
async def test_initialize_mcp_raises_sets_unavailable():
    """If the MCP probe raises, is_available must be False (graceful degradation)."""
    mcp = MagicMock()
    mcp.call_tool = AsyncMock(side_effect=ConnectionError("server not running"))
    client = MCPMemoryClient(mcp_client=mcp)
    await client.initialize()
    assert client.is_available is False


# ─────────────────────────────────────────────────────────────
# LOCAL FALLBACK — get/set/delete without MCP
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_preference_returns_default_when_not_set():
    """Unset preferences return their DEFAULT_PREFERENCES value."""
    client = MCPMemoryClient(mcp_client=None)
    await client.initialize()
    result = await client.get_preference("u1", PREF_VOICE_SPEED)
    assert result == DEFAULT_PREFERENCES[PREF_VOICE_SPEED]


@pytest.mark.asyncio
async def test_set_and_get_preference_local_fallback():
    """Preferences written via set_preference are readable via get_preference."""
    client = MCPMemoryClient(mcp_client=None)
    await client.initialize()
    await client.set_preference("u1", PREF_VOICE_SPEED, 0.75)
    result = await client.get_preference("u1", PREF_VOICE_SPEED)
    assert result == 0.75


@pytest.mark.asyncio
async def test_set_preference_different_users_isolated():
    """Preferences set for user A must not appear for user B."""
    client = MCPMemoryClient(mcp_client=None)
    await client.initialize()
    await client.set_preference("user_a", PREF_VERBOSITY, "verbose")
    result = await client.get_preference("user_b", PREF_VERBOSITY)
    # user_b should get the default, not user_a's value
    assert result == DEFAULT_PREFERENCES[PREF_VERBOSITY]


@pytest.mark.asyncio
async def test_delete_preference_reverts_to_default():
    """After deleting a preference, get_preference should return the default."""
    client = MCPMemoryClient(mcp_client=None)
    await client.initialize()
    await client.set_preference("u1", PREF_BRAILLE_MODE, True)
    await client.delete_preference("u1", PREF_BRAILLE_MODE)
    result = await client.get_preference("u1", PREF_BRAILLE_MODE)
    assert result == DEFAULT_PREFERENCES[PREF_BRAILLE_MODE]


@pytest.mark.asyncio
async def test_delete_nonexistent_preference_does_not_raise():
    """Deleting a preference that was never set should not raise."""
    client = MCPMemoryClient(mcp_client=None)
    await client.initialize()
    await client.delete_preference("u1", PREF_VERBOSITY)  # never set


@pytest.mark.asyncio
async def test_clear_user_data_removes_all_preferences():
    """clear_user_data must wipe all preferences for the given user."""
    client = MCPMemoryClient(mcp_client=None)
    await client.initialize()
    await client.set_preference("u1", PREF_VOICE_SPEED, 2.0)
    await client.set_preference("u1", PREF_VERBOSITY, "terse")
    await client.clear_user_data("u1")
    # All preferences should revert to defaults
    speed = await client.get_preference("u1", PREF_VOICE_SPEED)
    verbosity = await client.get_preference("u1", PREF_VERBOSITY)
    assert speed == DEFAULT_PREFERENCES[PREF_VOICE_SPEED]
    assert verbosity == DEFAULT_PREFERENCES[PREF_VERBOSITY]


@pytest.mark.asyncio
async def test_clear_nonexistent_user_does_not_raise():
    """Clearing a user who has no stored preferences should not raise."""
    client = MCPMemoryClient(mcp_client=None)
    await client.initialize()
    await client.clear_user_data("nonexistent_user")


@pytest.mark.asyncio
async def test_get_all_preferences_merges_defaults():
    """get_all_preferences should merge stored values over DEFAULT_PREFERENCES."""
    client = MCPMemoryClient(mcp_client=None)
    await client.initialize()
    await client.set_preference("u1", PREF_VERBOSITY, "terse")
    prefs = await client.get_all_preferences("u1")
    # Stored value overrides default
    assert prefs[PREF_VERBOSITY] == "terse"
    # Non-stored keys come from defaults
    assert prefs[PREF_VOICE_SPEED] == DEFAULT_PREFERENCES[PREF_VOICE_SPEED]
    # All default keys are present
    for key in DEFAULT_PREFERENCES:
        assert key in prefs


@pytest.mark.asyncio
async def test_get_all_preferences_returns_full_defaults_for_new_user():
    """A user with no stored preferences gets all DEFAULT_PREFERENCES values."""
    client = MCPMemoryClient(mcp_client=None)
    await client.initialize()
    prefs = await client.get_all_preferences("brand_new_user")
    assert prefs == DEFAULT_PREFERENCES


# ─────────────────────────────────────────────────────────────
# MCP-CONNECTED PATHS
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_preference_writes_to_mcp_and_local():
    """set_preference should call the MCP tool AND update the local store."""
    client = await _make_available_client()
    await client.set_preference("u1", PREF_VERBOSITY, "verbose")

    # Local store is always updated
    local_val = client._local_store.get("u1", {}).get(PREF_VERBOSITY)
    assert local_val == "verbose"
    # MCP call_tool was called (create_entities or add_observations)
    assert client._mcp.call_tool.called


@pytest.mark.asyncio
async def test_get_preference_reads_from_mcp_when_available():
    """get_preference should query MCP when available."""
    mcp = MagicMock()
    obs_str = f"{PREF_VOICE_SPEED}={json.dumps(1.5)}"
    mcp.call_tool = AsyncMock(return_value=_make_mcp_result([obs_str]))
    client = MCPMemoryClient(mcp_client=mcp)
    # Manually mark as available (skip the probe which returns entities=[])
    client._available = True

    result = await client.get_preference("u1", PREF_VOICE_SPEED)
    assert result == 1.5


@pytest.mark.asyncio
async def test_get_preference_returns_default_when_mcp_has_no_matching_obs():
    """If MCP returns no observation for the key, return the default."""
    mcp = MagicMock()
    mcp.call_tool = AsyncMock(return_value=_make_mcp_result([]))
    client = MCPMemoryClient(mcp_client=mcp)
    client._available = True

    result = await client.get_preference("u1", PREF_VOICE_SPEED)
    assert result == DEFAULT_PREFERENCES[PREF_VOICE_SPEED]


@pytest.mark.asyncio
async def test_get_preference_falls_back_to_default_when_mcp_raises():
    """If an MCP call raises, return the default value silently."""
    mcp = MagicMock()
    mcp.call_tool = AsyncMock(side_effect=RuntimeError("mcp error"))
    client = MCPMemoryClient(mcp_client=mcp)
    client._available = True

    result = await client.get_preference("u1", PREF_VERBOSITY)
    assert result == DEFAULT_PREFERENCES[PREF_VERBOSITY]


@pytest.mark.asyncio
async def test_get_all_from_mcp_parses_multiple_observations():
    """_get_all_from_mcp should return a dict of all parsed preferences."""
    mcp = MagicMock()
    obs = [
        f"{PREF_VOICE_SPEED}={json.dumps(0.8)}",
        f"{PREF_VERBOSITY}={json.dumps('terse')}",
        f"{PREF_BRAILLE_MODE}={json.dumps(True)}",
    ]
    mcp.call_tool = AsyncMock(return_value=_make_mcp_result(obs))
    client = MCPMemoryClient(mcp_client=mcp)
    client._available = True

    result = await client._get_all_from_mcp("u1")
    assert result[PREF_VOICE_SPEED] == 0.8
    assert result[PREF_VERBOSITY] == "terse"
    assert result[PREF_BRAILLE_MODE] is True


@pytest.mark.asyncio
async def test_set_preference_add_observations_fallback_when_create_raises():
    """
    If create_entities raises (entity already exists), set_preference falls back
    to add_observations. The preference must still be set in the local store.
    """
    call_count = 0

    async def selective_raise(tool_name: str, args: dict) -> Any:
        nonlocal call_count
        call_count += 1
        if "create_entities" in tool_name:
            raise RuntimeError("entity already exists")
        # add_observations succeeds
        return {}

    mcp = MagicMock()
    mcp.call_tool = AsyncMock(side_effect=selective_raise)
    client = MCPMemoryClient(mcp_client=mcp)
    client._available = True

    await client.set_preference("u1", PREF_VERBOSITY, "verbose")
    # local store should still have the value
    assert client._local_store["u1"][PREF_VERBOSITY] == "verbose"
    # add_observations was called as fallback
    assert call_count >= 2


@pytest.mark.asyncio
async def test_delete_preference_mcp_removes_observation():
    """delete_preference should call delete_observations on the MCP server."""
    mcp = MagicMock()
    obs_str = f"{PREF_VERBOSITY}={json.dumps('verbose')}"
    # First call (open_nodes) returns existing observation; second (delete) succeeds.
    mcp.call_tool = AsyncMock(side_effect=[_make_mcp_result([obs_str]), {}])
    client = MCPMemoryClient(mcp_client=mcp)
    client._available = True
    client._local_store["u1"] = {PREF_VERBOSITY: "verbose"}

    await client.delete_preference("u1", PREF_VERBOSITY)
    # delete_observations must have been called
    calls = [c.args[0] for c in mcp.call_tool.call_args_list]
    assert any("delete_observations" in c for c in calls)


@pytest.mark.asyncio
async def test_clear_user_data_calls_delete_entities():
    """clear_user_data should call delete_entities on the MCP server."""
    client = await _make_available_client()
    client._local_store["u1"] = {PREF_VERBOSITY: "verbose"}

    await client.clear_user_data("u1")
    calls = [c.args[0] for c in client._mcp.call_tool.call_args_list]
    assert any("delete_entities" in c for c in calls)
    # Local store also cleared
    assert "u1" not in client._local_store


# ─────────────────────────────────────────────────────────────
# ENTITY NAME AND OBSERVATION PARSING
# ─────────────────────────────────────────────────────────────


def test_entity_name_format():
    """Entity names must be stable and prefixed."""
    client = MCPMemoryClient()
    assert client._entity_name("user_42") == "blind_assistant_user_user_42"


def test_parse_observations_from_list_of_entities():
    """_parse_observations must handle the list-of-dicts format."""
    result = [
        {"name": "e1", "observations": ["key1=val1", "key2=val2"]},
        {"name": "e2", "observations": ["key3=val3"]},
    ]
    obs = MCPMemoryClient._parse_observations(result)
    assert "key1=val1" in obs
    assert "key3=val3" in obs


def test_parse_observations_from_dict_with_entities_key():
    """_parse_observations must handle the dict-with-entities format."""
    result = {"entities": [{"name": "e1", "observations": ["foo=bar"]}]}
    obs = MCPMemoryClient._parse_observations(result)
    assert "foo=bar" in obs


def test_parse_observations_empty_returns_empty_list():
    """_parse_observations on None or empty input returns []."""
    assert MCPMemoryClient._parse_observations(None) == []
    assert MCPMemoryClient._parse_observations([]) == []
    assert MCPMemoryClient._parse_observations({}) == []


def test_parse_observations_ignores_non_string_entries():
    """_parse_observations skips observations that are not strings."""
    result = [{"name": "e1", "observations": [42, None, "valid=obs"]}]
    obs = MCPMemoryClient._parse_observations(result)
    assert obs == ["valid=obs"]


# ─────────────────────────────────────────────────────────────
# CONTEXT MANAGER INTEGRATION
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_context_manager_initialize_calls_memory_client():
    """ContextManager.initialize() must call memory_client.initialize()."""
    from blind_assistant.core.context import ContextManager

    memory_client = MCPMemoryClient(mcp_client=None)
    cm = ContextManager(config={}, memory_client=memory_client)
    await cm.initialize()
    # After initialize, client should have run (available or not)
    assert not memory_client.is_available  # no MCP in test


@pytest.mark.asyncio
async def test_context_manager_initialize_no_memory_client():
    """ContextManager.initialize() must not raise when memory_client is None."""
    from blind_assistant.core.context import ContextManager

    cm = ContextManager(config={}, memory_client=None)
    await cm.initialize()  # should not raise


@pytest.mark.asyncio
async def test_context_manager_load_user_context_uses_stored_prefs():
    """load_user_context must populate UserContext from stored preferences."""
    from blind_assistant.core.context import ContextManager

    memory_client = MCPMemoryClient(mcp_client=None)
    await memory_client.initialize()
    await memory_client.set_preference("u1", "verbosity", "terse")
    await memory_client.set_preference("u1", "voice_speed", 1.5)
    await memory_client.set_preference("u1", "braille_mode", True)

    cm = ContextManager(config={}, memory_client=memory_client)
    ctx = await cm.load_user_context("u1", "session_1")

    assert ctx.verbosity == "terse"
    assert ctx.speech_rate == 1.5
    assert ctx.braille_mode is True


@pytest.mark.asyncio
async def test_context_manager_load_user_context_defaults_when_no_memory():
    """load_user_context must return defaults when no memory client is set."""
    from blind_assistant.core.context import ContextManager

    cm = ContextManager(config={}, memory_client=None)
    ctx = await cm.load_user_context("u1", "session_1")

    assert ctx.verbosity == "standard"
    assert ctx.speech_rate == 1.0
    assert ctx.braille_mode is False


@pytest.mark.asyncio
async def test_context_manager_update_preference_persists():
    """update_preference must write through to the memory client."""
    from blind_assistant.core.context import ContextManager

    memory_client = MCPMemoryClient(mcp_client=None)
    await memory_client.initialize()
    cm = ContextManager(config={}, memory_client=memory_client)
    await cm.update_preference("u1", "verbosity", "verbose")

    stored = await memory_client.get_preference("u1", "verbosity")
    assert stored == "verbose"


@pytest.mark.asyncio
async def test_context_manager_update_preference_no_memory_client_does_not_raise():
    """update_preference with no memory client should log but not raise."""
    from blind_assistant.core.context import ContextManager

    cm = ContextManager(config={}, memory_client=None)
    await cm.update_preference("u1", "verbosity", "verbose")  # no raise


@pytest.mark.asyncio
async def test_context_manager_get_preference_returns_none_without_memory_client():
    """get_preference with no memory client must return None."""
    from blind_assistant.core.context import ContextManager

    cm = ContextManager(config={}, memory_client=None)
    result = await cm.get_preference("u1", "verbosity")
    assert result is None


@pytest.mark.asyncio
async def test_context_manager_get_preference_with_memory_client():
    """get_preference delegates to the memory client when present."""
    from blind_assistant.core.context import ContextManager

    memory_client = MCPMemoryClient(mcp_client=None)
    await memory_client.initialize()
    await memory_client.set_preference("u1", "verbosity", "terse")

    cm = ContextManager(config={}, memory_client=memory_client)
    result = await cm.get_preference("u1", "verbosity")
    assert result == "terse"
