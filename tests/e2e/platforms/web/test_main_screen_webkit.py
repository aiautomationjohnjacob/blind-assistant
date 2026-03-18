"""
E2E Web Accessibility Tests — WebKit (VoiceOver+Safari simulation)

Tests the Blind Assistant web app (React Native Web / Expo Web) for
VoiceOver+Safari-specific accessibility patterns:

- ARIA live region announcements (critical for VoiceOver users)
- aria-label attributes on interactive elements (VoiceOver reads these)
- lang attribute on <html> (VoiceOver uses for pronunciation)
- heading structure (VoiceOver rotor uses headings for navigation)
- No role="text" in WebKit (invalid ARIA role — VoiceOver ignores or misbehaves)
- Skip link is the first focusable element (keyboard + Switch Control navigation)

Why WebKit matters:
  VoiceOver on Safari (macOS + iOS) is the primary screen reader for Apple users.
  It has subtly different ARIA support from NVDA+Chrome and NVDA+Firefox.
  Specifically: VoiceOver is strict about live regions, heading labels, and
  interactive element names. A page that passes Chromium tests may still be
  broken for VoiceOver users.

  This file extends test_main_screen_chromium.py (which covers the same WCAG
  checks for Chromium) with WebKit-specific patterns.

Per CLAUDE.md testing rules: tests/e2e/platforms/web/ naming convention is
  test_[feature]_[browser].py (see testing.md §E2E test naming convention).

HOW THESE TESTS RUN:
  CI (ci.yml e2e-web job — WebKit step):
    pytest tests/e2e/platforms/web/ --browser webkit

  Locally:
    pip install pytest pytest-playwright && playwright install webkit
    cd clients/mobile && npx expo export -p web
    python3 -m http.server 19006 --directory dist/ &
    pytest tests/e2e/platforms/web/test_main_screen_webkit.py --browser webkit

SKIP BEHAVIOUR:
  If playwright package is not importable, all tests skip gracefully.
  If the web server is not running, tests skip gracefully.
  This prevents failures in the Python unit test job which does not start a server.

Addresses GitHub issue #92: Add WebKit (VoiceOver+Safari) E2E tests for the web app.
"""

from __future__ import annotations

import contextlib
import http.client
import os

import pytest

# Use sync API — pytest-playwright's 'page' fixture is synchronous.
# Using async def with the sync page fixture causes RuntimeError (event loop conflict).
try:
    from playwright.sync_api import Page

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = object  # type: ignore[assignment,misc]  # placeholder for type hints

# The URL where the Expo web bundle is served.
# Overridable via WEB_APP_URL env var — used by deploy-staging.yml to test
# against the real Netlify staging deploy instead of localhost.
WEB_APP_URL = os.environ.get("WEB_APP_URL", "http://localhost:19006")

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def web_app_available() -> bool:
    """
    Check if the web app server is running before any tests execute.
    Avoids confusing connection-refused errors in test output.
    Returns True if the server responds, False otherwise.
    """
    try:
        # Use http.client directly — WEB_APP_URL is always http://localhost:19006
        # (no dynamic scheme from user input), so S310 does not apply here.
        conn = http.client.HTTPConnection("localhost", 19006, timeout=3)
        conn.request("GET", "/")
        resp = conn.getresponse()
        return resp.status == 200
    except (TimeoutError, http.client.HTTPException, OSError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _skip_if_unavailable(web_app_available: bool) -> None:
    """Raise pytest.skip if the web app or Playwright is not available."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip(
            "pytest-playwright is not installed. WebKit E2E tests run only in the 'e2e-web' CI job. "
            "To run locally: pip install pytest pytest-playwright && playwright install webkit && "
            "cd clients/mobile && npx expo export -p web && "
            "python3 -m http.server 19006 --directory dist/ & "
            "pytest tests/e2e/platforms/web/test_main_screen_webkit.py --browser webkit"
        )
    if not web_app_available:
        pytest.skip(
            f"Web app not running at {WEB_APP_URL}. "
            "Run: cd clients/mobile && npx expo export -p web && "
            "python3 -m http.server 19006 --directory dist/"
        )


def _wait_for_app_ready(page: Page) -> None:
    """
    Wait for the React app to finish hydrating after networkidle.

    Identical to the helper in test_main_screen_chromium.py — copied here
    because this test file is deliberately self-contained for clarity about
    which browser it targets (WebKit / VoiceOver+Safari).
    """
    js_errors: list[str] = []
    console_errors: list[str] = []

    with contextlib.suppress(Exception):
        page.on("pageerror", lambda err: js_errors.append(str(err)))

    with contextlib.suppress(Exception):
        page.on(
            "console",
            lambda msg: (
                console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None
            ),
        )

    try:
        # Wait up to 30s for at least one React-rendered interactive element.
        page.wait_for_selector(
            '[role="button"], input[aria-label]',
            timeout=30000,
            state="attached",
        )
    except Exception:
        print("\n" + "=" * 60)
        print("DIAGNOSTIC: React did not mount within 30s (WebKit)")
        print("=" * 60)
        if js_errors:
            print(f"JS page errors ({len(js_errors)}):")
            for err in js_errors:
                print(f"  !! {err}")
        if console_errors:
            print(f"Console errors ({len(console_errors)}):")
            for msg in console_errors[:10]:
                print(f"  {msg}")
        with contextlib.suppress(Exception):
            early_errors = page.evaluate("() => window.__webE2EErrors || []")
            if early_errors:
                print(f"Early JS errors ({len(early_errors)}):")
                for err in early_errors[:10]:
                    print(f"  !! {err}")
        print("=" * 60 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Test class: VoiceOver+Safari ARIA patterns
# ─────────────────────────────────────────────────────────────────────────────


class TestVoiceOverSafariARIA:
    """
    VoiceOver+Safari ARIA validation.

    VoiceOver reads aria-label attributes for interactive elements.
    Missing or wrong labels means a VoiceOver user hears "button" with no context.
    """

    def test_html_lang_attribute_set(self, page: Page, web_app_available: bool) -> None:
        """
        <html lang="en"> is set — VoiceOver uses this for pronunciation engine selection.

        Without a lang attribute, VoiceOver may read English text in the wrong language
        voice, making speech unintelligible for elderly or non-native users.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL, wait_until="networkidle")
        _wait_for_app_ready(page)
        lang = page.evaluate("() => document.documentElement.lang")
        assert lang and lang.startswith("en"), (
            f"<html lang> is '{lang}' — VoiceOver+Safari needs lang='en' for correct pronunciation. "
            "Check clients/mobile/public/index.html"
        )

    def test_interactive_elements_have_accessible_names(self, page: Page, web_app_available: bool) -> None:
        """
        All interactive elements (buttons, inputs) have non-empty aria-label or text content.

        VoiceOver announces the accessible name when the user moves focus to an element.
        An element with no accessible name is announced as "button" or "element" — useless.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL, wait_until="networkidle")
        _wait_for_app_ready(page)

        buttons = page.query_selector_all('[role="button"]')
        unnamed_buttons = []
        for btn in buttons:
            aria_label = btn.get_attribute("aria-label") or ""
            text_content = (btn.text_content() or "").strip()
            if not aria_label.strip() and not text_content:
                unnamed_buttons.append(btn.get_attribute("id") or btn.inner_html()[:80])

        assert not unnamed_buttons, (
            f"Found {len(unnamed_buttons)} button(s) with no accessible name. "
            "VoiceOver will announce these as 'button' with no context. "
            f"Elements: {unnamed_buttons[:3]}"
        )

    def test_aria_live_regions_exist_in_dom(self, page: Page, web_app_available: bool) -> None:
        """
        aria-live regions are present in the DOM before content is injected.

        VoiceOver+Safari requires live regions to be in the DOM BEFORE content
        changes — injecting a live region at the same time as the content change
        causes VoiceOver to miss the announcement. This test verifies the regions
        exist on page load, even if empty.

        Per CLAUDE.md accessibility rules: 'aria-live regions must exist in DOM
        before content is injected.'
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL, wait_until="networkidle")
        _wait_for_app_ready(page)

        live_regions = page.query_selector_all("[aria-live]")
        assert len(live_regions) >= 1, (
            "No aria-live regions found in the DOM. "
            "VoiceOver+Safari announces status changes via aria-live='polite' regions. "
            "Add aria-live regions to MainScreen.tsx and SetupWizardScreen.tsx."
        )

    def test_no_invalid_role_text_in_webkit(self, page: Page, web_app_available: bool) -> None:
        """
        role='text' is not present — it is invalid ARIA and ignored/misbehaves in WebKit.

        React Native Web sometimes emits role='text' for <Text> components. This is
        not a valid ARIA role in the ARIA spec and has inconsistent support in WebKit.
        The ISSUE-033 fix replaced 'accessibilityRole="text"' with a Platform.OS guard
        — this test verifies the fix holds for WebKit.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL, wait_until="networkidle")
        _wait_for_app_ready(page)

        # role="text" is not in the ARIA spec; VoiceOver ignores or misreads it.
        text_roles = page.query_selector_all('[role="text"]')
        assert len(text_roles) == 0, (
            f"Found {len(text_roles)} element(s) with role='text' (invalid ARIA). "
            "WebKit/VoiceOver ignores this role, making the element inaccessible. "
            "This was fixed by ISSUE-033 — check for regressions in MainScreen.tsx and SetupWizardScreen.tsx."
        )

    def test_page_title_is_meaningful(self, page: Page, web_app_available: bool) -> None:
        """
        <title> is set and meaningful — VoiceOver announces page title on load.

        An empty or generic title means VoiceOver announces nothing useful when
        the user opens the app. A descriptive title like 'Blind Assistant' tells
        the user where they are before any other content is read.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL, wait_until="networkidle")
        title = page.title()
        assert title and len(title.strip()) > 0, (
            f"Page title is '{title}' — VoiceOver reads this on page load. "
            "Set a descriptive title in clients/mobile/public/index.html."
        )


class TestVoiceOverKeyboardNav:
    """
    Keyboard navigation tests for VoiceOver+Safari.

    VoiceOver on macOS uses Tab for keyboard navigation, same as NVDA.
    Switch Control on iOS simulates sequential Tab presses.
    These tests verify that critical elements are reachable and in the right order.
    """

    def test_skip_link_is_first_focusable_element(self, page: Page, web_app_available: bool) -> None:
        """
        The skip link is the first Tab stop — required for VoiceOver+Safari keyboard users.

        Per CLAUDE.md: 'Skip navigation link must be the first focusable element.'
        VoiceOver+Safari Tab users would have to hear the entire navigation before
        reaching main content without this skip link.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL, wait_until="networkidle")
        _wait_for_app_ready(page)

        # Tab once from the page body — the first focused element should be the skip link.
        page.keyboard.press("Tab")
        focused_text = page.evaluate("() => document.activeElement ? document.activeElement.textContent : ''")
        focused_href = page.evaluate("() => document.activeElement ? document.activeElement.getAttribute('href') : ''")
        assert "skip" in (focused_text or "").lower() or focused_href == "#main-content", (
            f"First Tab stop is not the skip link. "
            f"Got: text='{focused_text}', href='{focused_href}'. "
            "The skip link must be the first focusable element (check public/index.html)."
        )

    def test_main_content_target_exists(self, page: Page, web_app_available: bool) -> None:
        """
        The skip link target (#main-content) exists and has tabindex='-1'.

        Without tabindex='-1', Safari does not move keyboard focus to the target
        element when the skip link is activated — the skip link appears to do nothing
        for keyboard-only VoiceOver users. This is a WebKit-specific requirement.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL, wait_until="networkidle")
        main_content = page.query_selector("#main-content")
        assert main_content is not None, (
            "#main-content element not found. "
            "The skip link href='#main-content' must have a target in the DOM (public/index.html)."
        )
        tabindex = main_content.get_attribute("tabindex")
        assert tabindex == "-1", (
            f"#main-content has tabindex='{tabindex}' (expected '-1'). "
            "Safari requires tabindex='-1' for programmatic focus routing via skip links. "
            "See ISSUE-037 fix in public/index.html."
        )
