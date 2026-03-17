"""
conftest.py — Web E2E test fixtures.

Provides a `page` fixture stub that skips gracefully when pytest-playwright
is not installed. In CI, pytest-playwright IS installed (see ci.yml e2e-web job).
In the standard unit test run, pytest-playwright is NOT installed, so these
tests skip cleanly without errors.

This avoids the "fixture 'page' not found" error that occurs when these tests
are collected by the main pytest run without pytest-playwright present.
"""

from __future__ import annotations

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Detect whether pytest-playwright is available
# ─────────────────────────────────────────────────────────────────────────────

try:
    # If pytest-playwright is installed, its plugin registers the `page` fixture
    # automatically. We do NOT override it here — just check it's available.
    import playwright  # noqa: F401
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Stub `page` fixture — only active when pytest-playwright is NOT installed
# ─────────────────────────────────────────────────────────────────────────────

if not PLAYWRIGHT_AVAILABLE:
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
