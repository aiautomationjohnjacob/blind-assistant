"""
Shared fixtures for iOS VoiceOver E2E tests.

Provides the `simctl` fixture that wraps xcrun simctl commands
for interacting with the iOS Simulator.

Requires:
  - macOS with Xcode installed
  - At least one iOS Simulator booted:
      xcrun simctl list devices | grep Booted
  - App installed on the simulator:
      cd clients/mobile && npx expo run:ios --simulator

These tests are skipped automatically when xcrun is not available,
which is always the case on Linux CI runners (iOS requires macOS).
The iOS E2E job runs on a separate macOS GitHub Actions runner.

Per testing.md: iOS E2E tests use xcrun simctl.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time

import pytest


class SimctlClient:
    """Thin wrapper around xcrun simctl for iOS Simulator interaction."""

    def __init__(self, device_udid: str = "booted") -> None:
        """
        Initialise simctl client for the given device UDID.

        'booted' targets the currently booted simulator automatically.
        """
        self._udid = device_udid

    def shell(self, command: str) -> str:
        """Run a simctl command and return stdout."""
        result = subprocess.run(
            ["xcrun", "simctl", *command.split()],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout

    def list_devices(self) -> list[dict]:  # type: ignore[type-arg]
        """Return a list of available simulator devices."""
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout)
        devices = []
        for runtime_devices in data.get("devices", {}).values():
            devices.extend(runtime_devices)
        return devices

    def get_booted_device(self) -> dict | None:  # type: ignore[type-arg]
        """Return the first booted simulator device, or None."""
        for device in self.list_devices():
            if device.get("state") == "Booted":
                return device
        return None

    def launch_app(self, bundle_id: str = "org.blindassistant.app") -> None:
        """Launch the Blind Assistant app on the booted simulator."""
        subprocess.run(
            ["xcrun", "simctl", "launch", self._udid, bundle_id],
            capture_output=True,
            timeout=30,
        )
        time.sleep(2)

    def terminate_app(self, bundle_id: str = "org.blindassistant.app") -> None:
        """Terminate the app on the booted simulator."""
        subprocess.run(
            ["xcrun", "simctl", "terminate", self._udid, bundle_id],
            capture_output=True,
            timeout=10,
        )

    def enable_voiceover(self) -> None:
        """Enable VoiceOver on the booted simulator."""
        subprocess.run(
            ["xcrun", "simctl", "spawn", self._udid,
             "notifyutil", "-p", "com.apple.accessibility.voiceover.notification.start"],
            capture_output=True,
            timeout=10,
        )
        time.sleep(1)

    def disable_voiceover(self) -> None:
        """Disable VoiceOver on the booted simulator."""
        subprocess.run(
            ["xcrun", "simctl", "spawn", self._udid,
             "notifyutil", "-p", "com.apple.accessibility.voiceover.notification.stop"],
            capture_output=True,
            timeout=10,
        )

    def screenshot(self, output_path: str = "/tmp/simctl_screenshot.png") -> str:
        """Capture a simulator screenshot and save it to the given path."""
        subprocess.run(
            ["xcrun", "simctl", "io", self._udid, "screenshot", output_path],
            capture_output=True,
            timeout=15,
        )
        return output_path

    def get_accessibility_tree(self, bundle_id: str = "org.blindassistant.app") -> str:
        """
        Return the accessibility tree for the app via the Accessibility Inspector CLI.

        This uses the axe command-line tool if available, or falls back to
        simctl spawn to dump the UI hierarchy via the accessibility API.
        """
        # Try using the built-in accessibility audit (Xcode 15+)
        result = subprocess.run(
            ["xcrun", "simctl", "accessibility", self._udid, "audit", "--bundle-id", bundle_id],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
        # Fallback: dump the view hierarchy via simctl
        result = subprocess.run(
            ["xcrun", "simctl", "io", self._udid, "enumerate", bundle_id],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout


@pytest.fixture(scope="session")
def simctl_available() -> bool:
    """Return True if xcrun simctl is available and a simulator is booted."""
    if shutil.which("xcrun") is None:
        return False
    # Check that at least one simulator is booted
    result = subprocess.run(
        ["xcrun", "simctl", "list", "devices", "--json"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode != 0:
        return False
    try:
        data = json.loads(result.stdout)
        for runtime_devices in data.get("devices", {}).values():
            for device in runtime_devices:
                if device.get("state") == "Booted":
                    return True
        return False
    except (json.JSONDecodeError, KeyError):
        return False


@pytest.fixture(scope="session")
def simctl(simctl_available: bool) -> SimctlClient:  # type: ignore[return]
    """
    Provide a simctl client for the test session.

    Skips the entire test module if xcrun is not available or no simulator is booted.
    iOS tests require macOS with Xcode and a running iOS Simulator.
    These tests run only in the macOS CI workflow (separate from the main ci.yml).
    """
    if not simctl_available:
        pytest.skip(
            "xcrun simctl not available or no iOS Simulator booted. "
            "iOS VoiceOver E2E tests require: macOS + Xcode + booted iOS Simulator. "
            "To start: xcrun simctl boot 'iPhone 15' && open -a Simulator"
        )
    return SimctlClient()
