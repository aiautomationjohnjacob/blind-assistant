"""
Unit tests for the main entry point (main.py).

Tests cover:
- start_services() creates MCPMemoryClient and passes it to APIServer when API is enabled
- start_services() continues gracefully when MCPMemoryClient raises on init
- start_services() skips MCPMemoryClient when API server is not enabled
- start_services() starts TelegramBot when telegram_enabled is True
- start_services() starts both TelegramBot and APIServer when both enabled
- main() --telegram flag sets telegram_enabled=True in config
- main() --telegram flag also forces api_server_enabled=True

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


# ─────────────────────────────────────────────────────────────
# start_services — Telegram wiring (Cycle 43)
# ─────────────────────────────────────────────────────────────


def test_start_services_starts_telegram_when_enabled():
    """start_services() creates and starts TelegramBot when telegram_enabled is True."""
    from blind_assistant.main import start_services

    config = {
        "telegram_enabled": True,
        "api_server_enabled": False,
        "voice_local_enabled": False,
    }

    telegram_constructor = MagicMock()
    fake_bot = MagicMock()
    fake_bot.start = AsyncMock(side_effect=asyncio.CancelledError)
    telegram_constructor.return_value = fake_bot

    with (
        patch("blind_assistant.core.orchestrator.Orchestrator", return_value=_make_fake_orchestrator()),
        patch("blind_assistant.interfaces.voice_local.VoiceLocalInterface"),
        patch("blind_assistant.interfaces.telegram_bot.TelegramBot", telegram_constructor),
        patch("blind_assistant.memory.mcp_memory.MCPMemoryClient"),
        contextlib.suppress(asyncio.CancelledError, Exception),
    ):
        asyncio.run(start_services(config))

    # TelegramBot must have been instantiated and start() called
    telegram_constructor.assert_called_once()
    fake_bot.start.assert_called_once()


def test_start_services_starts_both_telegram_and_api_when_both_enabled():
    """start_services() starts TelegramBot and APIServer concurrently when both enabled."""
    from blind_assistant.main import start_services

    config = {
        "telegram_enabled": True,
        "api_server_enabled": True,
        "voice_local_enabled": False,
    }

    telegram_started = []
    api_started = []

    class FakeTelegramBot:
        def __init__(self, orc, cfg):
            pass

        async def start(self):
            telegram_started.append(True)
            raise asyncio.CancelledError

    class FakeAPIServer:
        def __init__(self, orc, cfg, memory_client=None):
            pass

        async def start(self):
            api_started.append(True)
            raise asyncio.CancelledError

    with (
        patch("blind_assistant.core.orchestrator.Orchestrator", return_value=_make_fake_orchestrator()),
        patch("blind_assistant.interfaces.voice_local.VoiceLocalInterface"),
        patch("blind_assistant.interfaces.telegram_bot.TelegramBot", FakeTelegramBot),
        patch("blind_assistant.interfaces.api_server.APIServer", FakeAPIServer),
        patch("blind_assistant.memory.mcp_memory.MCPMemoryClient"),
        contextlib.suppress(asyncio.CancelledError, Exception),
    ):
        asyncio.run(start_services(config))

    # Both services must have attempted to start
    assert len(telegram_started) == 1
    assert len(api_started) == 1


def test_start_services_does_not_start_telegram_when_disabled():
    """start_services() does not create TelegramBot when telegram_enabled is False."""
    from blind_assistant.main import start_services

    config = {
        "telegram_enabled": False,
        "api_server_enabled": False,
        "voice_local_enabled": True,
    }

    class FakeVoice:
        def __init__(self, *args, **kwargs):
            pass

        async def start(self):
            raise asyncio.CancelledError

    telegram_constructor = MagicMock()

    with (
        patch("blind_assistant.core.orchestrator.Orchestrator", return_value=_make_fake_orchestrator()),
        patch("blind_assistant.interfaces.voice_local.VoiceLocalInterface", FakeVoice),
        patch("blind_assistant.interfaces.telegram_bot.TelegramBot", telegram_constructor),
        patch("blind_assistant.memory.mcp_memory.MCPMemoryClient"),
        contextlib.suppress(asyncio.CancelledError, Exception),
    ):
        asyncio.run(start_services(config))

    # TelegramBot must NOT be instantiated when telegram_enabled is False
    telegram_constructor.assert_not_called()


# ─────────────────────────────────────────────────────────────
# main() CLI argument parsing — Telegram flag (Cycle 43)
# ─────────────────────────────────────────────────────────────


def test_main_telegram_flag_sets_telegram_enabled_in_config():
    """main() --telegram flag sets telegram_enabled=True in the config dict."""
    import sys

    from blind_assistant.main import main

    captured_config: dict = {}

    async def fake_start_services(config: dict) -> None:
        captured_config.update(config)
        raise asyncio.CancelledError

    fake_config = {
        "telegram_enabled": False,
        "api_server_enabled": False,
        "voice_local_enabled": True,
    }

    with (
        patch("sys.argv", ["main", "--telegram"]),
        patch("blind_assistant.main.load_config", return_value=fake_config),
        patch("blind_assistant.main.start_services", fake_start_services),
        patch("blind_assistant.main.configure_logging"),
        contextlib.suppress(asyncio.CancelledError, Exception),
    ):
        main()

    assert captured_config.get("telegram_enabled") is True


def test_main_telegram_flag_also_forces_api_server_enabled():
    """main() --telegram flag implicitly enables api_server_enabled so bot has a backend."""
    import sys  # noqa: F401

    from blind_assistant.main import main

    captured_config: dict = {}

    async def fake_start_services(config: dict) -> None:
        captured_config.update(config)
        raise asyncio.CancelledError

    fake_config = {
        "telegram_enabled": False,
        "api_server_enabled": False,
        "voice_local_enabled": True,
    }

    with (
        patch("sys.argv", ["main", "--telegram"]),
        patch("blind_assistant.main.load_config", return_value=fake_config),
        patch("blind_assistant.main.start_services", fake_start_services),
        patch("blind_assistant.main.configure_logging"),
        contextlib.suppress(asyncio.CancelledError, Exception),
    ):
        main()

    # --telegram must force api_server_enabled so the Telegram bot has a backend to call
    assert captured_config.get("api_server_enabled") is True


def test_main_no_telegram_flag_leaves_telegram_disabled():
    """main() without --telegram does not change telegram_enabled in config."""
    from blind_assistant.main import main

    captured_config: dict = {}

    async def fake_start_services(config: dict) -> None:
        captured_config.update(config)
        raise asyncio.CancelledError

    fake_config = {
        "telegram_enabled": False,
        "api_server_enabled": False,
        "voice_local_enabled": True,
    }

    with (
        patch("sys.argv", ["main"]),
        patch("blind_assistant.main.load_config", return_value=fake_config),
        patch("blind_assistant.main.start_services", fake_start_services),
        patch("blind_assistant.main.configure_logging"),
        contextlib.suppress(asyncio.CancelledError, Exception),
    ):
        main()

    # telegram_enabled must remain False when --telegram flag is absent
    assert captured_config.get("telegram_enabled") is False
