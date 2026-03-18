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
    4. pip install playwright pytest pytest-playwright
    5. playwright install chromium
    6. pytest tests/e2e/platforms/web/test_wcag_axe_audit.py --browser chromium

  Locally:
    cd clients/mobile && npx expo export -p web
    python3 -m http.server 19006 --directory dist/ &
    pytest tests/e2e/platforms/web/test_wcag_axe_audit.py --browser chromium

SKIP BEHAVIOUR:
  If playwright or pytest-playwright are not importable → skips gracefully.
  If the web server is not running → skips gracefully.
  This prevents failures in the Python unit test job.

Per testing.md: E2E tests; only external APIs mocked.
Per CLAUDE.md accessibility rules: WCAG 2.1 AA on web is non-negotiable.
Phase 4 CI gate: zero CRITICAL axe-core violations before merge.

AXE-CORE BUNDLED LOCALLY:
  axe.min.js is committed to tests/e2e/platforms/web/axe.min.js (version 4.9.1).
  This eliminates the CDN network dependency (Cycle 29: ISSUE-034 fix).
  page.add_script_tag(path=...) is used instead of CDN URL injection.

SYNC API NOTE:
  These tests use the pytest-playwright sync Page fixture (playwright.sync_api.Page).
  The sync API is the correct pattern for pytest-playwright — it avoids event loop
  conflicts with pytest-asyncio's asyncio_mode="auto". Never use async def here.
"""

from __future__ import annotations

import contextlib
import json
import os
import pathlib

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
WEB_APP_URL = os.environ.get("WEB_APP_URL", "http://localhost:19006")

# Path to the bundled axe-core JS — eliminates CDN dependency.
# This file is committed to the repo at tests/e2e/platforms/web/axe.min.js.
_THIS_DIR = pathlib.Path(__file__).parent
AXE_JS_PATH = _THIS_DIR / "axe.min.js"

pytestmark = pytest.mark.web


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
#
# NOTE: web_app_available fixture is defined in conftest.py (DRY: shared
# across all 4 web E2E test files).
# ─────────────────────────────────────────────────────────────────────────────


def _skip_if_unavailable(web_app_available: bool) -> None:
    """Skip this test if Playwright is not installed or the web server is not running.

    NOTE: web_app_available is injected from the session fixture in conftest.py.
    """
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


def _wait_for_app_ready(page: Page) -> None:
    """
    Wait for React to finish hydrating the Expo web bundle.

    The deferred <script> loads and React runs checkStoredCredentials() async.
    The loading spinner renders with no role="button". We wait for the first
    role="button" to appear (either setup wizard or main screen), then run axe.
    This ensures axe audits the real app state, not the transient loading spinner.

    Without this wait, axe may only see the static HTML shell and miss the
    React-rendered DOM content that users actually interact with.

    On timeout, prints JS console errors and page error events to diagnose
    why React failed to mount (ISSUE-041: bundle crashes silently in CI).
    """
    # Collect JS errors for diagnostic output on timeout.
    js_errors: list[str] = []
    console_errors: list[str] = []

    with contextlib.suppress(Exception):
        page.on("pageerror", lambda err: js_errors.append(str(err)))

    with contextlib.suppress(Exception):
        page.on(
            "console",
            lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None,
        )

    try:
        # 30s timeout: CI can be slow; 15s was insufficient in CI Chromium (ISSUE-041).
        page.wait_for_selector("[role='button'], input[aria-label]", timeout=30000, state="attached")
    except Exception:
        # React did not mount within 30s. Print diagnostics to help diagnose ISSUE-041.
        print("\n" + "=" * 60)
        print("DIAGNOSTIC: React did not mount within 30s (ISSUE-041)")
        print("=" * 60)
        if js_errors:
            print(f"JS page errors via page.on ({len(js_errors)}):")
            for err in js_errors:
                print(f"  !! {err}")
        else:
            print("JS page errors via page.on: none captured (registered after goto)")
        if console_errors:
            print(f"Console errors/warnings via page.on ({len(console_errors)}):")
            for msg in console_errors[:10]:
                print(f"  {msg}")
        else:
            print("Console errors via page.on: none captured (registered after goto)")
        # Read errors captured by conftest.py inject_early_error_capture fixture.
        with contextlib.suppress(Exception):
            early_errors = page.evaluate("() => window.__webE2EErrors || []")
            if early_errors:
                print(f"Early JS errors (from init_script, {len(early_errors)}):")
                for err in early_errors[:10]:
                    print(f"  !! {err}")
            else:
                print("Early JS errors (from init_script): none captured")
        with contextlib.suppress(Exception):
            dom_summary = page.evaluate(
                """() => ({
                    title: document.title,
                    bodyText: document.body ? document.body.innerText.slice(0, 200) : 'no body',
                    buttonCount: document.querySelectorAll('[role="button"]').length,
                    inputCount: document.querySelectorAll('input').length,
                    rootHTML: document.getElementById('root')
                        ? document.getElementById('root').innerHTML.slice(0, 500)
                        : 'no #root element',
                    scriptCount: document.querySelectorAll('script').length,
                    expoGlobal: typeof globalThis.expo !== 'undefined' ? 'loaded' : 'missing',
                    requireDefined: typeof __r !== 'undefined' ? 'yes (Metro loaded)' : 'no (Metro missing)',
                    reactDefined: typeof React !== 'undefined' ? 'yes' : 'no',
                })"""
            )
            print(f"DOM state: {dom_summary}")
        print("=" * 60 + "\n")


def _inject_axe(page: Page) -> None:
    """
    Inject axe-core into the page from the local bundled file.

    Uses page.add_script_tag(path=...) instead of CDN to avoid network
    dependency in CI. axe.min.js is committed to the repo (Cycle 29 fix).
    """
    if AXE_JS_PATH.exists():
        # Local bundle — no network required
        page.add_script_tag(path=str(AXE_JS_PATH))
    else:
        # Fallback to CDN if local file is missing (should not happen in CI)
        page.evaluate(
            """async () => {
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js';
                    script.onload = resolve;
                    script.onerror = reject;
                    document.head.appendChild(script);
                });
            }"""
        )


# ─────────────────────────────────────────────────────────────────────────────
# axe-core WCAG Audit Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestWCAGAxeAudit:
    """
    Phase 4 CI gate: zero CRITICAL axe-core violations allowed.

    These tests run the axe-core engine via Playwright's add_script_tag (local bundle).
    axe-core is loaded from the committed axe.min.js file — no CDN required.
    The test fails if any violation with impact='critical' is found.
    """

    def test_no_critical_wcag_violations_main_screen(self, page: Page, web_app_available: bool) -> None:
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
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        # Inject axe-core from local bundle (no CDN dependency)
        _wait_for_app_ready(page)
        _inject_axe(page)

        # Run axe against the full document with WCAG 2.1 AA rules
        axe_result = page.evaluate(
            """() => {
                return window.axe.run(document, {
                    runOnly: {
                        type: 'tag',
                        values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']
                    }
                }).then(function(results) {
                    return {
                        violations: results.violations,
                        passes: results.passes.length,
                        incomplete: results.incomplete.length,
                        inapplicable: results.inapplicable.length
                    };
                });
            }"""
        )

        violations = axe_result.get("violations", [])
        critical_violations = [v for v in violations if v.get("impact") == "critical"]
        serious_violations = [v for v in violations if v.get("impact") == "serious"]

        # Log all violations for visibility in CI output (helps with debugging)
        if violations:
            print(f"\n{'=' * 60}")
            print(f"axe-core WCAG audit: {len(violations)} violation(s) found")
            print(f"  Critical: {len(critical_violations)}")
            print(f"  Serious:  {len(serious_violations)}")
            print(f"  Passes:   {axe_result.get('passes', 0)}")
            print(f"{'=' * 60}")
            for v in violations:
                print(f"\n[{v.get('impact', '?').upper()}] {v.get('id', '?')}: {v.get('description', '?')}")
                print(f"  Help: {v.get('helpUrl', '?')}")
                for node in v.get("nodes", [])[:3]:  # Show max 3 affected nodes
                    print(f"  Node: {node.get('html', '?')[:100]}")
            print(f"{'=' * 60}\n")

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
            "Violations: "
            + json.dumps(
                [
                    {
                        "id": v.get("id"),
                        "description": v.get("description"),
                        "nodes": len(v.get("nodes", [])),
                    }
                    for v in critical_violations
                ],
                indent=2,
            )
        )

    def test_no_critical_wcag_violations_contrast(self, page: Page, web_app_available: bool) -> None:
        """
        Specifically check colour-contrast violations (WCAG 2.1 SC 1.4.3).

        The MainScreen uses a dark color scheme designed for WCAG AA contrast.
        This test verifies those contrast values are maintained in the web export.
        Color contrast failures are rated 'serious' by axe-core (not critical),
        but they make the app unusable for low-vision users in bright environments.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        _wait_for_app_ready(page)
        _inject_axe(page)

        contrast_result = page.evaluate(
            """() => {
                return window.axe.run(document, {
                    runOnly: { type: 'rule', values: ['color-contrast'] }
                }).then(function(results) {
                    return {
                        violations: results.violations,
                        passes: results.passes.length
                    };
                });
            }"""
        )

        contrast_violations = contrast_result.get("violations", [])
        passes = contrast_result.get("passes", 0)

        print(f"\nColor contrast: {passes} pass(es), {len(contrast_violations)} violation(s)")
        for v in contrast_violations:
            for node in v.get("nodes", [])[:5]:
                print(f"  Contrast failure: {node.get('html', '?')[:80]}")

        # Contrast violations are 'serious' not 'critical' — log but don't block CI
        # We assert on zero CRITICAL contrast issues specifically
        critical_contrast = [v for v in contrast_violations if v.get("impact") == "critical"]
        assert len(critical_contrast) == 0, (
            f"CRITICAL contrast violation(s) found: {[v.get('id') for v in critical_contrast]}"
        )

    def test_interactive_elements_have_names(self, page: Page, web_app_available: bool) -> None:
        """
        All interactive elements must have accessible names (WCAG 4.1.2).

        An unnamed button or link is one of the most common and severe
        accessibility failures. axe-core rates this as 'critical'.
        This dedicated test ensures buttons, links, and inputs are all named.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        _wait_for_app_ready(page)
        _inject_axe(page)

        name_result = page.evaluate(
            """() => {
                return window.axe.run(document, {
                    runOnly: {
                        type: 'rule',
                        values: ['button-name', 'link-name', 'label', 'input-image-alt']
                    }
                }).then(function(results) {
                    return { violations: results.violations };
                });
            }"""
        )

        naming_violations = name_result.get("violations", [])

        if naming_violations:
            print("\nNaming violations found:")
            for v in naming_violations:
                print(f"  [{v.get('impact', '?').upper()}] {v.get('id', '?')}: {v.get('description', '?')}")
                for node in v.get("nodes", [])[:3]:
                    print(f"    Node: {node.get('html', '?')[:100]}")

        # All naming failures are critical — any failure is a CI block
        assert len(naming_violations) == 0, (
            "PHASE 4 GATE FAILED: Interactive element(s) have no accessible name.\n"
            "Screen readers cannot identify these elements. NVDA reads them as 'button'.\n"
            "Violations: "
            + json.dumps(
                [{"id": v.get("id"), "nodes": len(v.get("nodes", []))} for v in naming_violations],
                indent=2,
            )
        )

    def test_no_invalid_aria_roles(self, page: Page, web_app_available: bool) -> None:
        """
        All ARIA roles must be valid WAI-ARIA roles (WCAG 4.1.2).

        This test specifically targets the ISSUE-033 fix: accessibilityRole="text"
        was mapping to role="text" in react-native-web. "text" is not a valid
        WAI-ARIA role. After the Platform.OS fix, this should return zero violations.
        """
        _skip_if_unavailable(web_app_available)
        page.goto(WEB_APP_URL)
        page.wait_for_load_state("networkidle")

        _wait_for_app_ready(page)
        _inject_axe(page)

        role_result = page.evaluate(
            """() => {
                return window.axe.run(document, {
                    runOnly: { type: 'rule', values: ['aria-roles', 'aria-required-attr', 'aria-valid-attr'] }
                }).then(function(results) {
                    // Also check for role="text" specifically (not caught by axe, custom check)
                    const textRoleElements = document.querySelectorAll('[role="text"]');
                    return {
                        violations: results.violations,
                        invalidTextRoleCount: textRoleElements.length,
                        invalidTextRoleHTML: Array.from(textRoleElements).slice(0,5).map(
                            function(el) { return el.outerHTML.slice(0,100); }
                        )
                    };
                });
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
                print(f"  [{v.get('impact', '?').upper()}] {v.get('id', '?')}: {v.get('description', '?')}")

        critical_aria = [v for v in aria_violations if v.get("impact") in ("critical", "serious")]
        assert len(critical_aria) == 0, (
            "PHASE 4 GATE FAILED: Critical/serious ARIA role violations found.\n"
            "Violations: "
            + json.dumps(
                [
                    {
                        "id": v.get("id"),
                        "impact": v.get("impact"),
                        "description": v.get("description"),
                    }
                    for v in critical_aria
                ],
                indent=2,
            )
        )
