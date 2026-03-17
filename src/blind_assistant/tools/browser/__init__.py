"""
Browser Tool

Wraps Playwright to give the orchestrator autonomous web navigation capability.
Claude reasons about any website — no service-specific wrappers needed.

Per ARCHITECTURE.md: "Browser as universal adapter" — Claude navigates ANY website
(food ordering, travel, banking, shopping) the way a human would. Build a specific
integration only when the browser can't do it (e.g. Stripe tokenization, OAuth).

Per SECURITY_MODEL.md §2.4: screenshot content is screened before any API call;
financial pages are protected and never sent externally.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Lazy import of Playwright — imported at module level for testability (patchable)
# but the actual module is only loaded when initialize() is called.
try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover — Playwright not installed in all environments
    async_playwright = None  # type: ignore[assignment]


@dataclass
class PageState:
    """Snapshot of the current browser page state."""

    url: str
    title: str
    # Text content visible on the page (used by Claude to reason about next action)
    text_content: str = ""
    # Screenshot bytes — only set when needed (screened before any API call)
    screenshot: bytes | None = None
    # Form fields found on the page: {name: current_value}
    form_fields: dict[str, str] = field(default_factory=dict)


@dataclass
class BrowserAction:
    """A single browser action to take."""

    action_type: str  # "navigate", "click", "type", "select", "screenshot"
    # Target element (CSS selector or text to find)
    target: str = ""
    # Value to type or select
    value: str = ""
    # URL to navigate to
    url: str = ""


class BrowserTool:
    """
    Autonomous web browser for completing tasks on behalf of the user.

    Uses Playwright to navigate websites. Claude decides what to click, type,
    and navigate based on the page content returned by get_page_state().

    This is the "universal adapter" — it handles any website without
    service-specific code.
    """

    def __init__(self) -> None:
        self._browser = None
        self._page = None
        self._playwright = None
        self._initialized = False

    async def initialize(self) -> None:
        """Start the browser. Must be called before any navigation."""
        # async_playwright is imported at module level for testability.
        # If Playwright is not installed, it will be None here.
        if async_playwright is None:
            logger.error(
                "playwright not installed — browser tool unavailable. "
                "Install it with: pip install playwright && playwright install chromium"
            )
            raise ImportError("playwright is not installed. Run: pip install playwright && playwright install chromium")
        try:
            self._playwright = await async_playwright().start()
            # Use Chromium for best screen reader compatibility testing
            self._browser = await self._playwright.chromium.launch(headless=True)
            self._page = await self._browser.new_page()
            self._initialized = True
            logger.info("Browser tool initialized (Chromium headless)")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}", exc_info=True)
            raise

    async def close(self) -> None:
        """Clean up browser resources."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False
        logger.info("Browser tool closed")

    async def navigate(self, url: str) -> PageState:
        """Navigate to a URL and return the page state."""
        self._require_initialized()
        logger.info(f"Navigating to: {url}")
        await self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return await self.get_page_state()

    async def get_page_state(self) -> PageState:
        """
        Return a snapshot of the current page for Claude to reason about.

        Returns text content only — screenshots are taken separately and only
        when needed, since they trigger the redaction pipeline.
        """
        self._require_initialized()
        url = self._page.url
        title = await self._page.title()

        # Get visible text content (ignoring scripts, styles, hidden elements)
        text_content = await self._page.evaluate("""
            () => {
                // Remove script and style elements from consideration
                const clone = document.body.cloneNode(true);
                for (const el of clone.querySelectorAll('script, style, noscript')) {
                    el.remove();
                }
                return clone.innerText || clone.textContent || '';
            }
        """)

        # Truncate to avoid huge pages overwhelming the context window
        if len(text_content) > 8000:
            text_content = text_content[:8000] + "\n[... page truncated ...]"

        return PageState(
            url=url,
            title=title,
            text_content=text_content.strip(),
        )

    async def click(self, selector: str, text: str = "") -> PageState:
        """
        Click an element by CSS selector or by visible text.

        Args:
            selector: CSS selector to click
            text: If non-empty, find the first element containing this text

        Returns: Updated page state after click
        """
        self._require_initialized()
        try:
            if text:
                # Click by visible text (more resilient to layout changes)
                await self._page.get_by_text(text, exact=False).first.click(timeout=10_000)
            else:
                await self._page.click(selector, timeout=10_000)

            # Wait for any navigation or dynamic content
            await self._page.wait_for_load_state("domcontentloaded", timeout=15_000)
            return await self.get_page_state()
        except Exception as e:
            logger.warning(f"Click failed (selector={selector!r}, text={text!r}): {e}")
            raise

    async def type_text(self, selector: str, value: str, clear_first: bool = True) -> PageState:
        """
        Type text into a form field.

        Args:
            selector: CSS selector for the input field
            value: Text to type
            clear_first: If True, clear the field before typing

        Returns: Updated page state
        """
        self._require_initialized()
        if clear_first:
            await self._page.fill(selector, value, timeout=10_000)
        else:
            await self._page.type(selector, value, timeout=10_000)
        return await self.get_page_state()

    async def select_option(self, selector: str, value: str) -> PageState:
        """Select an option from a dropdown by value or label."""
        self._require_initialized()
        await self._page.select_option(selector, value, timeout=10_000)
        return await self.get_page_state()

    async def take_screenshot(self) -> bytes:
        """
        Capture a screenshot of the current page.

        NOTE: Callers are responsible for running this through the redaction
        pipeline before sending to any external API. Financial pages are
        automatically protected by screen_observer.
        """
        self._require_initialized()
        return await self._page.screenshot()

    async def find_elements(self, selector: str) -> list[str]:
        """Find all elements matching a selector and return their text content."""
        self._require_initialized()
        elements = await self._page.query_selector_all(selector)
        texts = []
        for el in elements:
            text = await el.inner_text()
            if text.strip():
                texts.append(text.strip())
        return texts

    async def wait_for_text(self, text: str, timeout: float = 30.0) -> bool:
        """Wait for text to appear on the page. Returns True if found, False if timeout."""
        try:
            await self._page.wait_for_function(
                f"() => document.body.innerText.includes({text!r})",
                timeout=timeout * 1000,
            )
            return True
        except Exception:
            return False

    def _require_initialized(self) -> None:
        """Raise if browser has not been initialized."""
        if not self._initialized or not self._page:
            raise RuntimeError("BrowserTool not initialized. Call await browser_tool.initialize() first.")


class BrowserSession:
    """
    Context manager for a browser session.

    Usage:
        async with BrowserSession() as browser:
            state = await browser.navigate("https://example.com")
    """

    def __init__(self) -> None:
        self.tool = BrowserTool()

    async def __aenter__(self) -> BrowserTool:
        await self.tool.initialize()
        return self.tool

    async def __aexit__(self, *args) -> None:
        await self.tool.close()
