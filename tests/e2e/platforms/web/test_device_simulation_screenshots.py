"""
Device Simulation Screenshots — Web (Playwright, all browsers)

This file captures named screenshots of key UI states for CI artifact review.
It is NOT a functional E2E test — it does NOT assert accessibility correctness.
Its sole purpose is to produce visual evidence of how the app renders in each
browser so that contributors and accessibility reviewers can see the UI without
running the app locally.

Screenshots are saved to: device-sim-screenshots/{browser}/{state}.png
These are uploaded as the 'device-sim-screenshots-{run_number}' CI artifact
by the e2e-web job in ci.yml.

WHICH STATES ARE CAPTURED:
  1. initial_load   — app immediately after page load (before React hydrates)
  2. app_ready      — app after React finishes hydrating (setup wizard or main screen)
  3. setup_wizard   — setup wizard screen (first-run flow for new users)
  4. main_screen    — main screen (after setup, when user can speak to the AI)

WHY THIS MATTERS FOR BLIND USERS:
  Sighted contributors review screenshots to catch layout regressions that
  automated tests may not catch. NVDA/TalkBack/VoiceOver users cannot review
  screenshots, but sighted co-contributors can — closing the feedback loop
  between the two groups.

HOW THESE TESTS RUN:
  CI (ci.yml e2e-web job) — runs after the functional accessibility tests:
    1. npm ci --legacy-peer-deps (in clients/mobile/)
    2. npx expo export --platform web (builds to clients/mobile/dist/)
    3. python -m http.server 19006 --directory clients/mobile/dist/ (background)
    4. pytest tests/e2e/platforms/web/test_device_simulation_screenshots.py
       --browser chromium --browser firefox --browser webkit
       --screenshot always

  Locally:
    cd clients/mobile && npx expo export -p web
    python3 -m http.server 19006 --directory dist/ &
    pytest tests/e2e/platforms/web/test_device_simulation_screenshots.py \\
      --browser chromium

SKIP BEHAVIOUR:
  If playwright package is not importable → skips gracefully.
  If the web server is not running → skips gracefully.

SYNC API NOTE:
  Uses the pytest-playwright sync Page fixture. Never use async def here.

Addresses: P3 — Device simulation CI (PRIORITY_STACK.md)
"""

from __future__ import annotations

import contextlib
import os
import pathlib

import pytest

try:
    from playwright.sync_api import Page

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = object  # type: ignore[assignment,misc]

WEB_APP_URL = os.environ.get("WEB_APP_URL", "http://localhost:19006")

# Directory where device simulation screenshots are saved.
# Relative to the project root (where pytest is run from in CI).
SCREENSHOT_DIR = pathlib.Path("device-sim-screenshots")


def _skip_if_unavailable(web_app_available: bool) -> None:
    """Skip if Playwright or the web server is unavailable."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip(
            "pytest-playwright is not installed. "
            "Run: pip install pytest pytest-playwright && playwright install chromium"
        )
    if not web_app_available:
        pytest.skip(
            f"Web app not running at {WEB_APP_URL}. "
            "Run: cd clients/mobile && npx expo export -p web && "
            "python3 -m http.server 19006 --directory dist/"
        )


def _browser_name(page: Page) -> str:
    """Return the browser name for screenshot file naming."""
    if not PLAYWRIGHT_AVAILABLE:
        return "unknown"
    # page.context.browser.browser_type.name gives 'chromium', 'firefox', 'webkit'
    try:
        return page.context.browser.browser_type.name  # type: ignore[union-attr]
    except Exception:
        return "unknown"


def _save_screenshot(page: Page, state: str) -> pathlib.Path:
    """Save a screenshot to device-sim-screenshots/{browser}/{state}.png.

    Returns the path of the saved screenshot.
    The parent directory is created automatically.
    """
    browser = _browser_name(page)
    out_dir = SCREENSHOT_DIR / browser
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{state}.png"
    page.screenshot(path=str(path), full_page=False)
    return path


def _wait_for_app_ready(page: Page) -> None:
    """Wait for the React app to hydrate and render an interactive element.

    Uses a 30s timeout — CI can be slow.
    If React does not mount, swallows the error; the screenshot will show what went wrong.
    """
    with contextlib.suppress(Exception):
        page.wait_for_selector(
            '[role="button"], input[aria-label]',
            timeout=30000,
            state="attached",
        )


class TestDeviceSimulationScreenshots:
    """Capture named screenshots for CI artifact review.

    These tests always pass — they are screenshot-only.
    A test fails only if Playwright itself errors (e.g., page crash).
    """

    def test_capture_initial_load_chromium(self, page: Page, web_app_available: bool) -> None:
        """Capture app state immediately after page.goto() — before React hydrates.

        This shows the static HTML shell (skip link, loading spinner placeholder).
        Useful for verifying that the page structure is correct before JS runs.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        # Do NOT wait for networkidle — capture the pre-hydration state.
        path = _save_screenshot(page, "01_initial_load")
        assert path.exists(), f"Screenshot not saved: {path}"

    def test_capture_app_ready(self, page: Page, web_app_available: bool) -> None:
        """Capture app state after React finishes hydrating.

        Shows either the SetupWizardScreen (first-run) or MainScreen (returning user).
        This is the state that NVDA/TalkBack users interact with.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        _wait_for_app_ready(page)
        path = _save_screenshot(page, "02_app_ready")
        assert path.exists(), f"Screenshot not saved: {path}"

    def test_capture_setup_wizard_token_step(self, page: Page, web_app_available: bool) -> None:
        """Capture the setup wizard token-entry step.

        The setup wizard is the first screen new users see. It includes:
        - A progress indicator (step 1 of 3)
        - A text input for the API connection code
        - A 'Save and continue' button

        This screenshot lets sighted contributors verify the setup wizard
        is visually clear and not cluttered.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        _wait_for_app_ready(page)
        # The setup wizard is shown on first load when no credentials are stored.
        # Check if a text input is visible (setup wizard) vs a speak button (main screen).
        # contextlib.suppress: if the selector times out, input_visible stays False.
        input_visible = False
        with contextlib.suppress(Exception):
            page.wait_for_selector("input", timeout=5000, state="visible")
            input_visible = True
        # Save regardless — if it's the main screen we still capture that state.
        state_name = "03_setup_wizard" if input_visible else "03_main_screen_no_setup"
        path = _save_screenshot(page, state_name)
        assert path.exists(), f"Screenshot not saved: {path}"

    def test_capture_main_screen(self, page: Page, web_app_available: bool) -> None:
        """Capture the main screen that users interact with daily.

        The main screen includes:
        - A heading: 'Blind Assistant'
        - A 'Speak' button (the primary action — Press to start, press again to send)
        - An aria-live region for transcripts and AI responses
        - A 'Settings' button

        This screenshot verifies the main screen is uncluttered and button labels
        are visually clear for sighted co-users and accessibility reviewers.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        _wait_for_app_ready(page)
        # Attempt to reach the main screen by simulating the token setup flow.
        # If we are already on the main screen (button with speak-related text), capture.
        # If we are on the setup wizard, try to proceed.
        # contextlib.suppress: query/click errors are non-fatal — we still capture.
        with contextlib.suppress(Exception):
            # Check if there's a text input (setup wizard)
            input_el = page.query_selector("input")
            if input_el:
                # Fill in a dummy token to proceed past step 1
                input_el.fill("test-token")
                # Click the first button (Save and continue)
                btn = page.query_selector('[role="button"]')
                if btn:
                    btn.click()
                    # Wait briefly for next step
                    page.wait_for_timeout(2000)
        path = _save_screenshot(page, "04_main_screen")
        assert path.exists(), f"Screenshot not saved: {path}"

    def test_capture_mobile_viewport(self, page: Page, web_app_available: bool) -> None:
        """Capture app at mobile viewport size (375x812 — iPhone 12/13 Pro).

        The web app targets TalkBack+Chrome on Android and VoiceOver+Safari on iPhone.
        This screenshot verifies the layout works at mobile viewport sizes.
        Complements the desktop screenshots to catch responsive layout regressions.
        """
        _skip_if_unavailable(web_app_available)
        page.set_viewport_size({"width": 375, "height": 812})
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        _wait_for_app_ready(page)
        path = _save_screenshot(page, "05_mobile_viewport_375x812")
        assert path.exists(), f"Screenshot not saved: {path}"

    def test_capture_tablet_viewport(self, page: Page, web_app_available: bool) -> None:
        """Capture app at tablet viewport size (768x1024 — iPad).

        iPad VoiceOver users interact with the web app at tablet viewport.
        This screenshot helps verify touch target sizes and layout proportions.
        """
        _skip_if_unavailable(web_app_available)
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        _wait_for_app_ready(page)
        path = _save_screenshot(page, "06_tablet_viewport_768x1024")
        assert path.exists(), f"Screenshot not saved: {path}"

    def test_screenshot_dir_contains_screenshots(self, page: Page, web_app_available: bool) -> None:
        """Verify that at least one screenshot was saved by previous tests.

        This is a sanity check that the screenshot pipeline is working end-to-end.
        Run this test LAST in the class.
        """
        _skip_if_unavailable(web_app_available)
        browser = _browser_name(page)
        out_dir = SCREENSHOT_DIR / browser
        if out_dir.exists():
            screenshots = list(out_dir.glob("*.png"))
            assert len(screenshots) >= 1, (
                f"Expected at least 1 screenshot in {out_dir}, found 0. The screenshot pipeline may be broken."
            )
        else:
            # Directory doesn't exist yet (tests run in a different order in some runners).
            # Not a failure — just capture a baseline screenshot now.
            page.goto(WEB_APP_URL)
            page.wait_for_load_state("networkidle")
            _wait_for_app_ready(page)
            path = _save_screenshot(page, "00_sanity_check")
            assert path.exists(), f"Screenshot not saved: {path}"
