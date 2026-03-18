"""
conftest.py — Web E2E test fixtures.

Provides a `page` fixture stub that skips gracefully when pytest-playwright
is not installed. In CI, pytest-playwright IS installed (see ci.yml e2e-web job).
In the standard unit test run, pytest-playwright is NOT installed, so these
tests skip cleanly without errors.

This avoids the "fixture 'page' not found" error that occurs when these tests
are collected by the main pytest run without pytest-playwright present.

ISSUE-041 DIAGNOSTIC:
An `autouse` fixture (`inject_early_error_capture`) is added when playwright IS
available. It calls `context.add_init_script()` BEFORE any page navigates, so that
uncaught JS errors during the initial page load (including Expo bundle failures) are
stored in `window.__wepE2EErrors`. These are read back in `_wait_for_app_ready`
when React fails to mount. Without this, `page.on("pageerror")` misses errors that
happen before the listener is attached.
"""

from __future__ import annotations

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Detect whether pytest-playwright is available
# ─────────────────────────────────────────────────────────────────────────────

try:
    # pytest-playwright registers the `page` fixture as a plugin.
    # Importing it here confirms it is installed and its fixtures are active.
    import pytest_playwright  # noqa: F401

    PYTEST_PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PYTEST_PLAYWRIGHT_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Stub `page` fixture — only active when pytest-playwright is NOT installed
# ─────────────────────────────────────────────────────────────────────────────

if not PYTEST_PLAYWRIGHT_AVAILABLE:

    @pytest.fixture
    def page() -> None:
        """
        Stub fixture: skips all web E2E tests when pytest-playwright is not installed.

        In CI (e2e-web job), pytest-playwright is installed and provides the real
        `page` fixture. In the unit test job, this stub fires and skips the test.
        """
        pytest.skip(
            "pytest-playwright is not installed. "
            "Web E2E tests run only in the 'e2e-web' CI job. "
            "To run locally: pip install pytest pytest-playwright && "
            "playwright install chromium && "
            "cd clients/mobile && npx expo export -p web && "
            "python3 -m http.server 19006 --directory dist/ & "
            "pytest tests/e2e/platforms/web/ --browser chromium"
        )

else:
    # ─────────────────────────────────────────────────────────────────────────
    # Early error capture — ISSUE-041 diagnostic
    #
    # pytest-playwright's `context` fixture creates a BrowserContext per test.
    # `context.add_init_script()` injects JS that runs in EVERY page of that
    # context, BEFORE any other script on the page. This captures errors that
    # happen during the initial Expo bundle execution — errors that `page.on`
    # listeners miss because they are registered after `page.goto()`.
    #
    # The captured errors are available as `window.__webE2EErrors` and read
    # back by `_wait_for_app_ready` in each test file.
    # ─────────────────────────────────────────────────────────────────────────

    @pytest.fixture(autouse=True)
    def inject_early_error_capture(context: object) -> None:
        """
        Inject an early error collector into every page context.

        Captures: uncaught exceptions (window.onerror), unhandled promise
        rejections (window.onunhandledrejection), and JS console.error calls.
        All captured errors are stored in window.__webE2EErrors (list of strings).

        This fixture is AUTOUSE — it runs for every test in this directory
        without needing to be explicitly requested.

        IMPORTANT: this must be called before any page.goto() call.
        context.add_init_script() achieves this: the script is injected into
        every new page created by this context, before navigation begins.
        """
        # Type: ignore because `context` comes from pytest-playwright's fixture
        # and is playwright.sync_api.BrowserContext, typed as `object` here to
        # avoid import issues when pytest-playwright is not installed.
        getattr(context, "add_init_script")(
            """
            // ISSUE-041 diagnostic: capture all uncaught JS errors at page init time.
            // Stored in window.__webE2EErrors for read-back by _wait_for_app_ready.
            window.__webE2EErrors = [];

            // Capture synchronous uncaught exceptions (e.g. ErrorUtils.reportFatalError)
            window.onerror = function(msg, src, line, col, err) {
                window.__webE2EErrors.push('[onerror] ' + msg + ' (' + src + ':' + line + ')');
                return false;  // do NOT suppress — let it propagate
            };

            // Capture unhandled Promise rejections (async errors in React/Expo init)
            window.addEventListener('unhandledrejection', function(evt) {
                var reason = evt.reason;
                var msg = reason instanceof Error
                    ? reason.message + '\\n' + (reason.stack || '')
                    : String(reason);
                window.__webE2EErrors.push('[unhandledrejection] ' + msg);
            });

            // Patch console.error to capture Expo/React error boundary logs
            var _origError = console.error;
            console.error = function() {
                var msg = Array.prototype.slice.call(arguments).join(' ');
                window.__webE2EErrors.push('[console.error] ' + msg);
                _origError.apply(console, arguments);
            };
            """
        )
