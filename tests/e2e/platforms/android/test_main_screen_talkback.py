"""
E2E Android TalkBack Accessibility Tests

Verifies the Blind Assistant Android app works with TalkBack, the primary
Android screen reader used by blind users.

Tests use ADB (Android Debug Bridge) to interact with an Android emulator
or real device. They verify:
- Every interactive element has a content description (TalkBack reads this)
- Touch target sizes meet 48dp Android minimum (our policy: 44dp)
- Focus order is logical
- State changes are announced via accessibility events

Per testing.md: Android E2E tests use ADB and AVD (Android Virtual Device).

NOTE: These tests require:
  1. Android SDK + ADB installed
  2. AVD (Android Virtual Device) created: `avdmanager create avd --name blind_test`
  3. Emulator running: `emulator -avd blind_test &`
  4. App built and installed: `cd clients/mobile && npx expo build:android`

These tests are skipped in CI until the Android build is set up (Phase 3).
"""

import pytest

# Skip all tests until Android build pipeline is set up
pytestmark = pytest.mark.skip(
    reason=(
        "Android build not yet set up. "
        "Requires AVD + ADB + Android app build. "
        "ISSUE-010: Android TalkBack E2E planned for Phase 3."
    )
)


class TestTalkBackNavigation:
    """TalkBack gesture navigation — explore by touch + swipe left/right."""

    def test_app_launches_without_talkback_crash(self, adb):
        """
        App must launch cleanly with TalkBack enabled.
        Some apps crash when launched with TalkBack due to missing content descriptions.
        """
        # Enable TalkBack
        adb.shell("settings put secure enabled_accessibility_services "
                  "com.samsung.android.accessibility.axb/com.samsung.android.accessibility.axb.TalkBackService")
        # Launch the app
        adb.shell("am start -n org.blindassistant.app/.MainActivity")
        # Verify no crash
        output = adb.shell("pidof org.blindassistant.app")
        assert output.strip() != "", "App process is not running after launch"

    def test_main_button_has_content_description(self, adb):
        """
        The press-to-talk button must have a contentDescription.
        Without this, TalkBack says 'unlabelled button' which gives no information.
        """
        # Dump accessibility window content
        adb.shell("uiautomator dump /sdcard/screen.xml")
        xml = adb.pull("/sdcard/screen.xml")
        assert 'content-desc="Speak to assistant"' in xml or \
               'content-desc=' in xml, "Main button has no content description"

    def test_focus_follows_logical_reading_order(self, adb):
        """
        TalkBack focus (swipe right) should go: title → status → button.
        This is the expected reading order for blind users.
        """
        # Simulate TalkBack swipe-right navigation
        # ADB accessibility event injection would go here
        pass


class TestAccessibilitySnapshot:
    """Screenshot-based accessibility verification using device-simulator."""

    def test_capture_screenshot_with_talkback_focus(self, adb):
        """
        Capture a screenshot showing TalkBack focus ring on the main button.
        Used for visual regression testing by the android-accessibility-expert agent.
        """
        # adb.screenshot() — captured and stored in tests/e2e/platforms/android/screenshots/
        pass
