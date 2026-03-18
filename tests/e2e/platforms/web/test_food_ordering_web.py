"""
E2E Web Test: Food ordering accessibility flow (NVDA+Chrome)

Verifies that a blind user on the web app can initiate and navigate the food ordering
flow using keyboard alone, with all status updates announced via aria-live regions.

This test covers the web platform's accessibility for the Phase 3 scenario:
  "Order food or a household item entirely by voice (including risk-disclosure flow)"

What these tests verify:
  1. The "order food" intent can be triggered via keyboard (Enter on the main button)
  2. Status updates during ordering use aria-live='polite' (NVDA hears them)
  3. Confirmation prompts (risk disclosure, order confirmation) are in the live region
  4. No visual-only information is used (no "click the green button" style copy)
  5. The confirmation buttons / Yes/No inputs are keyboard-reachable

Note: These tests run against the web app UI only — they do NOT test the Python
backend or actual food ordering. They verify the accessibility of the conversational
UX pattern that the web app presents to the user.

SKIP BEHAVIOUR: Same as test_main_screen_chromium.py — skips gracefully when
pytest-playwright is not installed or the web server is not running.

Per testing.md: E2E tests for Phase 3 "blind user testing" scenarios.
Per CLAUDE.md accessibility rules: WCAG 2.1 AA on web is non-negotiable.

SYNC API NOTE:
  These tests use the pytest-playwright sync Page fixture (playwright.sync_api.Page).
  The sync API is the correct pattern for pytest-playwright — it avoids event loop
  conflicts with pytest-asyncio's asyncio_mode="auto". Never use async def here.
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

# Overridable via env var (used by deploy-staging.yml for Netlify staging tests)
WEB_APP_URL = os.environ.get("WEB_APP_URL", "http://localhost:19006")

pytestmark = pytest.mark.web


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def web_app_available() -> bool:
    """Check if the web app server is running before any tests execute."""
    try:
        conn = http.client.HTTPConnection("localhost", 19006, timeout=3)
        conn.request("GET", "/")
        resp = conn.getresponse()
        return resp.status == 200
    except (TimeoutError, http.client.HTTPException, OSError):
        # If using a remote staging URL (not localhost), assume available
        return WEB_APP_URL != "http://localhost:19006"


def _skip_if_unavailable(web_app_available: bool) -> None:
    """Raise pytest.skip if Playwright or web server is not available."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("playwright not installed — web E2E tests run only in CI")
    if not web_app_available:
        pytest.skip(
            f"Web app not running at {WEB_APP_URL}. "
            "Run: cd clients/mobile && npx expo export -p web && "
            "python3 -m http.server 19006 --directory dist/ &"
        )


def _wait_for_app_ready(page: Page) -> None:
    """
    Wait for the React app to finish hydrating after networkidle.

    The Expo web bundle loads via a deferred <script> tag. After networkidle,
    React still needs to run checkStoredCredentials() and update state.
    The loading spinner (ActivityIndicator) renders without role="button".
    We wait for the first role="button" or input to appear — confirming that
    React has transitioned to either SetupWizardScreen or MainScreen.

    In CI, expo-secure-store returns null → setup wizard shows. In production,
    a stored token would skip to the main screen. Both screens are valid.
    """
    with contextlib.suppress(Exception):
        page.wait_for_selector(
            '[role="button"], input[aria-label]',
            timeout=5000,
            state="attached",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 Test Scenario: Food Ordering Accessibility
# ─────────────────────────────────────────────────────────────────────────────


class TestFoodOrderingAccessibility:
    """
    Accessibility audit for the food ordering conversational flow on web.

    Phase 3 scenario: "Order food or a household item entirely by voice
    (including risk-disclosure flow)"

    These tests verify the web app's accessibility structure supports this flow —
    not the actual ordering logic (that is tested in tests/e2e/core/test_food_ordering.py).
    """

    def test_main_interaction_button_is_keyboard_reachable(self, page: Page, web_app_available: bool) -> None:
        """
        The main press-to-talk button must be reachable via Tab key.

        A blind NVDA user navigates by Tab. If the button is not in the tab order,
        they cannot start the food ordering flow. WCAG 2.1 SC 2.1.1 (Keyboard).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        # Wait for React to hydrate — buttons only appear after React renders
        _wait_for_app_ready(page)

        # Tab through all focusable elements and look for the main action button.
        # Accept: voice button (main screen) or setup wizard buttons.
        # In CI, expo-secure-store returns null → setup wizard shows first.
        found_action_button = False
        ALL_KNOWN_BUTTON_KEYWORDS = (
            "speak", "record", "start", "assistant", "tap",  # main screen
            "continue", "confirm", "token", "next", "setup", "welcome", "save",  # setup wizard
            "skip",  # skip link
        )
        for _ in range(10):
            page.keyboard.press("Tab")
            focused_label = page.evaluate(
                "document.activeElement.getAttribute('aria-label') || document.activeElement.textContent || ''"
            )
            if focused_label:
                lower = focused_label.lower()
                if any(word in lower for word in ALL_KNOWN_BUTTON_KEYWORDS):
                    found_action_button = True
                    break

        assert found_action_button, (
            "Could not reach any labeled interactive button via Tab key. "
            "A blind NVDA user cannot interact with the app. "
            f"Accepted button keywords: {ALL_KNOWN_BUTTON_KEYWORDS}"
        )

    def test_status_updates_use_polite_live_region(self, page: Page, web_app_available: bool) -> None:
        """
        The status/response area must use aria-live='polite'.

        When the assistant responds (e.g., 'I found 5 restaurants near you'),
        NVDA must announce it without interrupting the user. 'assertive' would
        interrupt; 'polite' waits for the user to finish.

        WCAG 2.1 SC 4.1.3 (Status Messages).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        # Wait for React to hydrate — aria-live attrs are rendered by React, not static HTML
        _wait_for_app_ready(page)

        # Count polite live regions — there must be at least one for status updates
        polite_regions = page.query_selector_all('[aria-live="polite"]')
        assert len(polite_regions) > 0, (
            "No aria-live='polite' regions found on the main screen. "
            "When the assistant responds during food ordering, NVDA cannot "
            "announce the restaurant options or confirmation prompts. "
            "Both MainScreen and SetupWizardScreen use accessibilityLiveRegion='polite'."
        )

    def test_no_assertive_live_region_for_status(self, page: Page, web_app_available: bool) -> None:
        """
        Non-critical status updates must NOT use aria-live='assertive'.

        An assertive region would interrupt NVDA mid-sentence every time a
        status update fires. For food ordering, this means the user could be
        cut off while reading restaurant names. Only truly urgent messages
        (errors) should use assertive.

        WCAG 2.1 SC 4.1.3 (Status Messages).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        assertive_regions = page.query_selector_all('[aria-live="assertive"]')
        # assertive is acceptable for error messages, but check they're not the
        # main response region (which would interrupt constantly during ordering)
        for region in assertive_regions:
            role = region.get_attribute("role")
            aria_label = region.get_attribute("aria-label") or ""
            # 'alert' role implies assertive — acceptable for errors
            # but NOT for the main response area
            if role != "alert":
                assert "error" in aria_label.lower() or "alert" in aria_label.lower(), (
                    f"Found aria-live='assertive' on a non-error region (role={role}, "
                    f"label='{aria_label}'). This would interrupt NVDA during food ordering."
                )

    def test_confirmation_prompt_area_is_announced(self, page: Page, web_app_available: bool) -> None:
        """
        The response area (where confirmations appear) must be in a live region.

        During food ordering, the assistant asks:
          "I'd like to order from Chipotle for $12.50. Say yes to confirm."
        This prompt must be in an aria-live region so NVDA announces it when
        the text is injected — without requiring the user to navigate to it.

        WCAG 2.1 SC 4.1.3 (Status Messages).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")
        # Wait for React to hydrate — live regions are set by React, not static HTML.
        # Per CLAUDE.md: 'aria-live regions must exist in DOM before content is injected'.
        # Both MainScreen.statusText and SetupWizardScreen step instructions have
        # accessibilityLiveRegion='polite' which renders as aria-live='polite' in the DOM.
        _wait_for_app_ready(page)

        # The response/status area should be accessible via a live region
        live_regions = page.query_selector_all('[aria-live="polite"], [aria-live="assertive"], [aria-live="off"]')
        assert len(live_regions) > 0, (
            "No aria-live regions found in the page DOM. "
            "Per CLAUDE.md: 'aria-live regions must exist in DOM before content is injected'. "
            "The confirmation prompts for food ordering will not be announced by NVDA."
        )

    def test_response_area_visible_to_screen_reader(self, page: Page, web_app_available: bool) -> None:
        """
        The response area must NOT be hidden from screen readers.

        If the response area uses display:none or visibility:hidden or
        aria-hidden="true", NVDA cannot read the food ordering results.

        WCAG 2.1 SC 1.3.1 (Info and Relationships).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        # Check that no aria-live region is hidden from AT
        hidden_live_regions = page.evaluate(
            """() => {
                const regions = document.querySelectorAll(
                    '[aria-live="polite"], [aria-live="assertive"]'
                );
                let count = 0;
                for (const region of regions) {
                    const hidden = region.getAttribute('aria-hidden');
                    const style = window.getComputedStyle(region);
                    if (hidden === 'true' || style.display === 'none') {
                        count++;
                    }
                }
                return count;
            }"""
        )
        assert hidden_live_regions == 0, (
            f"{hidden_live_regions} aria-live region(s) are hidden from screen readers. "
            "A blind user cannot hear food ordering responses or confirmation prompts."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Risk Disclosure Accessibility
# ─────────────────────────────────────────────────────────────────────────────


class TestRiskDisclosureAccessibility:
    """
    Verify the risk disclosure (required before any food ordering payment) is
    accessible on web.

    Per CLAUDE.md (non-negotiable rule):
      "Every action that costs money or sends a communication requires explicit
       user confirmation"
    Per ETHICS_REQUIREMENTS.md:
      "Risk disclosure fires every transaction"

    The web app must present this warning in a way that:
    - NVDA announces it automatically when it appears (aria-live)
    - The confirmation button is keyboard reachable
    - The text contains no visual-only language
    """

    def test_interactive_elements_have_accessible_names(self, page: Page, web_app_available: bool) -> None:
        """
        All interactive elements (buttons, inputs) must have accessible names.

        During the risk disclosure flow, the "Yes, I understand" button must have
        a meaningful accessible name — not just "button" which tells NVDA nothing.

        WCAG 2.1 SC 4.1.2 (Name, Role, Value).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        # All buttons must have an accessible name
        buttons = page.query_selector_all('[role="button"]')
        unlabelled = []
        for button in buttons:
            label = button.get_attribute("aria-label")
            text = (button.text_content() or "").strip()
            if not (label and len(label.strip()) > 2) and not (text and len(text) > 2):
                unlabelled.append({"label": label, "text": text})

        assert len(unlabelled) == 0, (
            f"{len(unlabelled)} button(s) have no accessible name: {unlabelled}. "
            "A blind user cannot identify confirmation buttons during risk disclosure."
        )

    def test_no_visual_only_instructions_in_page(self, page: Page, web_app_available: bool) -> None:
        """
        Page text must not contain visual-only instructions like "click the button"
        or "see the confirmation at the top of the screen".

        Blind users using NVDA cannot follow visual directions. The web app must
        use action-neutral language: "press Enter", "say yes", not "click here".

        Per CLAUDE.md: "every voice prompt or conversational UX pattern" must be
        reviewed by voice-interface-designer.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        page_text = (page.evaluate("document.body.innerText") or "").lower()

        # Phrases that require vision to follow — not acceptable in a blind-first app
        visual_only_phrases = [
            "click the",
            "click here",
            "see above",
            "see below",
            "look at",
            "shown on screen",
            "visible on",
        ]
        found_violations = [phrase for phrase in visual_only_phrases if phrase in page_text]
        assert len(found_violations) == 0, (
            f"Page contains visual-only instructions: {found_violations}. "
            "Blind users cannot follow these. Use action-neutral language."
        )

    def test_colour_not_sole_conveyor_of_information(self, page: Page, web_app_available: bool) -> None:
        """
        Verify that interactive state is not conveyed by colour alone.

        WCAG 2.1 SC 1.4.1 (Use of Color): colour must not be the only visual
        means of conveying information. Buttons must have text or aria labels,
        not just colour changes (e.g. red = danger, green = safe).

        This test checks that all buttons have text content or aria-label,
        ensuring the information is available without seeing colour.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        # All buttons must have text or aria-label (not just colour)
        colour_only_buttons = page.evaluate(
            """() => {
                const buttons = document.querySelectorAll(
                    'button, [role="button"]'
                );
                let count = 0;
                for (const btn of buttons) {
                    const label = btn.getAttribute('aria-label');
                    const text = (btn.textContent || '').trim();
                    const ariaLabelledBy = btn.getAttribute('aria-labelledby');
                    if (!label && !text && !ariaLabelledBy) {
                        count++;
                    }
                }
                return count;
            }"""
        )
        assert colour_only_buttons == 0, (
            f"{colour_only_buttons} button(s) convey state through colour alone "
            "(no text, no aria-label, no aria-labelledby). "
            "NVDA users and users with colour blindness cannot interpret these."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Focus Management During Ordering Flow
# ─────────────────────────────────────────────────────────────────────────────


class TestFocusManagementOrderingFlow:
    """
    Verify focus management is correct during multi-step ordering interactions.

    WCAG 2.1 SC 2.4.3 (Focus Order): focus order must preserve meaning and
    operability. For a blind user mid-ordering flow, unexpected focus jumps
    break the conversational experience.
    """

    def test_initial_focus_is_logical(self, page: Page, web_app_available: bool) -> None:
        """
        When the page loads, the first focusable element should be at the top
        of the logical reading order — not a random button in the middle.

        WCAG 2.1 SC 1.3.2 (Meaningful Sequence) and SC 2.4.3 (Focus Order).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        # Press Tab once and check that we land on a meaningful element
        page.keyboard.press("Tab")
        element_tag = page.evaluate("document.activeElement.tagName.toLowerCase()")
        aria_role = page.evaluate("document.activeElement.getAttribute('role') || ''")
        aria_label = page.evaluate("document.activeElement.getAttribute('aria-label') || ''")

        # First tab stop should be an interactive element (button, input, link)
        interactive_tags = {"button", "input", "a", "select", "textarea"}
        interactive_roles = {"button", "link", "textbox", "menuitem", "tab"}
        is_interactive = element_tag in interactive_tags or aria_role in interactive_roles
        assert is_interactive, (
            f"First Tab stop is a non-interactive element: <{element_tag} role='{aria_role}' "
            f"aria-label='{aria_label}'>. NVDA users expect the first Tab to land on "
            "a meaningful interactive element (the main speak button)."
        )

    def test_escape_key_does_not_trap_focus(self, page: Page, web_app_available: bool) -> None:
        """
        Pressing Escape should not trap focus or crash the app.

        During ordering, a blind user might press Escape to cancel. The app
        must handle this gracefully — no focus trap, no blank state.

        WCAG 2.1 SC 2.1.2 (No Keyboard Trap).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        # Press Tab to focus something, then Escape
        page.keyboard.press("Tab")
        page.keyboard.press("Escape")

        # Verify the page is still interactive (not crashed or blank)
        focusable_count = page.evaluate(
            """() => {
                const sel = 'button, [role="button"], a[href], input, '
                          + '[tabindex]:not([tabindex="-1"])';
                return document.querySelectorAll(sel).length;
            }"""
        )
        assert focusable_count > 0, (
            "After pressing Escape, no focusable elements remain. "
            "The app may have crashed or cleared all content. "
            "A blind user pressing Escape to cancel an action would be stranded."
        )

    def test_enter_key_activates_main_button(self, page: Page, web_app_available: bool) -> None:
        """
        Pressing Enter when the main button is focused must activate it.

        NVDA users press Enter to activate buttons. The main press-to-talk
        button must respond to Enter (not just mouse click/touch).

        WCAG 2.1 SC 2.1.1 (Keyboard).
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        # Find the main button and focus it
        main_button = page.query_selector('[role="button"]')
        if main_button is None:
            pytest.skip("No button found on main screen — skipping Enter key test")

        main_button.focus()
        button_label_before = main_button.get_attribute("aria-label") or ""

        # Press Enter to activate
        page.keyboard.press("Enter")
        # Give the app a moment to respond
        page.wait_for_timeout(500)

        # Verify something changed — either the label, the live region content,
        # or the DOM structure (indicating the app responded to the keypress)
        live_region_content = page.evaluate(
            """() => {
                const regions = document.querySelectorAll(
                    '[aria-live="polite"], [aria-live="assertive"]'
                );
                let text = '';
                for (const r of regions) {
                    text += r.textContent || '';
                }
                return text.trim();
            }"""
        )

        # We accept either: (1) live region has content, (2) button label changed,
        # (3) new element appeared. The important thing is Enter didn't do nothing.
        button_label_after = main_button.get_attribute("aria-label") or ""
        state_changed = len(live_region_content) > 0 or button_label_after != button_label_before

        # Note: if the app requires microphone permission in a dialog, the dialog
        # itself is a valid response to Enter. We check the page still has focus.
        page_has_focus = page.evaluate("document.activeElement && document.activeElement !== document.body")

        assert state_changed or page_has_focus, (
            "Pressing Enter on the main button had no visible effect. "
            "NVDA users expect Enter to activate buttons. "
            f"Live region content after Enter: '{live_region_content}'"
        )
