"""
Blind Assistant — Main Entry Point

Starts all enabled services: voice interface (default), API server, and optionally
the Telegram bot (secondary/super-user channel — disabled by default).

Primary interfaces are the native standalone apps (Android, iOS, Desktop, Web) which
connect to the API server. The local voice interface is the development demo target.
Telegram is an optional super-user channel — not the primary interface.

Usage:
  python -m blind_assistant.main          # Local voice interface (default)
  python -m blind_assistant.main --api    # Start the REST API server (port 8000)
  python -m blind_assistant.main --voice  # Explicitly enable local voice interface
  python -m blind_assistant.main --setup  # Run voice-guided setup wizard
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


async def start_services(config: dict) -> None:
    """Start all enabled services concurrently."""
    from blind_assistant.core.orchestrator import Orchestrator
    from blind_assistant.interfaces.telegram_bot import TelegramBot
    from blind_assistant.interfaces.voice_local import VoiceLocalInterface

    orchestrator = Orchestrator(config)
    await orchestrator.initialize()

    tasks = []

    # Telegram is optional/secondary — disabled by default (requires manual visual setup)
    if config.get("telegram_enabled", False):
        bot = TelegramBot(orchestrator, config)
        tasks.append(asyncio.create_task(bot.start(), name="telegram"))
        logger.info("Telegram bot starting (secondary/super-user channel)...")

    # API server — primary connection point for all native client apps
    if config.get("api_server_enabled", False):
        from blind_assistant.interfaces.api_server import APIServer
        from blind_assistant.memory.mcp_memory import MCPMemoryClient

        # MCPMemoryClient persists user preferences across server restarts.
        # Initialised here so the production server has memory; injected for testability.
        memory_client: MCPMemoryClient | None = None
        try:
            memory_client = MCPMemoryClient()
            logger.info("MCPMemoryClient initialised — user preferences will persist.")
        except Exception as exc:
            logger.warning(
                "MCPMemoryClient could not be initialised (%s) — profile preferences will be session-only.",
                exc,
            )

        api_server = APIServer(orchestrator, config, memory_client=memory_client)
        tasks.append(asyncio.create_task(api_server.start(), name="api_server"))
        logger.info("REST API server starting on localhost:8000...")

    # Local voice interface — primary demo interface for development/desktop
    if config.get("voice_local_enabled", True):
        voice = VoiceLocalInterface(orchestrator, config)
        tasks.append(asyncio.create_task(voice.start(), name="voice_local"))
        logger.info("Local voice interface starting...")

    if not tasks:
        logger.error("No interfaces enabled. Check config.yaml.")
        sys.exit(1)

    logger.info("Blind Assistant is running. Say hello to get started.")

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


def load_config() -> dict:
    """Load configuration from config.yaml."""
    import yaml

    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if not config_path.exists():
        logger.error("config.yaml not found. Run the installer first: python installer/install.py")
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)


def configure_logging(debug: bool = False) -> None:
    """Set up root logging with a consistent format; reduce noise from third-party libs."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


def main() -> None:
    """Parse CLI arguments and launch the selected interface (setup / voice / Telegram / API)."""
    parser = argparse.ArgumentParser(description="Blind Assistant — AI life companion for blind users")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run the voice-guided setup wizard",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable local voice interface (microphone + speaker)",
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Start the REST API server on localhost:8000 (for client apps)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    configure_logging(debug=args.debug)

    if args.setup:
        # Run voice-guided installer
        from installer.install import run_installer

        asyncio.run(run_installer())
        return

    config = load_config()

    if args.voice:
        config["voice_local_enabled"] = True

    if args.api:
        config["api_server_enabled"] = True

    asyncio.run(start_services(config))


if __name__ == "__main__":
    main()
