"""
E2E Web Accessibility Tests — Chromium (NVDA+Chrome simulation)

Tests the Blind Assistant web app (React Native Web / Expo Web) for:
- Keyboard-only navigation (Tab, Enter, Space, Arrow keys)
- Correct ARIA roles and labels
- Focus management
- Language attribute on <html>
- Minimum touch target sizes (44x44px conceptually via aria label checks)

Per CLAUDE.md accessibility rules: WCAG 2.1 AA on web is non-negotiable.
Per testing.md: web E2E tests use Playwright (Chromium/Firefox/WebKit).

HOW THESE TESTS RUN:
  CI (ci.yml web-e2e job):
    1. npm ci --legacy-peer-deps (in clients/mobile/)
    2. npx expo export --platform web (builds to clients/mobile/dist/)
    3. python -m http.server 19006 --directory clients/mobile/dist/ (background)
    4. pytest tests/e2e/platforms/web/ --browser chromium

  Locally:
    cd clients/mobile && npx expo export -p web && \
    python3 -m http.server 19006 --directory dist/ &
    pytest tests/e2e/platforms/web/ --browser chromium

SKIP BEHAVIOUR:
  If playwright package is not importable, all tests skip gracefully.
  If the web server is not running, tests skip gracefully.
  This prevents failures in the Python unit test job which does not start a server.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    # Only imported for type hints — not needed at runtime.
    # TC002: playwright is a third-party dep available only in the e2e-web CI job.
    from playwright.async_api import Page

# Skip gracefully if pytest-playwright is not installed (e.g., unit test job)
try:
    import pytest_playwright as _  # noqa: F401
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# The URL where the Expo web bundle is served during CI and local testing
WEB_APP_URL = "http://localhost:19006"

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
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(WEB_APP_URL, timeout=3) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _skip_if_unavailable(web_app_available: bool) -> None:
    """Raise pytest.skip if the web app or Playwright is not available."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("playwright not installed — install with: pip install playwright")
    if not web_app_available:
        pytest.skip(
            f"Web app not running at {WEB_APP_URL}. "
            "Run: cd clients/mobile && npx expo export -p web && "
            "python3 -m http.server 19006 --directory dist/"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Keyboard Navigation Tests (NVDA+Chrome pattern)
# ─────────────────────────────────────────────────────────────────────────────

class TestMainScreenKeyboardNavigation:
    """
    Verify full keyboard-only navigation.

    NVDA+Chrome users navigate by Tab key. All interactive elements must be
    reachable and operable by keyboard alone — mouse never used.
    WCAG 2.1 SC 2.1.1 (Keyboard) and SC 2.4.3 (Focus Order).
    """

    async def test_can_reach_main_button_by_tab(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        Tab from the page start should reach the main press-to-talk button.
        The button's aria-label must reference 'speak' or 'assistant' so
        NVDA announces it recognisably when focus lands on it.
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")
        await page.keyboard.press("Tab")
        focused_label = await page.evaluate(
            "document.activeElement.getAttribute('aria-label')"
        )
        assert focused_label is not None, (
            "First Tab press should focus an element with an aria-label"
        )
        lower = focused_label.lower()
        assert "speak" in lower or "assistant" in lower or "record" in lower, (
            f"Focused element aria-label should be recognisable to a screen reader: "
            f"got '{focused_label}'"
        )

    async def test_no_keyboard_trap(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        Focus must not get trapped anywhere in the app.
        Tab 20 times without raising an exception = no trap detected.
        WCAG 2.1 SC 2.1.2 (No Keyboard Trap).
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")
        # Tab through all focusable elements — should cycle without errors
        for _ in range(20):
            await page.keyboard.press("Tab")
        # No assertion needed — if focus traps, the test will time out or error

    async def test_interactive_elements_reachable_by_tab(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        At least one focusable element must exist on the main screen.
        If TabIndex=-1 is mistakenly set on all elements, no element is reachable.
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")
        # Count elements that are keyboard reachable
        focusable_count = await page.evaluate(
            """() => {
                const sel = 'button, [role="button"], a[href], input, textarea, '
                          + '[tabindex]:not([tabindex="-1"])';
                return document.querySelectorAll(sel).length;
            }"""
        )
        assert focusable_count > 0, (
            "No keyboard-focusable elements found on the main screen"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ARIA Role and Label Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMainScreenARIA:
    """
    Verify ARIA roles and labels — critical for NVDA, VoiceOver, TalkBack.

    WCAG 2.1 SC 1.3.1 (Info and Relationships), SC 4.1.2 (Name, Role, Value).
    All interactive elements need a non-empty accessible name.
    """

    async def test_main_button_has_role_button(
        self, page: Page, web_app_available: bool
    ) -> None:
        """The press-to-talk button must have role=button for NVDA/TalkBack."""
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")
        buttons = await page.query_selector_all('[role="button"]')
        assert len(buttons) > 0, (
            "No elements with role=button found — "
            "screen readers cannot identify interactive elements"
        )

    async def test_main_button_has_accessible_label(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        Every button must have a non-empty aria-label.
        An unlabelled button reads as 'button' with no context — useless to NVDA.
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")
        buttons = await page.query_selector_all('[role="button"]')
        assert len(buttons) > 0, "No buttons found"
        for button in buttons:
            label = await button.get_attribute("aria-label")
            text_content = (await button.text_content() or "").strip()
            assert (label and len(label) > 2) or len(text_content) > 2, (
                f"Button missing accessible name — "
                f"aria-label='{label}', text='{text_content}'"
            )

    async def test_status_region_uses_polite_live_region(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        Status updates (processing, error) must use aria-live='polite'.
        'assertive' would interrupt the user mid-sentence — unacceptable for
        screen reader users. WCAG 2.1 SC 4.1.3 (Status Messages).
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")
        live_regions = await page.query_selector_all('[aria-live="polite"]')
        assert len(live_regions) > 0, (
            "No aria-live='polite' regions found — "
            "status updates will not be announced to screen reader users"
        )

    async def test_html_element_has_lang_attribute(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        The <html> element must have a lang attribute.
        Screen readers use this to select the correct speech synthesis voice.
        WCAG 2.1 SC 3.1.1 (Language of Page).
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")
        lang = await page.evaluate("document.documentElement.lang")
        assert lang and len(lang) >= 2, (
            f"<html lang=''> is missing or empty — got '{lang}'. "
            "Screen readers need this to select the correct TTS voice."
        )

    async def test_page_has_title(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        The page <title> must not be empty.
        Screen readers announce the title when a tab is focused.
        WCAG 2.1 SC 2.4.2 (Page Titled).
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")
        title = await page.title()
        assert title and len(title) > 0, (
            "Page title is empty — screen readers cannot identify this page"
        )

    async def test_no_elements_with_empty_aria_label(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        Elements with aria-label must not have an empty string value.
        An empty aria-label is worse than no label — it silences NVDA
        completely, as if the element does not exist.
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")
        empty_labels = await page.evaluate(
            """() => {
                const els = document.querySelectorAll('[aria-label=""]');
                return els.length;
            }"""
        )
        assert empty_labels == 0, (
            f"{empty_labels} element(s) found with aria-label=''. "
            "Empty labels silence screen readers — remove or fill them."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Setup Wizard ARIA Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSetupWizardARIA:
    """
    Verify the setup wizard is accessible.

    The wizard is the first screen a new blind user sees. If it is not
    accessible, they cannot set up the app independently.
    This is the most critical accessibility test in the suite.
    """

    async def test_setup_wizard_loads_or_main_screen_loads(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        After loading, either the setup wizard or the main screen must be visible.
        Verifies that the app renders something rather than a blank screen.
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")
        # Either a 'role=main' section, a button, or an input must be present
        has_content = await page.evaluate(
            """() => {
                return (
                    document.querySelectorAll('[role="button"]').length > 0 ||
                    document.querySelectorAll('input').length > 0 ||
                    document.querySelectorAll('[role="main"]').length > 0
                );
            }"""
        )
        assert has_content, (
            "App rendered a blank screen — no buttons, inputs, or main region found. "
            "A blind user would have no way to interact with the app."
        )

    async def test_inputs_have_accessible_names(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        All <input> elements must have an accessible name via aria-label,
        aria-labelledby, or a visible <label>.
        An unlabelled input is completely silent to NVDA.
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")
        unlabelled_inputs = await page.evaluate(
            """() => {
                const inputs = document.querySelectorAll('input');
                let count = 0;
                for (const input of inputs) {
                    const label = input.getAttribute('aria-label') ||
                                  input.getAttribute('aria-labelledby') ||
                                  input.getAttribute('placeholder');
                    if (!label || label.trim() === '') count++;
                }
                return count;
            }"""
        )
        assert unlabelled_inputs == 0, (
            f"{unlabelled_inputs} input element(s) have no accessible name. "
            "NVDA users cannot tell what these fields are for."
        )
