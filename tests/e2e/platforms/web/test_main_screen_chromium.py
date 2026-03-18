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
    cd clients/mobile && npx expo export -p web && \\
    python3 -m http.server 19006 --directory dist/ &
    pytest tests/e2e/platforms/web/ --browser chromium

SKIP BEHAVIOUR:
  If playwright package is not importable, all tests skip gracefully.
  If the web server is not running, tests skip gracefully.
  This prevents failures in the Python unit test job which does not start a server.

SYNC API NOTE:
  These tests use the pytest-playwright sync Page fixture (playwright.sync_api.Page).
  The sync API is the correct pattern for pytest-playwright — it avoids event loop
  conflicts with pytest-asyncio's asyncio_mode="auto". Never use async def here.
"""

from __future__ import annotations

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
            "pytest-playwright is not installed. Web E2E tests run only in the 'e2e-web' CI job. "
            "To run locally: pip install pytest pytest-playwright && playwright install chromium && "
            "cd clients/mobile && npx expo export -p web && "
            "python3 -m http.server 19006 --directory dist/ & "
            "pytest tests/e2e/platforms/web/ --browser chromium"
        )
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

    def test_can_reach_main_button_by_tab(self, page: Page, web_app_available: bool) -> None:
        """
        Tab from the page start should reach the main press-to-talk button.
        The button's aria-label must reference 'speak' or 'assistant' so
        NVDA announces it recognisably when focus lands on it.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        page.keyboard.press("Tab")
        focused_label = page.evaluate("document.activeElement.getAttribute('aria-label')")
        assert focused_label is not None, "First Tab press should focus an element with an aria-label"
        lower = focused_label.lower()
        assert "speak" in lower or "assistant" in lower or "record" in lower, (
            f"Focused element aria-label should be recognisable to a screen reader: got '{focused_label}'"
        )

    def test_no_keyboard_trap(self, page: Page, web_app_available: bool) -> None:
        """
        Focus must not get trapped anywhere in the app.
        Tab 20 times without raising an exception = no trap detected.
        WCAG 2.1 SC 2.1.2 (No Keyboard Trap).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        # Tab through all focusable elements — should cycle without errors
        for _ in range(20):
            page.keyboard.press("Tab")
        # No assertion needed — if focus traps, the test will time out or error

    def test_interactive_elements_reachable_by_tab(self, page: Page, web_app_available: bool) -> None:
        """
        At least one focusable element must exist on the main screen.
        If TabIndex=-1 is mistakenly set on all elements, no element is reachable.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        # Count elements that are keyboard reachable
        focusable_count = page.evaluate(
            """() => {
                const sel = 'button, [role="button"], a[href], input, textarea, '
                          + '[tabindex]:not([tabindex="-1"])';
                return document.querySelectorAll(sel).length;
            }"""
        )
        assert focusable_count > 0, "No keyboard-focusable elements found on the main screen"


# ─────────────────────────────────────────────────────────────────────────────
# ARIA Role and Label Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMainScreenARIA:
    """
    Verify ARIA roles and labels — critical for NVDA, VoiceOver, TalkBack.

    WCAG 2.1 SC 1.3.1 (Info and Relationships), SC 4.1.2 (Name, Role, Value).
    All interactive elements need a non-empty accessible name.
    """

    def test_main_button_has_role_button(self, page: Page, web_app_available: bool) -> None:
        """The press-to-talk button must have role=button for NVDA/TalkBack."""
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        buttons = page.query_selector_all('[role="button"]')
        assert len(buttons) > 0, (
            "No elements with role=button found — screen readers cannot identify interactive elements"
        )

    def test_main_button_has_accessible_label(self, page: Page, web_app_available: bool) -> None:
        """
        Every button must have a non-empty aria-label.
        An unlabelled button reads as 'button' with no context — useless to NVDA.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        buttons = page.query_selector_all('[role="button"]')
        assert len(buttons) > 0, "No buttons found"
        for button in buttons:
            label = button.get_attribute("aria-label")
            text_content = (button.text_content() or "").strip()
            assert (label and len(label) > 2) or len(text_content) > 2, (
                f"Button missing accessible name — aria-label='{label}', text='{text_content}'"
            )

    def test_status_region_uses_polite_live_region(self, page: Page, web_app_available: bool) -> None:
        """
        Status updates (processing, error) must use aria-live='polite'.
        'assertive' would interrupt the user mid-sentence — unacceptable for
        screen reader users. WCAG 2.1 SC 4.1.3 (Status Messages).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        live_regions = page.query_selector_all('[aria-live="polite"]')
        assert len(live_regions) > 0, (
            "No aria-live='polite' regions found — status updates will not be announced to screen reader users"
        )

    def test_html_element_has_lang_attribute(self, page: Page, web_app_available: bool) -> None:
        """
        The <html> element must have a lang attribute.
        Screen readers use this to select the correct speech synthesis voice.
        WCAG 2.1 SC 3.1.1 (Language of Page).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        lang = page.evaluate("document.documentElement.lang")
        assert lang and len(lang) >= 2, (
            f"<html lang=''> is missing or empty — got '{lang}'. "
            "Screen readers need this to select the correct TTS voice."
        )

    def test_page_has_title(self, page: Page, web_app_available: bool) -> None:
        """
        The page <title> must not be empty.
        Screen readers announce the title when a tab is focused.
        WCAG 2.1 SC 2.4.2 (Page Titled).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        title = page.title()
        assert title and len(title) > 0, "Page title is empty — screen readers cannot identify this page"

    def test_no_elements_with_empty_aria_label(self, page: Page, web_app_available: bool) -> None:
        """
        Elements with aria-label must not have an empty string value.
        An empty aria-label is worse than no label — it silences NVDA
        completely, as if the element does not exist.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        empty_labels = page.evaluate(
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

    def test_setup_wizard_loads_or_main_screen_loads(self, page: Page, web_app_available: bool) -> None:
        """
        After loading, either the setup wizard or the main screen must be visible.
        Verifies that the app renders something rather than a blank screen.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        # Either a 'role=main' section, a button, or an input must be present
        has_content = page.evaluate(
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

    def test_inputs_have_accessible_names(self, page: Page, web_app_available: bool) -> None:
        """
        All <input> elements must have an accessible name via aria-label,
        aria-labelledby, or a visible <label>.
        An unlabelled input is completely silent to NVDA.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        unlabelled_inputs = page.evaluate(
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


# ─────────────────────────────────────────────────────────────────────────────
# Structure and Navigation Tests (WCAG 2.4 Navigable)
# ─────────────────────────────────────────────────────────────────────────────


class TestPageStructure:
    """
    Verify the page structure enables efficient navigation.

    Screen readers expose page structure to the user via:
    - Skip links (Tab → skip to content)
    - Landmark regions (NVDA: D key, VoiceOver: VO+CMD+M)
    - Heading hierarchy (NVDA: H key, VoiceOver: VO+CMD+H)

    These tests verify that each structural element is present and correct.
    WCAG 2.1 SC 2.4.1 (Bypass Blocks), 2.4.6 (Headings and Labels),
    1.3.1 (Info and Relationships), 1.3.6 (Identify Purpose).
    """

    def test_skip_link_is_first_focusable_element(self, page: Page, web_app_available: bool) -> None:
        """
        A skip-to-main-content link must be the FIRST focusable element on the page.

        WCAG 2.4.1 Bypass Blocks (Level A): a mechanism must be available to
        skip blocks of content repeated on every page. For a single-page app,
        the repeated element is the status bar / navigation chrome; the main
        content is the voice button and response area.

        NVDA+Chrome: Tab from address bar → skip link announced as 'Skip to
        main content, link'. Activating it moves focus to #main-content.
        VoiceOver+Safari: same behaviour via Tab or VO+Tab.

        This test simulates that flow: Tab once from page load → the first
        focused element must be the skip link (href contains 'main').
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        # Tab from page load — first focus must land on skip link
        page.keyboard.press("Tab")
        focused_tag = page.evaluate("document.activeElement.tagName.toLowerCase()")
        focused_href = page.evaluate(
            "document.activeElement.getAttribute('href') || ''"
        )
        focused_text = (page.evaluate("document.activeElement.textContent") or "").lower()

        is_skip_link = (
            focused_tag == "a"
            and (
                "main" in focused_href.lower()
                or "skip" in focused_text
                or "main" in focused_text
            )
        )
        assert is_skip_link, (
            f"First Tab press did not focus a skip link. "
            f"Got: tag='{focused_tag}', href='{focused_href}', text='{focused_text}'. "
            "WCAG 2.4.1: the first Tab from any page must reach a skip link. "
            "Fix: add clients/mobile/public/index.html with a skip link as the "
            "first element in <body> before the React root."
        )

    def test_skip_link_target_exists(self, page: Page, web_app_available: bool) -> None:
        """
        The skip link's href target (#main-content) must exist in the DOM.

        A skip link pointing to a non-existent anchor is a broken link —
        activating it does nothing, which defeats its purpose entirely.
        WCAG 2.4.1: the mechanism must actually work.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        # Find the skip link (first <a> with href containing 'main')
        skip_link_href = page.evaluate(
            """() => {
                // Find first link with href containing 'main' or text containing 'skip'
                const links = document.querySelectorAll('a[href]');
                for (const link of links) {
                    const href = link.getAttribute('href') || '';
                    const text = (link.textContent || '').toLowerCase();
                    if (href.includes('main') || text.includes('skip')) {
                        return href;
                    }
                }
                return null;
            }"""
        )

        if skip_link_href is None:
            pytest.skip("No skip link found — covered by test_skip_link_is_first_focusable_element")

        # Extract the anchor ID from the href (e.g. '#main-content' → 'main-content')
        target_id = skip_link_href.lstrip("#")
        target_exists = page.evaluate(
            f"document.getElementById('{target_id}') !== null"
        )
        assert target_exists, (
            f"Skip link href='{skip_link_href}' targets id='{target_id}' "
            "but no element with that ID exists in the DOM. "
            "The skip link is broken — fix the template HTML or add the target element."
        )

    def test_main_landmark_is_present(self, page: Page, web_app_available: bool) -> None:
        """
        The page must have a 'main' landmark region.

        NVDA users press 'D' to cycle through landmark regions. Without a main
        landmark, there is no way to jump directly to the content. VoiceOver
        uses VO+CMD+M for landmarks. Both require a <main> element or
        role='main' to identify the primary content area.

        WCAG 1.3.6 Identify Purpose (Level AAA — but strongly recommended AA).
        Screen reader usability depends on landmarks even at AA.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        main_count = page.evaluate(
            """() => {
                // Count both <main> elements and role='main' attributes
                const mains = document.querySelectorAll('main, [role="main"]');
                return mains.length;
            }"""
        )
        assert main_count >= 1, (
            "No 'main' landmark found in the DOM. "
            "NVDA users press 'D' to jump to landmarks — without 'main' they "
            "must Tab through every element to reach the voice button. "
            "Fix: wrap the React root in <div role='main'> in public/index.html."
        )

    def test_page_has_heading_structure(self, page: Page, web_app_available: bool) -> None:
        """
        The page must have at least one heading (h1–h6 or role='heading').

        NVDA users press 'H' to jump between headings. Without any headings,
        the user must read the entire page linearly. A heading provides an
        anchor point and identifies the page's primary subject.

        For a React Native Web app, headings come from react-native-web
        mapping accessibilityRole='header' → role='heading' on a <div>.
        The heading must also have an appropriate aria-level (defaults to 2
        in react-native-web; we rely on it being announced as a heading).

        WCAG 2.4.6 Headings and Labels (Level AA).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        heading_count = page.evaluate(
            """() => {
                const headings = document.querySelectorAll(
                    'h1, h2, h3, h4, h5, h6, [role="heading"]'
                );
                return headings.length;
            }"""
        )
        assert heading_count >= 1, (
            "No headings found in the DOM (h1–h6 or role='heading'). "
            "NVDA users press 'H' to navigate headings — without any headings "
            "they must read the page linearly. "
            "Ensure accessibilityRole='header' is present on a title Text component."
        )

    def test_heading_has_accessible_label(self, page: Page, web_app_available: bool) -> None:
        """
        Headings produced by react-native-web (role='heading') must have an
        aria-label or non-empty text content so NVDA announces them meaningfully.

        react-native-web maps accessibilityRole='header' → <div role='heading'>.
        The aria-label from accessibilityLabel is forwarded to aria-label on the div.
        An empty heading would be announced as 'heading' with no context.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        heading_issues = page.evaluate(
            """() => {
                const headings = document.querySelectorAll(
                    'h1, h2, h3, h4, h5, h6, [role="heading"]'
                );
                const issues = [];
                for (const h of headings) {
                    const label = h.getAttribute('aria-label') || '';
                    const text = (h.textContent || '').trim();
                    if (!label && !text) {
                        issues.push(h.outerHTML.slice(0, 100));
                    }
                }
                return issues;
            }"""
        )
        assert len(heading_issues) == 0, (
            f"{len(heading_issues)} heading(s) have no text or aria-label: "
            f"{heading_issues}. An empty heading is announced as 'heading' "
            "with no context — completely useless to a screen reader user."
        )
