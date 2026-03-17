"""
Shared fixtures for Android TalkBack E2E tests.

Provides the `adb` fixture that wraps Android Debug Bridge commands
for interacting with the emulator or real device.

Requires:
  - ADB installed and in PATH (part of Android SDK)
  - An AVD running: `emulator -avd blind_assistant_test &`
  - OR a real Android device with USB debugging enabled

These tests are skipped automatically when ADB is not available,
which is always the case in non-release CI runs (only release tags
trigger the e2e-android CI job).

Per testing.md: Android E2E tests use ADB and AVD.
"""

from __future__ import annotations

# ruff: noqa: S603, S607  -- subprocess calls use ADB (system tool); args controlled by tests
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


class ADBClient:
    """Thin wrapper around ADB shell commands for E2E test use."""

    def __init__(self, device_serial: str | None = None) -> None:
        """Initialise ADB client, optionally targeting a specific device serial."""
        self._serial_flag = ["-s", device_serial] if device_serial else []

    def shell(self, command: str) -> str:
        """Run an ADB shell command and return stdout as a string."""
        result = subprocess.run(
            ["adb", *self._serial_flag, "shell", command],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout

    def pull(self, remote_path: str) -> str:
        """Pull a file from the device and return its text content."""
        # Use a named temp file for the ADB pull destination.
        # The file is created in the system temp directory (not /tmp directly).
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
            local_path = tmp.name
        subprocess.run(
            ["adb", *self._serial_flag, "pull", remote_path, local_path],
            capture_output=True,
            timeout=30,
        )
        try:
            return Path(local_path).read_text()
        except FileNotFoundError:
            return ""

    def screenshot(self, output_path: str | None = None) -> str:
        """Capture a device screenshot and save it locally. Returns local path."""
        if output_path is None:
            # Default to a temp file in the system temp dir (not hardcoded /tmp)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                output_path = tmp.name
        # Capture on device
        self.shell("screencap -p /sdcard/screenshot.png")
        # Pull to local
        subprocess.run(
            ["adb", *self._serial_flag, "pull", "/sdcard/screenshot.png", output_path],
            capture_output=True,
            timeout=30,
        )
        return output_path

    def enable_talkback(self) -> None:
        """Enable TalkBack accessibility service on the device."""
        # The TalkBack service package name for AOSP (matches AVD)
        self.shell(
            "settings put secure enabled_accessibility_services "
            "com.google.android.marvin.talkback/"
            "com.google.android.marvin.talkback.TalkBackService"
        )
        self.shell("settings put secure accessibility_enabled 1")
        time.sleep(1)  # Give TalkBack time to start

    def disable_talkback(self) -> None:
        """Disable TalkBack after a test suite runs."""
        self.shell("settings put secure enabled_accessibility_services ''")
        self.shell("settings put secure accessibility_enabled 0")

    def launch_app(self, package: str = "org.blindassistant.app") -> None:
        """Launch the Blind Assistant app via ADB intent."""
        self.shell(f"am start -n {package}/.MainActivity")
        time.sleep(2)  # Wait for app to render

    def dump_ui_xml(self) -> str:
        """Dump the current UI hierarchy as XML (uiautomator dump)."""
        self.shell("uiautomator dump /sdcard/ui_dump.xml")
        return self.pull("/sdcard/ui_dump.xml")

    def tap(self, x: int, y: int) -> None:
        """Simulate a tap at the given screen coordinates."""
        self.shell(f"input tap {x} {y}")

    def swipe_right(self) -> None:
        """Simulate TalkBack 'move to next element' (swipe right)."""
        # On a 1080x1920 screen, swipe from left-center to right-center
        self.shell("input swipe 200 960 800 960 300")
        time.sleep(0.5)

    def double_tap(self) -> None:
        """Simulate TalkBack 'activate focused element' (double-tap)."""
        self.shell("input tap 540 960")
        self.shell("input tap 540 960")
        time.sleep(0.3)


@pytest.fixture(scope="session")
def adb_available() -> bool:
    """Return True if ADB is available and a device is connected."""
    if shutil.which("adb") is None:
        return False
    result = subprocess.run(  # noqa: S607
        ["adb", "devices"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # "List of devices attached" is always the first line; count subsequent lines
    lines = [
        line.strip()
        for line in result.stdout.strip().splitlines()
        if line.strip() and "List of devices" not in line
    ]
    return len(lines) > 0


@pytest.fixture(scope="session")
def adb(adb_available: bool) -> ADBClient:  # type: ignore[return]
    """
    Provide an ADB client for the test session.

    Skips the entire test module if ADB is not available or no device is connected.
    In CI this fixture is only exercised by the e2e-android job (release tags only).
    """
    if not adb_available:
        pytest.skip(
            "ADB not available or no Android device/emulator connected. "
            "Android TalkBack E2E tests require: ADB installed + AVD running. "
            "These tests run only in the CI e2e-android job (release tags)."
        )
    return ADBClient()
