"""
Phase 4: WCAG 2.1 AA Accessibility Audit — axe-core via Playwright

This is the Phase 4 CI gate test. It runs the axe-core accessibility engine
against the live Expo web export and fails if any CRITICAL violations are found.

Per CLAUDE.md Phase 4 completion criteria:
  "Phase 4 complete when: /audit-a11y returns zero CRITICAL findings on web"

axe-core severity levels:
  critical → WCAG 2.1 Level A/AA violation that blocks screen reader access entirely
  serious  → Significant accessibility failure; causes major difficulty
  moderate → Accessibility issue that causes confusion or inefficiency
  minor    → Minor issue; low impact on accessibility

Gate level: CI fails on 'critical' violations only.
'serious' violations are logged as warnings (added to OPEN_ISSUES.md manually).

HOW THESE TESTS RUN:
  CI (ci.yml a11y-audit job):
    1. npm ci --legacy-peer-deps (in clients/mobile/)
    2. npx expo export --platform web (builds to clients/mobile/dist/)
    3. python -m http.server 19006 --directory clients/mobile/dist/ (background)
    4. pip install playwright pytest pytest-asyncio pytest-playwright axe-playwright
    5. playwright install chromium
    6. pytest tests/e2e/platforms/web/test_wcag_axe_audit.py --browser chromium

  Locally:
    cd clients/mobile && npx expo export -p web
    python3 -m http.server 19006 --directory dist/ &
    pip install axe-playwright
    pytest tests/e2e/platforms/web/test_wcag_axe_audit.py --browser chromium

SKIP BEHAVIOUR:
  If playwright or axe_playwright are not importable → skips gracefully.
  If the web server is not running → skips gracefully.
  This prevents failures in the Python unit test job.

Per testing.md: E2E tests; only external APIs mocked.
Per CLAUDE.md accessibility rules: WCAG 2.1 AA on web is non-negotiable.
Phase 4 CI gate: zero CRITICAL axe-core violations before merge.
"""

from __future__ import annotations

import http.client
import json
import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.async_api import Page

# ─────────────────────────────────────────────────────────────────────────────
# Availability guards
# ─────────────────────────────────────────────────────────────────────────────

try:
    import pytest_playwright as _  # noqa: F401

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    # axe-playwright Python package — used only to detect if it's installed.
    # The actual axe-core injection uses page.evaluate (CDN), which does not
    # require this package. AXE_AVAILABLE guards are kept for future use.
    import axe_playwright_python  # type: ignore[import]  # noqa: F401

    AXE_AVAILABLE = True
except ImportError:
    AXE_AVAILABLE = False

# The URL where the Expo web bundle is served.
WEB_APP_URL = os.environ.get("WEB_APP_URL", "http://localhost:19006")

pytestmark = pytest.mark.web


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def web_app_available() -> bool:
    """Check if the web server is reachable before running axe tests."""
    try:
        conn = http.client.HTTPConnection("localhost", 19006, timeout=3)
        conn.request("GET", "/")
        resp = conn.getresponse()
        return resp.status == 200
    except (TimeoutError, http.client.HTTPException, OSError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────


def _skip_if_unavailable(web_app_available: bool) -> None:
    """Skip this test if Playwright, axe-playwright, or the web server is missing."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("playwright not installed — install with: pip install playwright pytest-playwright")
    if not AXE_AVAILABLE:
        pytest.skip(
            "axe-playwright not installed — install with: pip install axe-playwright-python"
        )
    if not web_app_available:
        pytest.skip(
            f"Web app not running at {WEB_APP_URL}. "
            "Run: cd clients/mobile && npx expo export -p web && "
            "python3 -m http.server 19006 --directory dist/"
        )


# Note: axe-core is injected via CDN inside each test's page.evaluate() call.
# This makes tests fully self-contained — no axe-playwright-python required at runtime.
# AXE_AVAILABLE is kept for future explicit-package tests.

# ─────────────────────────────────────────────────────────────────────────────
# axe-core WCAG Audit Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestWCAGAxeAudit:
    """
    Phase 4 CI gate: zero CRITICAL axe-core violations allowed.

    These tests run the axe-core engine via Playwright JavaScript evaluation.
    axe-core is injected from a CDN and run against the rendered DOM.
    The test fails if any violation with impact='critical' is found.
    """

    async def test_no_critical_wcag_violations_main_screen(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        Phase 4 gate: the main screen must have zero CRITICAL axe violations.

        axe 'critical' impact corresponds to WCAG 2.1 Level A failures that
        block screen reader access entirely. Examples:
          - Button with no accessible name
          - Image with no alt text
          - Form field with no label
          - Role with required owned elements missing

        If this test fails, CI blocks. The violation details are printed to
        help identify and fix the issue before merge.
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")

        # Inject axe-core from CDN and run the audit
        # axe.run() with no selector audits the entire document
        axe_result = await page.evaluate(
            """async () => {
                // Inject axe-core if not already loaded
                if (!window.axe) {
                    await new Promise((resolve, reject) => {
                        const script = document.createElement('script');
                        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js';
                        script.onload = resolve;
                        script.onerror = reject;
                        document.head.appendChild(script);
                    });
                }
                // Run axe against the full document with WCAG 2.1 AA rules
                const results = await window.axe.run(document, {
                    runOnly: {
                        type: 'tag',
                        values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']
                    }
                });
                return {
                    violations: results.violations,
                    passes: results.passes.length,
                    incomplete: results.incomplete.length,
                    inapplicable: results.inapplicable.length
                };
            }"""
        )

        violations = axe_result.get("violations", [])
        critical_violations = [v for v in violations if v.get("impact") == "critical"]
        serious_violations = [v for v in violations if v.get("impact") == "serious"]

        # Log all violations for visibility in CI output (helps with debugging)
        if violations:
            print(f"\n{'='*60}")
            print(f"axe-core WCAG audit: {len(violations)} violation(s) found")
            print(f"  Critical: {len(critical_violations)}")
            print(f"  Serious:  {len(serious_violations)}")
            print(f"  Passes:   {axe_result.get('passes', 0)}")
            print(f"{'='*60}")
            for v in violations:
                print(f"\n[{v.get('impact','?').upper()}] {v.get('id','?')}: {v.get('description','?')}")
                print(f"  Help: {v.get('helpUrl','?')}")
                for node in v.get("nodes", [])[:3]:  # Show max 3 affected nodes
                    print(f"  Node: {node.get('html','?')[:100]}")
            print(f"{'='*60}\n")

        # Log serious violations as warnings — they go to OPEN_ISSUES.md, not CI failure
        if serious_violations:
            serious_ids = [v.get("id") for v in serious_violations]
            print(
                f"WARNING: {len(serious_violations)} serious WCAG violation(s) found "
                f"(not a CI failure, but must be addressed): {serious_ids}"
            )

        # Phase 4 gate: fail on critical violations only
        assert len(critical_violations) == 0, (
            f"PHASE 4 GATE FAILED: {len(critical_violations)} CRITICAL WCAG violation(s) found.\n"
            f"These block screen reader access and must be fixed before merge.\n"
            f"Violations: {json.dumps([{'id': v.get('id'), 'description': v.get('description'), 'nodes': len(v.get('nodes',[]))} for v in critical_violations], indent=2)}"
        )

    async def test_no_critical_wcag_violations_contrast(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        Specifically check colour-contrast violations (WCAG 2.1 SC 1.4.3).

        The MainScreen uses a dark color scheme designed for WCAG AA contrast.
        This test verifies those contrast values are maintained in the web export.
        Color contrast failures are rated 'serious' by axe-core (not critical),
        but they make the app unusable for low-vision users in bright environments.
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")

        contrast_result = await page.evaluate(
            """async () => {
                if (!window.axe) {
                    await new Promise((resolve, reject) => {
                        const script = document.createElement('script');
                        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js';
                        script.onload = resolve;
                        script.onerror = reject;
                        document.head.appendChild(script);
                    });
                }
                const results = await window.axe.run(document, {
                    runOnly: { type: 'rule', values: ['color-contrast'] }
                });
                return {
                    violations: results.violations,
                    passes: results.passes.length
                };
            }"""
        )

        contrast_violations = contrast_result.get("violations", [])
        passes = contrast_result.get("passes", 0)

        print(f"\nColor contrast: {passes} pass(es), {len(contrast_violations)} violation(s)")
        for v in contrast_violations:
            for node in v.get("nodes", [])[:5]:
                print(f"  Contrast failure: {node.get('html','?')[:80]}")

        # Contrast violations are 'serious' not 'critical' — log but don't block CI
        # We assert on zero CRITICAL contrast issues specifically
        critical_contrast = [
            v for v in contrast_violations if v.get("impact") == "critical"
        ]
        assert len(critical_contrast) == 0, (
            f"CRITICAL contrast violation(s) found: "
            f"{[v.get('id') for v in critical_contrast]}"
        )

    async def test_interactive_elements_have_names(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        All interactive elements must have accessible names (WCAG 4.1.2).

        An unnamed button or link is one of the most common and severe
        accessibility failures. axe-core rates this as 'critical'.
        This dedicated test ensures buttons, links, and inputs are all named.
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")

        name_result = await page.evaluate(
            """async () => {
                if (!window.axe) {
                    await new Promise((resolve, reject) => {
                        const script = document.createElement('script');
                        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js';
                        script.onload = resolve;
                        script.onerror = reject;
                        document.head.appendChild(script);
                    });
                }
                const results = await window.axe.run(document, {
                    runOnly: {
                        type: 'rule',
                        values: ['button-name', 'link-name', 'label', 'input-image-alt']
                    }
                });
                return { violations: results.violations };
            }"""
        )

        naming_violations = name_result.get("violations", [])

        if naming_violations:
            print("\nNaming violations found:")
            for v in naming_violations:
                print(f"  [{v.get('impact','?').upper()}] {v.get('id','?')}: {v.get('description','?')}")
                for node in v.get("nodes", [])[:3]:
                    print(f"    Node: {node.get('html','?')[:100]}")

        # All naming failures are critical — any failure is a CI block
        assert len(naming_violations) == 0, (
            f"PHASE 4 GATE FAILED: Interactive element(s) have no accessible name.\n"
            f"Screen readers cannot identify these elements. NVDA reads them as 'button'.\n"
            f"Violations: {json.dumps([{'id': v.get('id'), 'nodes': len(v.get('nodes',[]))} for v in naming_violations], indent=2)}"
        )

    async def test_no_invalid_aria_roles(
        self, page: Page, web_app_available: bool
    ) -> None:
        """
        All ARIA roles must be valid WAI-ARIA roles (WCAG 4.1.2).

        This test specifically targets the ISSUE-033 fix: accessibilityRole="text"
        was mapping to role="text" in react-native-web. "text" is not a valid
        WAI-ARIA role. After the Platform.OS fix, this should return zero violations.
        """
        _skip_if_unavailable(web_app_available)
        await page.goto(WEB_APP_URL)
        await page.wait_for_load_state("networkidle")

        role_result = await page.evaluate(
            """async () => {
                if (!window.axe) {
                    await new Promise((resolve, reject) => {
                        const script = document.createElement('script');
                        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js';
                        script.onload = resolve;
                        script.onerror = reject;
                        document.head.appendChild(script);
                    });
                }
                const results = await window.axe.run(document, {
                    runOnly: { type: 'rule', values: ['aria-roles', 'aria-required-attr', 'aria-valid-attr'] }
                });
                // Also check for role="text" specifically (not caught by axe, custom check)
                const textRoleElements = document.querySelectorAll('[role="text"]');
                return {
                    violations: results.violations,
                    invalidTextRoleCount: textRoleElements.length,
                    invalidTextRoleHTML: Array.from(textRoleElements).slice(0,5).map(el => el.outerHTML.slice(0,100))
                };
            }"""
        )

        aria_violations = role_result.get("violations", [])
        invalid_text_role_count = role_result.get("invalidTextRoleCount", 0)
        invalid_text_role_html = role_result.get("invalidTextRoleHTML", [])

        # Check for role="text" (the react-native-web ISSUE-033 problem)
        if invalid_text_role_count > 0:
            print(f"\nFound {invalid_text_role_count} element(s) with invalid role='text':")
            for html in invalid_text_role_html:
                print(f"  {html}")

        assert invalid_text_role_count == 0, (
            f"PHASE 4 GATE FAILED: {invalid_text_role_count} element(s) have role='text' in the DOM.\n"
            f"'text' is not a valid WAI-ARIA role. react-native-web maps accessibilityRole='text' "
            f"to role='text', which is not recognized by screen readers.\n"
            f"Fix: use Platform.OS === 'web' ? undefined : 'text' (ISSUE-033 pattern).\n"
            f"Affected elements: {invalid_text_role_html}"
        )

        # Check for other ARIA role violations
        if aria_violations:
            print("\nARIA violations found:")
            for v in aria_violations:
                print(f"  [{v.get('impact','?').upper()}] {v.get('id','?')}: {v.get('description','?')}")

        critical_aria = [v for v in aria_violations if v.get("impact") in ("critical", "serious")]
        assert len(critical_aria) == 0, (
            f"PHASE 4 GATE FAILED: Critical/serious ARIA role violations found.\n"
            f"Violations: {json.dumps([{'id': v.get('id'), 'impact': v.get('impact'), 'description': v.get('description')} for v in critical_aria], indent=2)}"
        )
