"""
E2E iOS VoiceOver Accessibility Tests

Verifies the Blind Assistant iOS app works with VoiceOver, Apple's built-in
screen reader for iPhone and iPad. VoiceOver users navigate by swiping right
to move to the next element and double-tapping to activate.

Tests use xcrun simctl to interact with the iOS Simulator.

Per testing.md: iOS E2E tests use xcrun simctl (iOS Simulator).

NOTE: These tests require:
  1. macOS with Xcode installed
  2. iOS Simulator: `xcrun simctl list devices`
  3. App built for simulator: `cd clients/mobile && npx expo build:ios --simulator`

These tests are skipped in CI until the iOS build is set up (Phase 3).
Only macOS CI agents can run iOS simulator tests.
"""

import pytest

# Skip all tests until iOS build pipeline is set up
pytestmark = pytest.mark.skip(
    reason=(
        "iOS build not yet set up. "
        "Requires macOS + Xcode + iOS Simulator. "
        "ISSUE-010: iOS VoiceOver E2E planned for Phase 3."
    )
)


class TestVoiceOverNavigation:
    """VoiceOver swipe navigation on iPhone simulator."""

    def test_app_launches_without_voiceover_crash(self, simctl):
        """
        App must launch cleanly with VoiceOver enabled.
        VoiceOver is enabled via: xcrun simctl spawn <device> accessibility voiceover enable
        """

    def test_main_button_accessible_label(self, simctl):
        """
        The press-to-talk button must have an accessibilityLabel.
        VoiceOver reads this as: "[label], button. [hint]."
        """

    def test_swipe_right_moves_focus_to_button(self, simctl):
        """
        Swiping right from the title should move focus to the status text,
        then to the main button.
        """


class TestVoiceOverAnnouncements:
    """VoiceOver announcement testing via accessibility notification capture."""

    def test_startup_announcement_is_spoken(self, simctl):
        """
        When the app launches, VoiceOver should announce 'Blind Assistant is ready'.
        This uses UIAccessibilityPostNotification(.announcement) on iOS.
        """

    def test_response_announced_when_ready(self, simctl):
        """
        After an API response arrives, VoiceOver should announce the response text.
        Uses accessibilityLiveRegion = "polite" mapped to iOS accessibility notifications.
        """
