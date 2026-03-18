"""
MCP Memory Server Client

Provides cross-session user preference storage and retrieval using the MCP memory server
(knowledge-graph-based persistence). Falls back to an in-memory dict when the MCP memory
server is unavailable (e.g., unit tests or offline operation).

Per INTEGRATION_MAP.md §2.2: the MCP memory server stores:
- User preferences (voice speed, verbosity, braille mode)
- Important context (user's name, location, common tasks)
- Installed tool registry state

The MCP memory server runs as a local background process. This client wraps the
mcp_memory MCP tool calls behind a simple async interface so the rest of the codebase
does not need to know about MCP internals.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Keys used in the memory graph for user preferences.
# Keeping them as module-level constants makes them easy to find and refactor.
PREF_VOICE_SPEED = "voice_speed"
PREF_VERBOSITY = "verbosity"
PREF_BRAILLE_MODE = "braille_mode"
PREF_OUTPUT_MODE = "output_mode"
PREF_USER_NAME = "user_name"
PREF_TIMEZONE = "timezone"
PREF_COMMON_TASKS = "common_tasks"

# Default preferences used when no stored preference exists.
DEFAULT_PREFERENCES: dict[str, Any] = {
    PREF_VOICE_SPEED: 1.0,
    PREF_VERBOSITY: "standard",
    PREF_BRAILLE_MODE: False,
    PREF_OUTPUT_MODE: "voice_text",
    PREF_USER_NAME: None,
    PREF_TIMEZONE: "UTC",
    PREF_COMMON_TASKS: [],
}


class MCPMemoryClient:
    """
    Thin async wrapper around the MCP memory server for user preference persistence.

    Uses an in-memory fallback dict when the MCP memory server is not reachable.
    This ensures the app remains functional even without MCP — preferences just
    won't persist across restarts in that case.

    Usage::

        client = MCPMemoryClient()
        await client.initialize()
        await client.set_preference("user_123", "voice_speed", 0.8)
        speed = await client.get_preference("user_123", "voice_speed")
    """

    def __init__(self, mcp_client: Any | None = None) -> None:
        # mcp_client is injected for testability; in production it comes from
        # the MCP session established by the orchestrator at startup.
        self._mcp = mcp_client
        # Fallback in-memory store — format: {user_id: {key: value}}
        self._local_store: dict[str, dict[str, Any]] = {}
        self._available = False

    async def initialize(self) -> None:
        """
        Test connectivity to the MCP memory server.

        Sets self._available = True if the server responds, False otherwise.
        The caller should not treat unavailability as a fatal error — the local
        fallback silently handles all read/write operations.
        """
        if self._mcp is None:
            logger.debug("MCP client not provided — using in-memory preference store.")
            self._available = False
            return

        try:
            # Probe the memory server with a lightweight read_graph call.
            await self._mcp.call_tool("mcp__memory__read_graph", {})
            self._available = True
            logger.info("MCP memory server connected successfully.")
        except Exception as exc:
            logger.warning("MCP memory server unavailable (%s) — falling back to in-memory store.", exc)
            self._available = False

    # ─────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────

    async def get_preference(self, user_id: str, key: str) -> Any:
        """
        Retrieve a single preference value for a user.

        Returns the default value for that key if nothing has been stored.
        Never raises — returns the default on any error.
        """
        if self._available:
            return await self._get_from_mcp(user_id, key)
        return self._local_store.get(user_id, {}).get(key, DEFAULT_PREFERENCES.get(key))

    async def set_preference(self, user_id: str, key: str, value: Any) -> None:
        """
        Persist a single preference value for a user.

        Writes to both the MCP store (if available) and the local fallback so
        within-session reads always work regardless of MCP availability.
        """
        # Always write to local store for within-session consistency.
        if user_id not in self._local_store:
            self._local_store[user_id] = {}
        self._local_store[user_id][key] = value

        if self._available:
            await self._set_in_mcp(user_id, key, value)

    async def get_all_preferences(self, user_id: str) -> dict[str, Any]:
        """
        Return all stored preferences for a user, merged with defaults.

        Missing keys are filled from DEFAULT_PREFERENCES so callers always
        receive a complete preference dict without None-checking every key.
        """
        stored: dict[str, Any] = {}

        if self._available:
            stored = await self._get_all_from_mcp(user_id)
        else:
            stored = dict(self._local_store.get(user_id, {}))

        # Merge stored values over defaults so new preference keys added in
        # future code are automatically available to existing users.
        merged = dict(DEFAULT_PREFERENCES)
        merged.update(stored)
        return merged

    async def delete_preference(self, user_id: str, key: str) -> None:
        """
        Remove a stored preference, reverting to the default value on next read.
        """
        # Remove from local store.
        if user_id in self._local_store and key in self._local_store[user_id]:
            del self._local_store[user_id][key]

        if self._available:
            await self._delete_from_mcp(user_id, key)

    async def clear_user_data(self, user_id: str) -> None:
        """
        Remove ALL preferences for a user (e.g., on account deletion).

        This is a destructive operation. Callers must get explicit user
        confirmation before calling this method.
        """
        self._local_store.pop(user_id, None)

        if self._available:
            await self._clear_user_from_mcp(user_id)

    @property
    def is_available(self) -> bool:
        """Return True if the MCP memory server is reachable."""
        return self._available

    # ─────────────────────────────────────────────────────────────
    # MCP LAYER — each method wraps one MCP tool call
    # ─────────────────────────────────────────────────────────────

    def _entity_name(self, user_id: str) -> str:
        """Return a stable entity name for a user in the MCP knowledge graph."""
        # Prefix avoids collisions with other MCP entities.
        return f"blind_assistant_user_{user_id}"

    async def _get_from_mcp(self, user_id: str, key: str) -> Any:
        """Fetch a single preference from the MCP memory graph."""
        # _mcp is guaranteed non-None here: _get_from_mcp is only called when
        # self._available is True, which requires a successful initialize() probe.
        assert self._mcp is not None
        try:
            result = await self._mcp.call_tool(
                "mcp__memory__open_nodes",
                {"names": [self._entity_name(user_id)]},
            )
            # The MCP memory server stores observations as a list of strings.
            # We JSON-encode each preference as "key=<json_value>".
            for obs in self._parse_observations(result):
                if obs.startswith(f"{key}="):
                    raw = obs[len(f"{key}=") :]
                    return json.loads(raw)
        except Exception as exc:
            logger.debug("MCP get_preference failed for %s/%s: %s", user_id, key, exc)

        return DEFAULT_PREFERENCES.get(key)

    async def _set_in_mcp(self, user_id: str, key: str, value: Any) -> None:
        """Write a single preference to the MCP memory graph."""
        assert self._mcp is not None  # only called when self._available is True
        entity = self._entity_name(user_id)
        observation = f"{key}={json.dumps(value)}"

        try:
            # Ensure the entity exists before adding an observation.
            await self._mcp.call_tool(
                "mcp__memory__create_entities",
                {
                    "entities": [
                        {
                            "name": entity,
                            "entityType": "UserPreferences",
                            "observations": [observation],
                        }
                    ]
                },
            )
        except Exception:
            # Entity may already exist — try adding the observation directly.
            try:
                await self._mcp.call_tool(
                    "mcp__memory__add_observations",
                    {
                        "observations": [
                            {
                                "entityName": entity,
                                "contents": [observation],
                            }
                        ]
                    },
                )
            except Exception as exc:
                logger.warning("MCP set_preference failed for %s/%s: %s", user_id, key, exc)

    async def _get_all_from_mcp(self, user_id: str) -> dict[str, Any]:
        """Retrieve all preferences for a user from the MCP memory graph."""
        assert self._mcp is not None  # only called when self._available is True
        try:
            result = await self._mcp.call_tool(
                "mcp__memory__open_nodes",
                {"names": [self._entity_name(user_id)]},
            )
            prefs: dict[str, Any] = {}
            for obs in self._parse_observations(result):
                if "=" in obs:
                    k, _, v = obs.partition("=")
                    try:
                        prefs[k] = json.loads(v)
                    except json.JSONDecodeError:
                        logger.debug("Ignoring malformed MCP observation: %s", obs)
            return prefs
        except Exception as exc:
            logger.debug("MCP get_all_preferences failed for %s: %s", user_id, exc)
            return {}

    async def _delete_from_mcp(self, user_id: str, key: str) -> None:
        """Remove a specific preference observation from the MCP memory graph."""
        try:
            # Read current observations, remove the target, then re-write.
            result = await self._mcp.call_tool(
                "mcp__memory__open_nodes",
                {"names": [self._entity_name(user_id)]},
            )
            all_obs = self._parse_observations(result)
            to_delete = [obs for obs in all_obs if obs.startswith(f"{key}=")]
            if to_delete:
                await self._mcp.call_tool(
                    "mcp__memory__delete_observations",
                    {
                        "deletions": [
                            {
                                "entityName": self._entity_name(user_id),
                                "observations": to_delete,
                            }
                        ]
                    },
                )
        except Exception as exc:
            logger.debug("MCP delete_preference failed for %s/%s: %s", user_id, key, exc)

    async def _clear_user_from_mcp(self, user_id: str) -> None:
        """Delete the entire user entity from the MCP memory graph."""
        try:
            await self._mcp.call_tool(
                "mcp__memory__delete_entities",
                {"entityNames": [self._entity_name(user_id)]},
            )
        except Exception as exc:
            logger.debug("MCP clear_user_data failed for %s: %s", user_id, exc)

    @staticmethod
    def _parse_observations(mcp_result: Any) -> list[str]:
        """
        Extract the observation strings from an MCP open_nodes result.

        The MCP memory server returns a nested structure; this normalises it
        so the rest of the code can iterate over plain strings.
        """
        observations: list[str] = []
        if mcp_result is None:
            return observations

        # mcp_result may be a list of entity dicts or a dict with 'entities' key.
        entities: list[Any] = []
        if isinstance(mcp_result, list):
            entities = mcp_result
        elif isinstance(mcp_result, dict):
            entities = mcp_result.get("entities", [])

        for entity in entities:
            if isinstance(entity, dict):
                for obs in entity.get("observations", []):
                    if isinstance(obs, str):
                        observations.append(obs)
        return observations
