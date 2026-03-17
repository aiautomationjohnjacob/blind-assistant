"""
Unit tests for tools/browser/__init__.py — BrowserTool and BrowserSession.

All Playwright calls are mocked — no real browser is launched.
Tests verify: initialization, navigation, click, type, page state, close,
error handling, and the BrowserSession context manager.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from blind_assistant.tools.browser import BrowserTool, BrowserSession, PageState


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_page() -> AsyncMock:
    """A fully mocked Playwright page object."""
    page = AsyncMock()
    page.url = "https://example.com"
    page.title = AsyncMock(return_value="Example Page")
    page.evaluate = AsyncMock(return_value="Page text content here")
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.click = AsyncMock()
    page.fill = AsyncMock()
    page.type = AsyncMock()
    page.select_option = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"fake_screenshot_bytes")
    page.query_selector_all = AsyncMock(return_value=[])
    page.wait_for_function = AsyncMock()
    page.get_by_text = MagicMock()
    page.get_by_text.return_value.first.click = AsyncMock()
    return page


@pytest.fixture
def mock_browser(mock_page: AsyncMock) -> AsyncMock:
    """A mocked Playwright Browser object."""
    browser = AsyncMock()
    browser.new_page = AsyncMock(return_value=mock_page)
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_playwright_instance(mock_browser: AsyncMock) -> AsyncMock:
    """A mocked Playwright instance."""
    pw = AsyncMock()
    pw.chromium.launch = AsyncMock(return_value=mock_browser)
    pw.stop = AsyncMock()
    return pw


@pytest.fixture
async def initialized_browser_tool(
    mock_page: AsyncMock,
    mock_browser: AsyncMock,
    mock_playwright_instance: AsyncMock,
) -> BrowserTool:
    """A BrowserTool that has been initialized (Playwright mocked)."""
    tool = BrowserTool()
    # Patch async_playwright at the module level so initialize() picks up the mock.
    # The callable must return an object with .start() that returns the playwright instance.
    mock_apw_callable = MagicMock()
    mock_apw_callable.return_value.start = AsyncMock(return_value=mock_playwright_instance)
    with patch("blind_assistant.tools.browser.async_playwright", mock_apw_callable):
        await tool.initialize()
    return tool


# ─────────────────────────────────────────────────────────────
# Initialization tests
# ─────────────────────────────────────────────────────────────

async def test_initialize_sets_initialized_flag(
    mock_page: AsyncMock,
    mock_browser: AsyncMock,
    mock_playwright_instance: AsyncMock,
) -> None:
    """After initialize(), _initialized is True."""
    tool = BrowserTool()
    assert not tool._initialized

    with patch("blind_assistant.tools.browser.async_playwright") as mock_apw:
        mock_apw.return_value.start = AsyncMock(return_value=mock_playwright_instance)
        await tool.initialize()

    assert tool._initialized


async def test_initialize_raises_on_import_error() -> None:
    """initialize() re-raises ImportError when playwright is not installed."""
    tool = BrowserTool()
    with patch("blind_assistant.tools.browser.async_playwright", side_effect=ImportError("no playwright")):
        with pytest.raises(ImportError):
            await tool.initialize()


async def test_initialize_raises_on_launch_error(mock_playwright_instance: AsyncMock) -> None:
    """initialize() re-raises if browser launch fails."""
    tool = BrowserTool()
    mock_playwright_instance.chromium.launch = AsyncMock(side_effect=Exception("launch failed"))

    with patch("blind_assistant.tools.browser.async_playwright") as mock_apw:
        mock_apw.return_value.start = AsyncMock(return_value=mock_playwright_instance)
        with pytest.raises(Exception, match="launch failed"):
            await tool.initialize()


# ─────────────────────────────────────────────────────────────
# _require_initialized guard
# ─────────────────────────────────────────────────────────────

async def test_navigate_raises_when_not_initialized() -> None:
    """Navigation before initialize() raises RuntimeError."""
    tool = BrowserTool()
    with pytest.raises(RuntimeError, match="not initialized"):
        await tool.navigate("https://example.com")


async def test_get_page_state_raises_when_not_initialized() -> None:
    """get_page_state() before initialize() raises RuntimeError."""
    tool = BrowserTool()
    with pytest.raises(RuntimeError, match="not initialized"):
        await tool.get_page_state()


async def test_click_raises_when_not_initialized() -> None:
    """click() before initialize() raises RuntimeError."""
    tool = BrowserTool()
    with pytest.raises(RuntimeError, match="not initialized"):
        await tool.click(".some-selector")


async def test_type_text_raises_when_not_initialized() -> None:
    """type_text() before initialize() raises RuntimeError."""
    tool = BrowserTool()
    with pytest.raises(RuntimeError, match="not initialized"):
        await tool.type_text("#input", "hello")


async def test_take_screenshot_raises_when_not_initialized() -> None:
    """take_screenshot() before initialize() raises RuntimeError."""
    tool = BrowserTool()
    with pytest.raises(RuntimeError, match="not initialized"):
        await tool.take_screenshot()


# ─────────────────────────────────────────────────────────────
# Navigation tests
# ─────────────────────────────────────────────────────────────

async def test_navigate_calls_goto(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """navigate() calls page.goto with the given URL."""
    await initialized_browser_tool.navigate("https://doordash.com")
    mock_page.goto.assert_called_once_with(
        "https://doordash.com",
        wait_until="domcontentloaded",
        timeout=30_000,
    )


async def test_navigate_returns_page_state(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """navigate() returns a PageState with url, title, and text_content."""
    state = await initialized_browser_tool.navigate("https://doordash.com")
    assert isinstance(state, PageState)
    assert state.url == "https://example.com"  # mock page.url
    assert state.title == "Example Page"
    assert "Page text content here" in state.text_content


# ─────────────────────────────────────────────────────────────
# Page state tests
# ─────────────────────────────────────────────────────────────

async def test_get_page_state_truncates_long_content(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """get_page_state() truncates text content to 8000 chars."""
    long_content = "x" * 10_000
    mock_page.evaluate = AsyncMock(return_value=long_content)

    state = await initialized_browser_tool.get_page_state()

    # Should be truncated — 8000 chars + truncation notice
    assert len(state.text_content) < 10_000
    assert "[... page truncated ...]" in state.text_content


async def test_get_page_state_short_content_not_truncated(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """get_page_state() does not truncate content within 8000 chars."""
    short_content = "Short page content"
    mock_page.evaluate = AsyncMock(return_value=short_content)

    state = await initialized_browser_tool.get_page_state()

    assert state.text_content == short_content
    assert "[... page truncated ...]" not in state.text_content


# ─────────────────────────────────────────────────────────────
# Click tests
# ─────────────────────────────────────────────────────────────

async def test_click_by_selector(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """click() with a CSS selector calls page.click."""
    await initialized_browser_tool.click(".add-to-cart")
    mock_page.click.assert_called_once_with(".add-to-cart", timeout=10_000)


async def test_click_by_text(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """click() with text parameter uses get_by_text."""
    await initialized_browser_tool.click("", text="Add to cart")
    mock_page.get_by_text.assert_called_once_with("Add to cart", exact=False)


async def test_click_raises_on_playwright_error(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """click() re-raises Playwright exceptions so orchestrator can handle them."""
    mock_page.click = AsyncMock(side_effect=Exception("element not found"))
    with pytest.raises(Exception, match="element not found"):
        await initialized_browser_tool.click(".missing-element")


# ─────────────────────────────────────────────────────────────
# Type text tests
# ─────────────────────────────────────────────────────────────

async def test_type_text_uses_fill_when_clear_first(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """type_text() with clear_first=True uses page.fill."""
    await initialized_browser_tool.type_text("#address", "123 Main St", clear_first=True)
    mock_page.fill.assert_called_once_with("#address", "123 Main St", timeout=10_000)


async def test_type_text_uses_type_when_no_clear(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """type_text() with clear_first=False uses page.type (appends)."""
    await initialized_browser_tool.type_text("#search", "pizza", clear_first=False)
    mock_page.type.assert_called_once_with("#search", "pizza", timeout=10_000)


# ─────────────────────────────────────────────────────────────
# Screenshot tests
# ─────────────────────────────────────────────────────────────

async def test_take_screenshot_returns_bytes(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """take_screenshot() returns raw bytes from Playwright."""
    result = await initialized_browser_tool.take_screenshot()
    assert result == b"fake_screenshot_bytes"
    mock_page.screenshot.assert_called_once()


# ─────────────────────────────────────────────────────────────
# Wait for text tests
# ─────────────────────────────────────────────────────────────

async def test_wait_for_text_returns_true_when_found(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """wait_for_text() returns True when text appears."""
    mock_page.wait_for_function = AsyncMock(return_value=None)  # success
    result = await initialized_browser_tool.wait_for_text("Order confirmed")
    assert result is True


async def test_wait_for_text_returns_false_on_timeout(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """wait_for_text() returns False on timeout without raising."""
    mock_page.wait_for_function = AsyncMock(side_effect=Exception("timeout"))
    result = await initialized_browser_tool.wait_for_text("Never appears", timeout=1.0)
    assert result is False


# ─────────────────────────────────────────────────────────────
# Find elements tests
# ─────────────────────────────────────────────────────────────

async def test_find_elements_returns_text_list(
    initialized_browser_tool: BrowserTool,
    mock_page: AsyncMock,
) -> None:
    """find_elements() returns list of text content from matching elements."""
    el1 = AsyncMock()
    el1.inner_text = AsyncMock(return_value="Pizza Palace")
    el2 = AsyncMock()
    el2.inner_text = AsyncMock(return_value="  Taco Town  ")  # whitespace stripped
    el3 = AsyncMock()
    el3.inner_text = AsyncMock(return_value="")  # empty — excluded
    mock_page.query_selector_all = AsyncMock(return_value=[el1, el2, el3])

    results = await initialized_browser_tool.find_elements(".restaurant-name")

    assert results == ["Pizza Palace", "Taco Town"]


# ─────────────────────────────────────────────────────────────
# Close tests
# ─────────────────────────────────────────────────────────────

async def test_close_shuts_down_browser(
    initialized_browser_tool: BrowserTool,
) -> None:
    """close() closes the browser and stops playwright, sets initialized=False."""
    assert initialized_browser_tool._initialized
    await initialized_browser_tool.close()
    assert not initialized_browser_tool._initialized


# ─────────────────────────────────────────────────────────────
# BrowserSession context manager tests
# ─────────────────────────────────────────────────────────────

async def test_browser_session_initializes_and_closes() -> None:
    """BrowserSession context manager calls initialize() and close()."""
    with patch.object(BrowserTool, "initialize", new_callable=AsyncMock) as mock_init, \
         patch.object(BrowserTool, "close", new_callable=AsyncMock) as mock_close:
        async with BrowserSession() as browser:
            assert browser is not None
            mock_init.assert_called_once()
        mock_close.assert_called_once()


async def test_browser_session_closes_on_exception() -> None:
    """BrowserSession still calls close() even if an exception occurs inside."""
    with patch.object(BrowserTool, "initialize", new_callable=AsyncMock), \
         patch.object(BrowserTool, "close", new_callable=AsyncMock) as mock_close:
        with pytest.raises(ValueError, match="test error"):
            async with BrowserSession():
                raise ValueError("test error")

        mock_close.assert_called_once()
