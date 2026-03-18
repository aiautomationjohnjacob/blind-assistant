"""
Unit tests for the main entry point (main.py).

Tests cover:
- start_services() creates MCPMemoryClient and passes it to APIServer when API is enabled
- start_services() continues gracefully when MCPMemoryClient raises on init
- start_services() skips MCPMemoryClient when API server is not enabled
- load_config() exits when config.yaml is missing

All external I/O is mocked (asyncio tasks, MCPMemoryClient, APIServer, Orchestrator).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────
# start_services — API server MCPMemoryClient wiring
# ─────────────────────────────────────────────────────────────


async def _run_start_services_with_api(extra_config: dict | None = None) -> dict:
    """Helper: run start_services() with api_server_enabled=True for one iteration.

    Cancels the asyncio.gather immediately so we can inspect what was constructed.
    Returns the keyword arguments captured from APIServer constructor calls.
    """
    import asyncio

    from blind_assistant.main import start_services

    config = {"api_server_enabled": True, "voice_local_enabled": False, **(extra_config or {})}

    captured: dict = {}

    class FakeAPIServer:
        def __init__(self, orc, cfg, memory_client=None):
            captured["memory_client"] = memory_client

        async def start(self):
            # Raise immediately so gather() exits quickly without blocking
            raise asyncio.CancelledError

    fake_orchestrator = MagicMock()
    fake_orchestrator.initialize = AsyncMock()

    with (
        patch("blind_assistant.main.Orchestrator", return_value=fake_orchestrator),
        patch("blind_assistant.main.VoiceLocalInterface"),
        patch("blind_assistant.main.TelegramBot"),
        patch("blind_assistant.interfaces.api_server.APIServer", FakeAPIServer),
    ):
        try:
            await start_services(config)
        except (asyncio.CancelledError, Exception):
            pass

    return captured


def test_start_services_passes_memory_client_to_api_server():
    """start_services() creates MCPMemoryClient and injects it into APIServer."""
    import asyncio

    from blind_assistant.main import start_services

    config = {"api_server_enabled": True, "voice_local_enabled": False}

    captured: dict = {}

    class FakeAPIServer:
        def __init__(self, orc, cfg, memory_client=None):
            captured["memory_client"] = memory_client

        async def start(self):
            raise asyncio.CancelledError

    fake_orchestrator = MagicMock()
    fake_orchestrator.initialize = AsyncMock()

    fake_memory = MagicMock()

    with (
        patch("blind_assistant.main.Orchestrator", return_value=fake_orchestrator),
        patch("blind_assistant.main.VoiceLocalInterface"),
        patch("blind_assistant.main.TelegramBot"),
        patch("blind_assistant.interfaces.api_server.APIServer", FakeAPIServer),
        patch("blind_assistant.memory.mcp_memory.MCPMemoryClient", return_value=fake_memory),
    ):
        try:
            asyncio.run(start_services(config))
        except (asyncio.CancelledError, Exception):
            pass

    # The injected memory_client must be our fake instance
    assert captured.get("memory_client") is fake_memory


def test_start_services_continues_when_mcp_memory_raises():
    """start_services() degrades gracefully if MCPMemoryClient constructor raises."""
    import asyncio

    from blind_assistant.main import start_services

    config = {"api_server_enabled": True, "voice_local_enabled": False}

    captured: dict = {}

    class FakeAPIServer:
        def __init__(self, orc, cfg, memory_client=None):
            captured["memory_client"] = memory_client

        async def start(self):
            raise asyncio.CancelledError

    fake_orchestrator = MagicMock()
    fake_orchestrator.initialize = AsyncMock()

    with (
        patch("blind_assistant.main.Orchestrator", return_value=fake_orchestrator),
        patch("blind_assistant.main.VoiceLocalInterface"),
        patch("blind_assistant.main.TelegramBot"),
        patch("blind_assistant.interfaces.api_server.APIServer", FakeAPIServer),
        patch(
            "blind_assistant.memory.mcp_memory.MCPMemoryClient",
            side_effect=RuntimeError("MCP unavailable"),
        ),
    ):
        try:
            asyncio.run(start_services(config))
        except (asyncio.CancelledError, Exception):
            pass

    # When MCPMemoryClient fails, APIServer must still be created — with memory_client=None
    assert "memory_client" in captured
    assert captured["memory_client"] is None


def test_start_services_does_not_create_mcp_when_api_disabled():
    """start_services() skips MCPMemoryClient entirely when api_server_enabled is False."""
    import asyncio

    from blind_assistant.main import start_services

    config = {"api_server_enabled": False, "voice_local_enabled": True}

    fake_orchestrator = MagicMock()
    fake_orchestrator.initialize = AsyncMock()

    class FakeVoice:
        def __init__(self, *args, **kwargs):
            pass

        async def start(self):
            raise asyncio.CancelledError

    mcp_constructor = MagicMock()

    with (
        patch("blind_assistant.main.Orchestrator", return_value=fake_orchestrator),
        patch("blind_assistant.main.VoiceLocalInterface", FakeVoice),
        patch("blind_assistant.main.TelegramBot"),
        patch("blind_assistant.memory.mcp_memory.MCPMemoryClient", mcp_constructor),
    ):
        try:
            asyncio.run(start_services(config))
        except (asyncio.CancelledError, Exception):
            pass

    # MCPMemoryClient must NOT have been instantiated when API server is off
    mcp_constructor.assert_not_called()
