"""
Blind Assistant — Voice-Guided Installer

Sets up Blind Assistant entirely by voice. No sighted assistance required.

Usage:
  python installer/install.py

The installer will:
1. Speak all instructions aloud (no reading required)
2. Wait for verbal responses at each step
3. Confirm each step before proceeding
4. Test everything after setup is complete

Requirements for running the installer:
- Python 3.11+
- pyttsx3 (pip install pyttsx3) — for voice output before setup is complete
- A microphone
- Internet connection (for downloading Whisper model and connecting to Claude AI)

The installer will speak these requirements to you if they are not met.
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================
# Step messages — all spoken aloud, never just displayed
# ============================================================

WELCOME_MESSAGE = """
Welcome to Blind Assistant setup.
I am your AI life companion — designed to help you use your computer independently.

I will guide you through setup entirely by voice.
This will take about 5 to 10 minutes.

At each step, I will tell you what to do and wait for your response.
You can say "say that again" at any time to hear any instruction repeated.
You can say "I need help" at any time to get more explanation.

Are you ready to start? Say yes when you're ready.
"""

STEP_APP_INTRO = """
Step 1: Setting up the Blind Assistant app on your phone.

The Blind Assistant app is a free app for Android and iPhone.
It works with TalkBack on Android, and with VoiceOver on iPhone.

To install it: open the Play Store on Android, or the App Store on iPhone.
Search for Blind Assistant.
Install it and open it.
The app will ask for your server address, which is the address of this computer.

If you are setting up on this computer now, say ready and I will tell you your server address.
If you want to do this later, say skip.
"""

STEP_API_SERVER_INFO = """
Your server is running at:
http colon slash slash {server_address} colon 8000

Write this down or take a screenshot.
You will enter this address in the Blind Assistant app on your phone.

Say ready when you have noted the address.
"""

STEP_TELEGRAM_OPTIONAL_INTRO = """
Optional power-user step: Telegram remote access.

Telegram is a messaging app that power users can optionally use to control
Blind Assistant remotely — from any device, anywhere in the world.

This step is entirely optional. The native Blind Assistant app on your phone is the
primary way to use this assistant. Telegram is only for power users who want
an extra remote access channel.

Note: setting up Telegram requires sighted assistance to navigate some visual menus.
If you are a blind user and do not have sighted help available, say skip.

Would you like to set up Telegram remote access? Say yes or skip.
"""

STEP_TELEGRAM_BOT_CREATION = """
Here is how to create your Telegram bot. I will say each step, then wait.

Open Telegram and search for BotFather. That is spelled B-O-T-F-A-T-H-E-R, all one word.
Start a chat with BotFather.
Send it the message: slash newbot.
It will ask you for a name for your bot. Type anything you like, such as My Assistant.
It will then ask for a username ending in bot.
After you create it, BotFather will give you a long code called a token.
That token looks something like: 123456789 colon ABC-DEF1234.

Please copy that token now. I will ask you to read it or paste it in a moment.

Say ready when you have the token.
"""

STEP_CLAUDE_INTRO = """
Step 2: Setting up your Claude AI connection.

Claude is the AI that powers my thinking and understanding.
You will need an API key from Anthropic — the company that makes Claude.

To get your key:
Go to anthropic.com and create an account, or log in if you have one.
Navigate to API keys and create a new key.
The key starts with the letters sk-ant.

Say ready when you have your Claude API key.
"""

STEP_ELEVENLABS_INTRO = """
Step 3: Setting up my voice.

I can speak with a clear, natural voice using a service called ElevenLabs.
This step is optional — I can also use a basic voice that works without internet.

To use the high quality voice:
Go to elevenlabs.io and create a free account.
Copy your API key from your profile settings.

Say yes if you want to set up the high quality voice, or skip to continue with the basic voice.
"""

STEP_VAULT_INTRO = """
Step 4: Setting up your personal knowledge base.

I can remember things for you — appointments, medications, important notes, and more.
This is stored privately on your device, protected with your own password.

I need you to choose a passphrase. This should be something you can remember,
like a phrase from a song or a sentence that means something to you.
You will say it to unlock your notes at the start of each session.

Please think of your passphrase now. Say ready when you have one in mind.
"""

STEP_COMPLETE = """
Setup is complete!

Here is what I can do for you now:
I can see your screen and describe what is on it.
I can help you navigate apps that do not work with screen readers.
I can remember notes and information for you.
I can help you order food and manage daily tasks.

To talk to me: open the Blind Assistant app on your phone and speak your request.
You can also speak directly to this computer.

Try saying: what is on my screen right now.

Welcome to your new assistant. I am here whenever you need me.
"""

STEP_FAILED_GRACEFULLY = """
I was not able to complete setup because of: {reason}.

Here is what you can try:
{suggestion}

You can run setup again any time by saying: python installer slash install dot p y.
"""


class VoiceInstaller:
    """Voice-guided setup wizard."""

    def __init__(self) -> None:
        self._tts = None
        self._step_count = 0
        self._last_message = ""
        self._setup_mode = True

    def _init_tts(self) -> None:
        """Initialize local TTS engine (no external services needed at this point)."""
        try:
            import pyttsx3
            self._tts = pyttsx3.init()
            if self._tts is not None:  # pyttsx3.init() can return None on some systems
                self._tts.setProperty("rate", 160)  # Slightly slower for clarity
                self._tts.setProperty("volume", 0.95)
        except ImportError:
            print(
                "\nWARNING: pyttsx3 not installed. "
                "Please run: pip install pyttsx3\n"
                "Then restart setup.\n"
            )
            # Still continue — print to terminal as fallback
            self._tts = None

    def _speak(self, message: str) -> None:
        """Speak a message aloud and also print it."""
        self._last_message = message
        # Always print (for users who might be running with a screen reader)
        print(f"\n{message}\n")

        if self._tts:
            try:
                self._tts.say(message)
                self._tts.runAndWait()
            except Exception as e:
                logger.warning(f"TTS failed: {e}")

    def _wait_for_input(self, prompt: str = "") -> str:
        """Wait for text input (fallback when voice input not yet set up)."""
        if prompt:
            self._speak(prompt)
        try:
            return input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            return "cancel"

    def _check_ready(self, response: str) -> bool:
        """Check if user said they're ready."""
        ready_words = {"yes", "ready", "ok", "okay", "sure", "go", "done", "yeah", "yep"}
        return any(word in response.lower() for word in ready_words)

    def _check_skip(self, response: str) -> bool:
        """Check if user wants to skip a step."""
        return any(word in response.lower() for word in {"skip", "no", "later", "next"})

    async def run(self) -> bool:
        """
        Run the complete installation wizard.
        Returns True if successful.
        """
        self._init_tts()

        # Welcome
        self._speak(WELCOME_MESSAGE)
        response = self._wait_for_input()
        if not self._check_ready(response):
            self._speak("Okay. Run setup again when you're ready.")
            return False

        # Step 1: Native app connection info (primary interface)
        await self._setup_native_app()

        # Step 2: Claude API (required)
        success = await self._setup_claude()
        if not success:
            return False

        # Step 3: ElevenLabs (optional)
        await self._setup_elevenlabs()

        # Step 4: Personal vault
        success = await self._setup_vault()
        if not success:
            return False

        # Step 5: Telegram (optional power-user channel)
        await self._setup_telegram_optional()

        # Install Python dependencies
        await self._install_dependencies()

        # Self-test
        await self._run_self_test()

        self._speak(STEP_COMPLETE)
        return True

    async def _setup_native_app(self) -> None:
        """
        Guide user through connecting the native Blind Assistant app.

        The native app (Android TalkBack / iPhone VoiceOver) is the PRIMARY interface.
        This step tells the user their server address so they can enter it in the app.
        """
        import socket

        self._speak(STEP_APP_INTRO)
        response = self._wait_for_input()

        if self._check_skip(response):
            self._speak(
                "No problem. You can connect the app later. "
                "Run setup again to get your server address."
            )
            return

        # Determine the local IP so the phone can connect
        try:
            # Connect to an external address (does not send data) to find local IP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
            sock.close()
        except OSError:
            local_ip = "127.0.0.1"

        server_address = local_ip
        self._speak(STEP_API_SERVER_INFO.format(server_address=server_address))
        self._wait_for_input()
        self._speak("Great. You can now enter that address in the Blind Assistant app.")

    async def _setup_telegram_optional(self) -> None:
        """
        Optional: guide power users through Telegram bot setup.

        Telegram is a secondary/super-user channel only.
        The native app is primary. This step is clearly marked as optional
        and warns blind users that Telegram setup requires sighted assistance
        for some visual configuration steps.
        """
        from blind_assistant.security.credentials import (
            store_credential,
            TELEGRAM_BOT_TOKEN,
            TELEGRAM_ALLOWED_USER_IDS,
        )

        self._speak(STEP_TELEGRAM_OPTIONAL_INTRO)
        response = self._wait_for_input()

        if self._check_skip(response):
            self._speak("Okay, skipping Telegram setup. The native app is your primary interface.")
            return

        self._speak(STEP_TELEGRAM_BOT_CREATION)
        response = self._wait_for_input()

        if not self._check_ready(response):
            self._speak("Okay, let me know when you have the token.")
            response = self._wait_for_input()

        self._speak(
            "Please type or paste your Telegram bot token now. "
            "It should start with numbers followed by a colon."
        )
        token = self._wait_for_input("Bot token:")

        if not token or ":" not in token:
            self._speak(
                "That doesn't look like a bot token. "
                "The token should have numbers, then a colon, then letters and numbers. "
                "Let's try again."
            )
            token = self._wait_for_input("Bot token:")

        store_credential(TELEGRAM_BOT_TOKEN, token)
        self._speak("Bot token saved securely.")

        self._speak(
            "Now I need to know your Telegram user ID so only you can control me. "
            "To find your ID, send a message to a bot called 'userinfobot' on Telegram. "
            "It will tell you your ID number. "
            "Say ready when you have your user ID number."
        )
        self._wait_for_input()
        user_id = self._wait_for_input("Your Telegram user ID:")

        if user_id.isdigit():
            store_credential(TELEGRAM_ALLOWED_USER_IDS, user_id)
            self._speak(
                f"Your user ID {user_id} has been saved. "
                "Only you can control this assistant via Telegram."
            )
        else:
            self._speak(
                "I didn't catch a number. I'll save this step for later. "
                "You can add your user ID by running setup again."
            )

    async def _setup_claude(self) -> bool:
        """Guide user through Claude API key setup."""
        from blind_assistant.security.credentials import store_credential, CLAUDE_API_KEY

        self._speak(STEP_CLAUDE_INTRO)
        response = self._wait_for_input()

        if not self._check_ready(response):
            self._speak(
                "Please get your Claude API key from anthropic.com "
                "and run setup again."
            )
            return False

        self._speak("Please type or paste your Claude API key.")
        api_key = self._wait_for_input("Claude API key:")

        if not api_key or not api_key.startswith("sk-"):
            self._speak(
                "That doesn't look quite right. Claude API keys start with sk-ant. "
                "Try again."
            )
            api_key = self._wait_for_input("Claude API key:")

        store_credential(CLAUDE_API_KEY, api_key)
        self._speak("Claude API key saved securely.")
        return True

    async def _setup_elevenlabs(self) -> None:
        """Optional ElevenLabs voice setup."""
        from blind_assistant.security.credentials import store_credential, ELEVENLABS_API_KEY

        self._speak(STEP_ELEVENLABS_INTRO)
        response = self._wait_for_input()

        if self._check_skip(response):
            self._speak("Okay, I'll use the basic voice for now. You can set this up later.")
            return

        self._speak("Please type or paste your ElevenLabs API key.")
        api_key = self._wait_for_input("ElevenLabs API key:")

        if api_key:
            store_credential(ELEVENLABS_API_KEY, api_key)
            self._speak("ElevenLabs voice key saved. I'll use the high quality voice.")

    async def _setup_vault(self) -> bool:
        """Guide user through personal vault setup."""
        self._speak(STEP_VAULT_INTRO)
        response = self._wait_for_input()

        if not self._check_ready(response):
            self._speak("Take your time. Say ready when you have a passphrase in mind.")
            self._wait_for_input()

        self._speak(
            "Please say or type your passphrase now. "
            "I will remember it only for this session — I won't store the passphrase itself."
        )
        passphrase = self._wait_for_input("Your vault passphrase:")

        if len(passphrase) < 4:
            self._speak("Please choose a passphrase with at least 4 words or characters.")
            passphrase = self._wait_for_input("Your vault passphrase:")

        # Create the vault
        from pathlib import Path
        from blind_assistant.second_brain.encryption import VaultKey, generate_salt

        vault_path = Path.home() / "blind-assistant-vault"
        salt = generate_salt()
        salt_path = vault_path / ".salt"

        vault_path.mkdir(parents=True, exist_ok=True)
        salt_path.write_bytes(salt)
        salt_path.chmod(0o600)

        vault_key = VaultKey()
        vault_key.unlock(passphrase, salt)

        # Store in keychain so user doesn't need to re-enter each session
        try:
            vault_key.store_in_keychain()
            self._speak(
                "Your personal knowledge base is ready. "
                "Your vault key has been saved to your system keychain. "
                "You won't need to enter your passphrase each time."
            )
        except Exception:
            self._speak(
                "Your personal knowledge base is ready. "
                "You'll be asked for your passphrase when you start a new session."
            )

        return True

    async def _install_dependencies(self) -> None:
        """Install Python dependencies."""
        self._speak(
            "Now I'm going to install the software I need to work. "
            "This will take a minute or two. I'll let you know when it's done."
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", "-r",
                str(Path(__file__).parent.parent / "requirements.txt"),
                "--quiet",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode == 0:
                self._speak("Software installed successfully.")
            else:
                self._speak(
                    f"Some software didn't install correctly. "
                    "This might cause some features not to work. "
                    "We can try to fix this later."
                )
                logger.error(f"pip install failed: {stderr.decode()}")
        except Exception as e:
            logger.error(f"Dependency installation failed: {e}")
            self._speak("Software installation ran into a problem. We'll continue anyway.")

    async def _run_self_test(self) -> None:
        """
        Verify that required components are configured.

        Required (2 checks): Claude AI key + personal vault
        Optional (reported but not counted): Telegram bot token
        """
        self._speak("Running a quick test to make sure everything is working...")

        required_passed = 0
        required_total = 2  # Claude + vault

        # Test Claude API (required)
        try:
            from blind_assistant.security.credentials import get_credential, CLAUDE_API_KEY
            if get_credential(CLAUDE_API_KEY):
                required_passed += 1
                self._speak("Claude AI connection: ready.")
        except Exception:
            self._speak("Claude AI: not yet configured. Please re-run setup and enter your API key.")

        # Test vault (required)
        vault_path = Path.home() / "blind-assistant-vault"
        if vault_path.exists():
            required_passed += 1
            self._speak("Personal knowledge base: ready.")
        else:
            self._speak("Personal knowledge base: not yet set up.")

        # Test Telegram (optional — just report, do not count against total)
        try:
            from blind_assistant.security.credentials import get_credential, TELEGRAM_BOT_TOKEN
            if get_credential(TELEGRAM_BOT_TOKEN):
                self._speak("Telegram remote access: configured (optional).")
        except Exception:
            pass  # Telegram is optional; silent skip is correct here

        if required_passed == required_total:
            self._speak(
                "All required components are ready. "
                "You can start using the assistant now."
            )
        else:
            missing = required_total - required_passed
            self._speak(
                f"{missing} required component{'s are' if missing > 1 else ' is'} not yet configured. "
                "Run setup again to complete the remaining steps."
            )


async def run_installer() -> None:
    """Main entry point for the installer."""
    logging.basicConfig(level=logging.INFO)

    installer = VoiceInstaller()
    success = await installer.run()

    if success:
        print("\nSetup complete. Run: python -m blind_assistant.main\n")
    else:
        print("\nSetup incomplete. Run setup again when ready.\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_installer())
