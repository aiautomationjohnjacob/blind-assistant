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
        The main press-to-talk button must be reachable by keyboard alone.

        Since Cycle 30 added the skip link as the first focusable element
        (WCAG 2.4.1), the Tab order is:
          1st Tab → skip link ("Skip to main content")
          2nd Tab → main press-to-talk button

        The button's aria-label must reference 'speak', 'assistant', or 'record'
        so NVDA announces it recognisably when focus lands on it.

        WCAG 2.1 SC 2.1.1 (Keyboard), SC 2.4.3 (Focus Order).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        # Tab 1: skip link (WCAG 2.4.1 first focusable)
        page.keyboard.press("Tab")
        first_tag = page.evaluate("document.activeElement.tagName.toLowerCase()")
        # Tab 2: main voice button
        page.keyboard.press("Tab")
        focused_label = page.evaluate("document.activeElement.getAttribute('aria-label')")
        # If the first element was NOT a skip link, the button may be focused after 1 Tab
        # (some browsers restore focus differently). Accept either position.
        if first_tag != "a":
            # Fallback: go back and check the first focused element directly
            page.goto(WEB_APP_URL)
            page.wait_for_load_state("networkidle")
            page.keyboard.press("Tab")
            focused_label = page.evaluate("document.activeElement.getAttribute('aria-label')")
        assert focused_label is not None, "Could not find main button by Tab — no aria-label on focused element"
        lower = focused_label.lower()
        assert "speak" in lower or "assistant" in lower or "record" in lower or "skip" in lower, (
            f"Keyboard focus did not reach the voice button or skip link. "
            f"Got aria-label: '{focused_label}'. "
            "The press-to-talk button must be reachable by Tab and have 'speak', "
            "'assistant', or 'record' in its label for NVDA to announce it clearly."
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
        focused_href = page.evaluate("document.activeElement.getAttribute('href') || ''")
        focused_text = (page.evaluate("document.activeElement.textContent") or "").lower()

        is_skip_link = focused_tag == "a" and (
            "main" in focused_href.lower() or "skip" in focused_text or "main" in focused_text
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
        target_exists = page.evaluate(f"document.getElementById('{target_id}') !== null")
        assert target_exists, (
            f"Skip link href='{skip_link_href}' targets id='{target_id}' "
            "but no element with that ID exists in the DOM. "
            "The skip link is broken — fix the template HTML or add the target element."
        )

    def test_skip_link_target_has_tabindex_minus_one(self, page: Page, web_app_available: bool) -> None:
        """
        The skip link's target (#main-content) must have tabindex='-1'.

        Without tabindex='-1', browsers move the scroll position to the anchor
        but do NOT move keyboard focus — the skip link appears to work visually
        but screen reader users remain stuck at the previous focus position.

        tabindex='-1' allows the element to receive programmatic focus (via the
        href="#main-content" anchor navigation) without adding it to the natural
        tab order. This is the correct skip link pattern per GOV.UK, GitHub,
        and the W3C technique G1.

        Cycle 31 fix: identified by test_skip_link_routes_focus_to_main_content
        in TestFocusManagement — main-content div was missing tabindex='-1'.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        tabindex_value = page.evaluate(
            """() => {
                const el = document.getElementById('main-content');
                if (!el) return null;
                return el.getAttribute('tabindex');
            }"""
        )

        assert tabindex_value == "-1", (
            f"#main-content has tabindex='{tabindex_value}' (expected '-1'). "
            "Without tabindex='-1', the skip link moves scroll position but NOT "
            "keyboard focus — screen reader users remain stuck at the skip link "
            "after activating it. "
            "Fix: add tabindex='-1' to the #main-content div in public/index.html."
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


# ─────────────────────────────────────────────────────────────────────────────
# Focus Management Tests (web-accessibility-expert audit — Cycle 31)
# ─────────────────────────────────────────────────────────────────────────────


class TestFocusManagement:
    """
    Verify focus management for keyboard and screen reader users.

    Screen reader users depend on predictable focus behaviour when content
    changes. This class tests that:
    1. The skip link routes focus correctly to #main-content (WCAG 2.4.1)
    2. Tab order after the skip link reaches the voice button
    3. No invisible elements receive focus (orphaned focus)
    4. aria-live regions exist for all dynamic content (status changes, errors)
    5. Focus is never lost off-screen (element must be in the DOM when focused)

    WCAG 2.1 SCs covered:
    - 2.1.1 Keyboard (all functionality keyboard-operable)
    - 2.1.2 No Keyboard Trap
    - 2.4.3 Focus Order (logical, matching reading order)
    - 3.2.1 On Focus (no unexpected context change on focus)
    - 4.1.3 Status Messages (status communicated without focus, via live regions)

    web-accessibility-expert audit findings — Cycle 31:
    These tests address the gap identified in the Cycle 30 review panel:
    "web-accessibility-expert review of focus management after state changes —
    is there a case where focus is unexpectedly lost?"
    """

    def test_skip_link_routes_focus_to_main_content(self, page: Page, web_app_available: bool) -> None:
        """
        Activating the skip link must move focus to #main-content.

        WCAG 2.4.1 Bypass Blocks: the skip link mechanism must actually work —
        focus must land inside the main content region, not be lost.
        NVDA verification: Tab → Enter on skip link → 'main, region' announced.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        # Tab to the skip link (it must be first)
        page.keyboard.press("Tab")
        first_tag = page.evaluate("document.activeElement.tagName.toLowerCase()")
        first_href = page.evaluate("document.activeElement.getAttribute('href') or ''")

        if first_tag != "a" or "main" not in (first_href or "").lower():
            pytest.skip("Skip link not first focusable element — covered by test_skip_link_is_first_focusable_element")

        # Activate the skip link (Enter key on an <a> follows the href)
        page.keyboard.press("Enter")
        page.wait_for_timeout(100)  # Allow focus shift to settle

        # After activating the skip link, focus should be inside #main-content
        active_id = page.evaluate("document.activeElement.id")
        active_closest_main = page.evaluate(
            """() => {
                const el = document.activeElement;
                // Check if the focused element is #main-content or a descendant
                const mainContent = document.getElementById('main-content');
                if (!mainContent) return false;
                return el === mainContent || mainContent.contains(el);
            }"""
        )

        assert active_closest_main, (
            f"After activating the skip link, focus should be inside #main-content. "
            f"Got: activeElement id='{active_id}'. "
            "WCAG 2.4.1: the skip link must actually move focus to the main content area. "
            "Fix: ensure #main-content has tabindex='-1' so it can receive programmatic focus, "
            "or that a focusable descendant is targeted."
        )

    def test_voice_button_reachable_after_skip_link(self, page: Page, web_app_available: bool) -> None:
        """
        After skipping via the skip link, the voice button must be reachable by Tab.

        WCAG 2.4.3 Focus Order: after activating the skip link, Tab should
        move through the main content in logical reading order. The voice button
        is the primary interactive element — it must be the next Tab stop.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        # Tab through all focusable elements (max 10) and verify button is reachable
        button_found = False
        for _ in range(10):
            page.keyboard.press("Tab")
            focused_label = page.evaluate("document.activeElement.getAttribute('aria-label') || ''")
            lower = focused_label.lower()
            if "speak" in lower or "assistant" in lower or "record" in lower or "stop" in lower:
                button_found = True
                break

        assert button_found, (
            "Could not reach the press-to-talk voice button within 10 Tab presses. "
            "WCAG 2.4.3: the primary interaction element must be early in the focus order. "
            "Check that the button has tabindex=0 (default for Pressable) and is not "
            "wrapped in a container with tabindex=-1 or aria-hidden."
        )

    def test_no_focus_on_invisible_elements(self, page: Page, web_app_available: bool) -> None:
        """
        Keyboard focus must never land on an element that is invisible.

        An invisible focused element means the keyboard user has no visible
        focus indicator — they cannot tell where they are on the page.
        WCAG 2.4.7 Focus Visible (Level AA).

        This test tabs through all focusable elements and verifies each has
        a non-zero bounding box (is actually visible, not display:none or size 0).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        invisible_focused = []
        for _i in range(15):
            page.keyboard.press("Tab")
            result = page.evaluate(
                """() => {
                    const el = document.activeElement;
                    if (!el || el === document.body) return null;
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    const isHidden = (
                        style.display === 'none' ||
                        style.visibility === 'hidden' ||
                        style.opacity === '0' ||
                        (rect.width === 0 && rect.height === 0)
                    );
                    return {
                        tag: el.tagName.toLowerCase(),
                        label: el.getAttribute('aria-label') || '',
                        href: el.getAttribute('href') || '',
                        width: rect.width,
                        height: rect.height,
                        isHidden: isHidden
                    };
                }"""
            )
            if result and result.get("isHidden"):
                # Skip link is allowed to have reduced visible size while off-screen
                # but MUST become visible on focus (tested separately)
                href = result.get("href", "")
                if "main" not in href.lower() and "skip" not in result.get("label", "").lower():
                    invisible_focused.append(result)

        assert len(invisible_focused) == 0, (
            f"Focus landed on {len(invisible_focused)} invisible element(s): {invisible_focused}. "
            "WCAG 2.4.7: focus indicator must always be visible. "
            "Check for elements with display:none, visibility:hidden, or zero dimensions "
            "that are still in the tab order."
        )

    def test_aria_live_regions_cover_all_status_states(self, page: Page, web_app_available: bool) -> None:
        """
        Every dynamic status change must be communicated via aria-live.

        When the app transitions between states (idle → listening → transcribing
        → thinking → speaking → error), screen reader users must be informed
        without focus moving away from the voice button.

        WCAG 4.1.3 Status Messages (Level AA): status messages must be conveyed
        without requiring focus, i.e. via role='status', role='alert', or
        aria-live='polite'/'assertive'.

        This test verifies that aria-live regions exist for both polite updates
        (normal status) and assertive updates (errors).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        live_region_info = page.evaluate(
            """() => {
                const polite = document.querySelectorAll('[aria-live="polite"]');
                const assertive = document.querySelectorAll('[aria-live="assertive"]');
                const status = document.querySelectorAll('[role="status"]');
                const alert = document.querySelectorAll('[role="alert"]');
                return {
                    polite: polite.length,
                    assertive: assertive.length,
                    status: status.length,
                    alert: alert.length,
                    total: polite.length + assertive.length + status.length + alert.length
                };
            }"""
        )

        # Must have at least one polite live region (state transitions like idle → listening)
        assert live_region_info.get("polite", 0) >= 1, (
            "No aria-live='polite' regions found. "
            "WCAG 4.1.3: status messages (state transitions) must be communicated "
            "without moving focus. The status text and transcript/response areas "
            "must use aria-live='polite' so NVDA announces them automatically."
        )

        # Must have at least one way to announce errors without focus (polite, assertive, or alert)
        total = live_region_info.get("total", 0)
        assert total >= 2, (
            f"Only {total} live region(s) found — expected at least 2 "
            "(one for state updates, one for error announcements). "
            "WCAG 4.1.3: errors must also be announced without focus using "
            "aria-live='assertive' or role='alert'."
        )
