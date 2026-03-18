"""
Context Manager

Manages user context across sessions:
- User preferences (voice speed, verbosity, braille mode)
- Conversation history
- Integration with MCP memory server for cross-session persistence
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blind_assistant.memory.mcp_memory import MCPMemoryClient

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages persistent user context.

    Preferences are stored via MCPMemoryClient (MCP memory server with local fallback).
    Conversation history is in-memory only (unless user opts in to logging).
    """

    def __init__(self, config: dict, memory_client: MCPMemoryClient | None = None) -> None:
        self.config = config
        # MCPMemoryClient handles both MCP server writes and local fallback automatically.
        self._memory_client = memory_client

    async def initialize(self) -> None:
        """Initialize context manager and connect to MCP memory server if available."""
        if self._memory_client is not None:
            await self._memory_client.initialize()
            if self._memory_client.is_available:
                logger.info("Context manager connected to MCP memory server.")
            else:
                logger.info("Context manager using in-memory preference store (MCP unavailable).")
        else:
            logger.debug("Context manager initialized without memory client.")

    async def load_user_context(self, user_id: str, session_id: str) -> Any:
        """
        Load context for a user. Creates default context if none exists.
        """
        from blind_assistant.core.orchestrator import UserContext

        if self._memory_client is not None:
            prefs = await self._memory_client.get_all_preferences(user_id)
        else:
            prefs = {}

        return UserContext(
            user_id=user_id,
            session_id=session_id,
            verbosity=prefs.get("verbosity", "standard"),
            speech_rate=float(prefs.get("voice_speed", 1.0)),
            output_mode=prefs.get("output_mode", "voice_text"),
            braille_mode=bool(prefs.get("braille_mode", False)),
        )

    async def update_preference(self, user_id: str, key: str, value: Any) -> None:
        """Update a user preference in persistent storage via MCP memory server."""
        if self._memory_client is not None:
            await self._memory_client.set_preference(user_id, key, value)
            logger.info("Preference updated for %s: %s = %s", user_id, key, value)
        else:
            logger.info("Preference update for %s: %s = %s (no memory client — not persisted)", user_id, key, value)

    async def get_preference(self, user_id: str, key: str) -> Any:
        """Retrieve a stored preference value, returning None if not set."""
        if self._memory_client is not None:
            return await self._memory_client.get_preference(user_id, key)
        return None
