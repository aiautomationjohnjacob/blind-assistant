"""
Unit tests for the main entry point (main.py).

Tests cover:
- start_services() creates MCPMemoryClient and passes it to APIServer when API is enabled
- start_services() continues gracefully when MCPMemoryClient raises on init
- start_services() skips MCPMemoryClient when API server is not enabled

All external I/O is mocked. main.py uses lazy imports inside start_services(), so
we must patch at the source module path (not blind_assistant.main.X).
"""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _make_fake_orchestrator() -> MagicMock:
    """Build a mock Orchestrator whose initialize() resolves immediately."""
    orc = MagicMock()
    orc.initialize = AsyncMock()
    return orc


# ─────────────────────────────────────────────────────────────
# start_services — MCPMemoryClient wiring (Cycle 25)
# ─────────────────────────────────────────────────────────────


def test_start_services_passes_memory_client_to_api_server():
    """start_services() creates MCPMemoryClient and injects it into APIServer."""
    from blind_assistant.main import start_services

    config = {"api_server_enabled": True, "voice_local_enabled": False}

    captured: dict = {}

    class FakeAPIServer:
        def __init__(self, orc, cfg, memory_client=None):
            captured["memory_client"] = memory_client

        async def start(self):
            # Cancel immediately so gather() exits without blocking
            raise asyncio.CancelledError

    fake_memory = MagicMock()

    with (
        patch("blind_assistant.core.orchestrator.Orchestrator", return_value=_make_fake_orchestrator()),
        patch("blind_assistant.interfaces.voice_local.VoiceLocalInterface"),
        patch("blind_assistant.interfaces.telegram_bot.TelegramBot"),
        patch("blind_assistant.interfaces.api_server.APIServer", FakeAPIServer),
        patch("blind_assistant.memory.mcp_memory.MCPMemoryClient", return_value=fake_memory),
        contextlib.suppress(asyncio.CancelledError, Exception),
    ):
        asyncio.run(start_services(config))

    # The injected memory_client must be our fake instance
    assert captured.get("memory_client") is fake_memory


def test_start_services_continues_when_mcp_memory_raises():
    """start_services() degrades gracefully if MCPMemoryClient constructor raises."""
    from blind_assistant.main import start_services

    config = {"api_server_enabled": True, "voice_local_enabled": False}

    captured: dict = {}

    class FakeAPIServer:
        def __init__(self, orc, cfg, memory_client=None):
            captured["memory_client"] = memory_client

        async def start(self):
            raise asyncio.CancelledError

    with (
        patch("blind_assistant.core.orchestrator.Orchestrator", return_value=_make_fake_orchestrator()),
        patch("blind_assistant.interfaces.voice_local.VoiceLocalInterface"),
        patch("blind_assistant.interfaces.telegram_bot.TelegramBot"),
        patch("blind_assistant.interfaces.api_server.APIServer", FakeAPIServer),
        patch(
            "blind_assistant.memory.mcp_memory.MCPMemoryClient",
            side_effect=RuntimeError("MCP unavailable"),
        ),
        contextlib.suppress(asyncio.CancelledError, Exception),
    ):
        asyncio.run(start_services(config))

    # When MCPMemoryClient fails, APIServer must still be created with memory_client=None
    assert "memory_client" in captured
    assert captured["memory_client"] is None


def test_start_services_does_not_create_mcp_when_api_disabled():
    """start_services() skips MCPMemoryClient entirely when api_server_enabled is False."""
    from blind_assistant.main import start_services

    config = {"api_server_enabled": False, "voice_local_enabled": True}

    class FakeVoice:
        def __init__(self, *args, **kwargs):
            pass

        async def start(self):
            raise asyncio.CancelledError

    mcp_constructor = MagicMock()

    with (
        patch("blind_assistant.core.orchestrator.Orchestrator", return_value=_make_fake_orchestrator()),
        patch("blind_assistant.interfaces.voice_local.VoiceLocalInterface", FakeVoice),
        patch("blind_assistant.interfaces.telegram_bot.TelegramBot"),
        patch("blind_assistant.memory.mcp_memory.MCPMemoryClient", mcp_constructor),
        contextlib.suppress(asyncio.CancelledError, Exception),
    ):
        asyncio.run(start_services(config))

    # MCPMemoryClient must NOT have been instantiated when API server is off
    mcp_constructor.assert_not_called()
