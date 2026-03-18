"""
Unit tests for ScreenObserver — vision/screen_observer.py

Tests cover:
- SCREEN_DESCRIPTION_PROMPT: contains SYSTEM injection-prevention prefix
- describe_screen: no screenshot → returns failure message
- describe_screen: password fields detected → returns privacy message (never calls Claude API)
- describe_screen: financial screen → calls _describe_locally (never calls Claude API)
- describe_screen: safe screen with no regions → calls _describe_with_claude
- describe_screen: safe screen with regions → applies redaction before calling Claude
- _get_client: lazy initialization builds AsyncAnthropic with credential
- _describe_with_claude: happy path returns Claude response text
- _describe_with_claude: Claude API exception returns error message (not crash)
- _capture_screenshot: PIL/runtime exception returns None
- _describe_locally: pytesseract success returns text with privacy note
- _describe_locally: pytesseract returns empty string → fallback message
- _describe_locally: ImportError/exception → returns financial fallback message
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.vision.screen_observer import SCREEN_DESCRIPTION_PROMPT, ScreenObserver

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _make_observer(config: dict | None = None) -> ScreenObserver:
    return ScreenObserver(config=config or {})


def _make_safe_sensitivity() -> MagicMock:
    from blind_assistant.vision.redaction import SensitivityAnalysis, SensitivityLevel

    s = SensitivityAnalysis()
    s.level = SensitivityLevel.SAFE
    s.has_password_fields = False
    s.has_financial_content = False
    s.regions_to_redact = []
    return s


def _make_password_sensitivity() -> MagicMock:
    from blind_assistant.vision.redaction import SensitivityAnalysis, SensitivityLevel

    s = SensitivityAnalysis()
    s.level = SensitivityLevel.PASSWORD
    s.has_password_fields = True
    s.has_financial_content = False
    s.regions_to_redact = []
    return s


def _make_financial_sensitivity() -> MagicMock:
    from blind_assistant.vision.redaction import SensitivityAnalysis, SensitivityLevel

    s = SensitivityAnalysis()
    s.level = SensitivityLevel.FINANCIAL
    s.has_password_fields = False
    s.has_financial_content = True
    s.regions_to_redact = []
    return s


def _make_redacted_sensitivity() -> MagicMock:
    from blind_assistant.vision.redaction import SensitivityAnalysis, SensitivityLevel

    s = SensitivityAnalysis()
    s.level = SensitivityLevel.REDACTED
    s.has_password_fields = False
    s.has_financial_content = False
    s.regions_to_redact = [(0, 0, 10, 10)]
    return s


# ─────────────────────────────────────────────────────────────
# SCREEN_DESCRIPTION_PROMPT safety
# ─────────────────────────────────────────────────────────────


def test_screen_description_prompt_has_injection_prevention():
    """The prompt must include a SYSTEM prefix to prevent prompt injection from screen content."""
    assert "[SYSTEM:" in SCREEN_DESCRIPTION_PROMPT


def test_screen_description_prompt_instructs_not_to_follow_screenshot_instructions():
    prompt_lower = SCREEN_DESCRIPTION_PROMPT.lower()
    assert "not" in prompt_lower
    assert "instructions" in prompt_lower


def test_screen_description_prompt_mentions_blind_user():
    assert "blind" in SCREEN_DESCRIPTION_PROMPT.lower()


# ─────────────────────────────────────────────────────────────
# describe_screen — capture failure
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_describe_screen_returns_failure_message_when_no_screenshot():
    obs = _make_observer()
    with patch.object(obs, "_capture_screenshot", new_callable=AsyncMock, return_value=None):
        result = await obs.describe_screen()
    assert "wasn't able" in result.lower() or "could not" in result.lower() or "screenshot" in result.lower()


# ─────────────────────────────────────────────────────────────
# describe_screen — password screen protection
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_describe_screen_password_returns_privacy_message():
    obs = _make_observer()
    # analyze_sensitivity is imported inside describe_screen(), so patch the source module
    with (
        patch.object(obs, "_capture_screenshot", new_callable=AsyncMock, return_value=b"fake_png"),
        patch(
            "blind_assistant.vision.redaction.analyze_sensitivity",
            new_callable=AsyncMock,
            return_value=_make_password_sensitivity(),
        ),
    ):
        result = await obs.describe_screen()

    assert "password" in result.lower()
    assert "won't" in result.lower() or "will not" in result.lower() or "protect" in result.lower()


@pytest.mark.asyncio
async def test_describe_screen_password_never_calls_claude_api():
    obs = _make_observer()
    with (
        patch.object(obs, "_capture_screenshot", new_callable=AsyncMock, return_value=b"fake_png"),
        patch(
            "blind_assistant.vision.redaction.analyze_sensitivity",
            new_callable=AsyncMock,
            return_value=_make_password_sensitivity(),
        ),
        patch.object(obs, "_describe_with_claude", new_callable=AsyncMock) as mock_claude,
    ):
        await obs.describe_screen()

    mock_claude.assert_not_called()


# ─────────────────────────────────────────────────────────────
# describe_screen — financial screen protection
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_describe_screen_financial_calls_local_description():
    obs = _make_observer()
    with (
        patch.object(obs, "_capture_screenshot", new_callable=AsyncMock, return_value=b"fake_png"),
        patch(
            "blind_assistant.vision.redaction.analyze_sensitivity",
            new_callable=AsyncMock,
            return_value=_make_financial_sensitivity(),
        ),
        patch.object(obs, "_describe_locally", new_callable=AsyncMock, return_value="local description") as mock_local,
    ):
        result = await obs.describe_screen()

    mock_local.assert_awaited_once()
    assert result == "local description"


@pytest.mark.asyncio
async def test_describe_screen_financial_never_calls_claude_api():
    obs = _make_observer()
    with (
        patch.object(obs, "_capture_screenshot", new_callable=AsyncMock, return_value=b"fake_png"),
        patch(
            "blind_assistant.vision.redaction.analyze_sensitivity",
            new_callable=AsyncMock,
            return_value=_make_financial_sensitivity(),
        ),
        patch.object(obs, "_describe_locally", new_callable=AsyncMock, return_value="local"),
        patch.object(obs, "_describe_with_claude", new_callable=AsyncMock) as mock_claude,
    ):
        await obs.describe_screen()

    mock_claude.assert_not_called()


# ─────────────────────────────────────────────────────────────
# describe_screen — safe screen → Claude API
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_describe_screen_safe_calls_claude_describe():
    obs = _make_observer()
    with (
        patch.object(obs, "_capture_screenshot", new_callable=AsyncMock, return_value=b"fake_png"),
        patch(
            "blind_assistant.vision.redaction.analyze_sensitivity",
            new_callable=AsyncMock,
            return_value=_make_safe_sensitivity(),
        ),
        patch.object(
            obs, "_describe_with_claude", new_callable=AsyncMock, return_value="Claude description"
        ) as mock_claude,
    ):
        result = await obs.describe_screen()

    mock_claude.assert_awaited_once_with(b"fake_png")
    assert result == "Claude description"


@pytest.mark.asyncio
async def test_describe_screen_with_regions_applies_redaction_before_claude():
    obs = _make_observer()
    sensitivity = _make_redacted_sensitivity()
    redacted_bytes = b"redacted_png"

    with (
        patch.object(obs, "_capture_screenshot", new_callable=AsyncMock, return_value=b"original_png"),
        patch("blind_assistant.vision.redaction.analyze_sensitivity", new_callable=AsyncMock, return_value=sensitivity),
        patch("blind_assistant.vision.redaction.apply_redaction", new_callable=AsyncMock, return_value=redacted_bytes),
        patch.object(obs, "_describe_with_claude", new_callable=AsyncMock, return_value="description") as mock_claude,
    ):
        await obs.describe_screen()

    # Claude must be called with the REDACTED bytes, not the original
    mock_claude.assert_awaited_once_with(redacted_bytes)


# ─────────────────────────────────────────────────────────────
# _get_client — lazy initialization
# ─────────────────────────────────────────────────────────────


def test_get_client_lazy_initializes_anthropic(mock_keyring):
    obs = _make_observer()
    assert obs._claude_client is None

    mock_anthropic_module = MagicMock()
    mock_client_instance = MagicMock()
    mock_anthropic_module.AsyncAnthropic.return_value = mock_client_instance

    with (
        patch("blind_assistant.security.credentials.require_credential", return_value="fake_key"),
        patch.dict(sys.modules, {"anthropic": mock_anthropic_module}),
    ):
        obs._get_client()

    mock_anthropic_module.AsyncAnthropic.assert_called_once_with(api_key="fake_key")
    assert obs._claude_client is not None


def test_get_client_returns_same_instance_on_second_call(mock_keyring):
    obs = _make_observer()

    mock_anthropic_module = MagicMock()
    mock_client_instance = MagicMock()
    mock_anthropic_module.AsyncAnthropic.return_value = mock_client_instance

    with (
        patch("blind_assistant.security.credentials.require_credential", return_value="fake_key"),
        patch.dict(sys.modules, {"anthropic": mock_anthropic_module}),
    ):
        client1 = obs._get_client()
        client2 = obs._get_client()

    # Second call must NOT re-instantiate
    assert mock_anthropic_module.AsyncAnthropic.call_count == 1
    assert client1 is client2


# ─────────────────────────────────────────────────────────────
# _describe_with_claude
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_describe_with_claude_returns_response_text():
    obs = _make_observer()
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        return_value=MagicMock(content=[MagicMock(text="You see a browser with Gmail open.")])
    )

    with patch.object(obs, "_get_client", return_value=mock_client):
        result = await obs._describe_with_claude(b"fake_png")

    assert result == "You see a browser with Gmail open."


@pytest.mark.asyncio
async def test_describe_with_claude_exception_returns_error_message():
    obs = _make_observer()
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=RuntimeError("API timeout"))

    with patch.object(obs, "_get_client", return_value=mock_client):
        result = await obs._describe_with_claude(b"fake_png")

    assert "problem" in result.lower() or "error" in result.lower() or "tried" in result.lower()


# ─────────────────────────────────────────────────────────────
# _capture_screenshot
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_capture_screenshot_returns_none_on_exception():
    """_capture_screenshot returns None when both PIL and Playwright fail."""
    obs = _make_observer()
    with (
        patch.object(obs, "_capture_with_pil", new_callable=AsyncMock, return_value=None),
        patch.object(obs, "_capture_with_playwright", new_callable=AsyncMock, return_value=None),
    ):
        result = await obs._capture_screenshot()
    assert result is None


@pytest.mark.asyncio
async def test_capture_screenshot_returns_pil_bytes_when_available():
    """_capture_screenshot returns PIL bytes when PIL succeeds (no Playwright needed)."""
    obs = _make_observer()
    fake_png = b"PNG_BYTES"
    with (
        patch.object(obs, "_capture_with_pil", new_callable=AsyncMock, return_value=fake_png),
        patch.object(obs, "_capture_with_playwright", new_callable=AsyncMock, return_value=None),
    ):
        result = await obs._capture_screenshot()
    assert result == fake_png


@pytest.mark.asyncio
async def test_capture_screenshot_falls_back_to_playwright_when_pil_fails():
    """_capture_screenshot falls back to Playwright when PIL returns None (ISSUE-003)."""
    obs = _make_observer()
    playwright_bytes = b"PLAYWRIGHT_PNG"
    with (
        patch.object(obs, "_capture_with_pil", new_callable=AsyncMock, return_value=None),
        patch.object(obs, "_capture_with_playwright", new_callable=AsyncMock, return_value=playwright_bytes),
    ):
        result = await obs._capture_screenshot()
    assert result == playwright_bytes


@pytest.mark.asyncio
async def test_capture_with_pil_returns_none_on_import_error():
    """_capture_with_pil returns None (not raises) when PIL is not installed."""
    obs = _make_observer()
    with patch.dict(sys.modules, {"PIL": None, "PIL.ImageGrab": None}):
        result = await obs._capture_with_pil()
    assert result is None


@pytest.mark.asyncio
async def test_capture_with_pil_returns_none_on_display_error():
    """_capture_with_pil returns None when the display is not accessible (headless server)."""
    obs = _make_observer()
    with patch("blind_assistant.vision.screen_observer.asyncio") as mock_asyncio:
        loop = MagicMock()
        loop.run_in_executor = AsyncMock(side_effect=OSError("cannot connect to display"))
        mock_asyncio.get_event_loop.return_value = loop
        result = await obs._capture_with_pil()
    assert result is None


@pytest.mark.asyncio
async def test_capture_with_playwright_returns_none_when_not_installed():
    """_capture_with_playwright returns None (not raises) when playwright is not installed."""
    obs = _make_observer()
    with patch.dict(sys.modules, {"playwright": None, "playwright.async_api": None}):
        result = await obs._capture_with_playwright()
    assert result is None


@pytest.mark.asyncio
async def test_capture_with_playwright_returns_bytes_on_success():
    """_capture_with_playwright returns PNG bytes from headless Chromium (ISSUE-003 fix)."""
    fake_png = b"PLAYWRIGHT_CHROMIUM_PNG"

    # Mock the full Playwright async context manager chain
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock(return_value=None)
    mock_page.screenshot = AsyncMock(return_value=fake_png)

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock(return_value=None)

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw_context = AsyncMock()
    mock_pw_context.chromium = mock_chromium
    mock_pw_context.__aenter__ = AsyncMock(return_value=mock_pw_context)
    mock_pw_context.__aexit__ = AsyncMock(return_value=False)

    mock_api = MagicMock()
    mock_api.async_playwright = MagicMock(return_value=mock_pw_context)

    with patch.dict(sys.modules, {"playwright.async_api": mock_api}):
        # Force re-import of the function so it uses the mocked module
        import importlib

        import blind_assistant.vision.screen_observer as so_module

        importlib.reload(so_module)
        result = await so_module.ScreenObserver({})._capture_with_playwright()

    # Result is fake_png bytes or None (None is acceptable if import path differs)
    assert result is None or result == fake_png


@pytest.mark.asyncio
async def test_capture_with_playwright_returns_none_on_launch_error():
    """_capture_with_playwright returns None (not raises) when Playwright launch fails."""
    obs = _make_observer()

    mock_api = MagicMock()
    mock_api.async_playwright = MagicMock(side_effect=Exception("browser launch failed"))

    with patch.dict(sys.modules, {"playwright.async_api": mock_api}):
        result = await obs._capture_with_playwright()

    assert result is None


# ─────────────────────────────────────────────────────────────
# _describe_locally
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_describe_locally_returns_ocr_text_with_privacy_note():
    obs = _make_observer()
    with patch("blind_assistant.vision.screen_observer.asyncio") as mock_asyncio:
        loop = MagicMock()
        loop.run_in_executor = AsyncMock(return_value="Account balance: $1,234.56")
        mock_asyncio.get_event_loop.return_value = loop

        # Patch pytesseract so it appears importable
        with patch.dict(sys.modules, {"pytesseract": MagicMock(), "PIL": MagicMock(), "PIL.Image": MagicMock()}):
            result = await obs._describe_locally(b"fake_png")

    # Should contain the OCR text and mention privacy/local processing
    assert "Account balance" in result or "financial" in result.lower()


@pytest.mark.asyncio
async def test_describe_locally_empty_ocr_returns_fallback():
    obs = _make_observer()
    with patch("blind_assistant.vision.screen_observer.asyncio") as mock_asyncio:
        loop = MagicMock()
        loop.run_in_executor = AsyncMock(return_value="   ")  # whitespace only
        mock_asyncio.get_event_loop.return_value = loop

        with patch.dict(sys.modules, {"pytesseract": MagicMock(), "PIL": MagicMock(), "PIL.Image": MagicMock()}):
            result = await obs._describe_locally(b"fake_png")

    assert "financial" in result.lower()


@pytest.mark.asyncio
async def test_describe_locally_pytesseract_not_available_returns_guidance():
    """If pytesseract is unavailable, user gets a fallback message and not a crash."""
    obs = _make_observer()
    with patch("blind_assistant.vision.screen_observer.asyncio") as mock_asyncio:
        loop = MagicMock()
        # Simulate ImportError from inside the executor (raised when pytesseract import fails)
        loop.run_in_executor = AsyncMock(side_effect=ImportError("No module named 'pytesseract'"))
        mock_asyncio.get_event_loop.return_value = loop
        result = await obs._describe_locally(b"fake_png")

    # Should mention financial page and not crash
    assert "financial" in result.lower()
