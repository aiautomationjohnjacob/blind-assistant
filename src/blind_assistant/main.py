"""
Blind Assistant — Main Entry Point

Starts all services: Telegram bot interface, voice interface, and background tasks.

Usage:
  python -m blind_assistant.main          # Start all services
  python -m blind_assistant.main --voice  # Local voice interface only
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

    if config.get("telegram_enabled", True):
        bot = TelegramBot(orchestrator, config)
        tasks.append(asyncio.create_task(bot.start(), name="telegram"))
        logger.info("Telegram bot starting...")

    if config.get("voice_local_enabled", False):
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
        logger.error(
            "config.yaml not found. "
            "Run the installer first: python installer/install.py"
        )
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)


def configure_logging(debug: bool = False) -> None:
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
    parser = argparse.ArgumentParser(
        description="Blind Assistant — AI life companion for blind users"
    )
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

    asyncio.run(start_services(config))


if __name__ == "__main__":
    main()
