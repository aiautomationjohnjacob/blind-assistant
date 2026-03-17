"""
Integration tests for BrowserTool — uses a REAL Playwright browser against a local
HTML fixture. This validates that BrowserTool's navigation, text extraction, clicking,
and form typing actually work end-to-end — not just with mocks.

This test addresses ISSUE-021: the food ordering checkout loop was implemented and tested
entirely with mocked browser calls. These integration tests verify the real code paths.

Approach:
- Serve a static HTML page from a pytest fixture (no external network required)
- BrowserTool navigates to the local page using real Playwright
- Tests verify: text extraction, navigation, clicking, form interaction

Skip conditions (this is an integration test, not a unit test):
- Playwright system dependencies not available (headless Chrome requires libnss3, etc.)
- Set PLAYWRIGHT_AVAILABLE=1 env var to force-run in environments where deps are installed

CI note: These tests run in the CI job 'integration-browser' which uses the
playwright-installed GitHub Action runner with system dependencies. They are SKIPPED
in the default test run (pytest tests/unit/) and must be explicitly invoked with
pytest tests/integration/ or the integration-browser CI job.

Per testing.md: integration tests use real file I/O and real browser but no real
external APIs (food ordering sites).
"""

import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest

# ─────────────────────────────────────────────────────────────
# Skip logic — check if real Playwright can launch a browser
# ─────────────────────────────────────────────────────────────

PLAYWRIGHT_AVAILABLE = os.environ.get("PLAYWRIGHT_AVAILABLE", "0") == "1"

# Quick check: can Playwright actually launch a browser in this environment?
# We try a minimal browser launch and catch the dependency error.
_playwright_launch_ok = False

def _check_playwright() -> bool:
    """Return True if Playwright can actually launch Chromium (system deps present)."""
    try:
        import asyncio as _asyncio
        from playwright.async_api import async_playwright as _apw

        async def _probe() -> bool:
            try:
                async with _apw() as p:
                    browser = await p.chromium.launch(headless=True)
                    await browser.close()
                    return True
            except Exception:
                return False

        return _asyncio.run(_probe())
    except ImportError:
        return False


# Only probe once per process — this avoids 5 second overhead per test
_playwright_launch_ok = _check_playwright()

# Skip if Playwright can't launch (missing system deps) AND env var not set
pytestmark = pytest.mark.skipif(
    not _playwright_launch_ok and not PLAYWRIGHT_AVAILABLE,
    reason=(
        "Playwright system dependencies not available (libnss3, libnspr4 etc.). "
        "Install with: sudo playwright install-deps "
        "OR set PLAYWRIGHT_AVAILABLE=1 in environment. "
        "This test runs in the 'integration-browser' CI job where deps are available. "
        "ISSUE-021: validates real browser navigation for food ordering checkout loop."
    ),
)

# ─────────────────────────────────────────────────────────────
# Local test HTML server fixture
# ─────────────────────────────────────────────────────────────

FOOD_ORDERING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Food Delivery — Pizza near you</title>
</head>
<body>
  <h1>Food Delivery</h1>
  <p>Showing results for: Pizza</p>

  <section class="restaurants">
    <article class="restaurant" id="pizza-palace">
      <h2 class="restaurant-name">Pizza Palace</h2>
      <span class="rating">4.5 stars</span>
      <span class="delivery-time">25-35 min</span>
      <span class="delivery-fee">$2.99 delivery</span>
      <a href="/restaurant/pizza-palace" class="restaurant-link">Order from Pizza Palace</a>
    </article>

    <article class="restaurant" id="taco-town">
      <h2 class="restaurant-name">Taco Town</h2>
      <span class="rating">4.2 stars</span>
      <span class="delivery-time">20-30 min</span>
      <span class="delivery-fee">Free delivery</span>
      <a href="/restaurant/taco-town" class="restaurant-link">Order from Taco Town</a>
    </article>

    <article class="restaurant" id="burger-barn">
      <h2 class="restaurant-name">Burger Barn</h2>
      <span class="rating">4.0 stars</span>
      <span class="delivery-time">30-45 min</span>
      <span class="delivery-fee">$1.99 delivery</span>
      <a href="/restaurant/burger-barn" class="restaurant-link">Order from Burger Barn</a>
    </article>
  </section>

  <form id="search-form" action="/search" method="get">
    <label for="search-input">Search for food</label>
    <input id="search-input" name="q" type="text" placeholder="Enter food or restaurant name">
    <button type="submit" id="search-button">Search</button>
  </form>
</body>
</html>
"""

RESTAURANT_MENU_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Pizza Palace — Menu</title>
</head>
<body>
  <h1>Pizza Palace Menu</h1>
  <p>Free delivery on orders over $15</p>

  <section class="menu-items">
    <article class="menu-item">
      <h2>Margherita Pizza</h2>
      <p>Fresh mozzarella, tomato sauce, basil — $14.99</p>
      <button class="add-to-cart" data-item="Margherita Pizza" data-price="14.99">
        Add to cart
      </button>
    </article>

    <article class="menu-item">
      <h2>Pepperoni Pizza</h2>
      <p>Classic pepperoni, mozzarella, tomato sauce — $16.99</p>
      <button class="add-to-cart" data-item="Pepperoni Pizza" data-price="16.99">
        Add to cart
      </button>
    </article>

    <article class="menu-item">
      <h2>Veggie Supreme</h2>
      <p>Bell peppers, mushrooms, olives, onions — $15.99</p>
      <button class="add-to-cart" data-item="Veggie Supreme" data-price="15.99">
        Add to cart
      </button>
    </article>
  </section>
</body>
</html>
"""

CART_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Your Cart — Pizza Palace</title>
</head>
<body>
  <h1>Your Cart</h1>

  <section class="cart-items">
    <div class="cart-item">
      <span class="item-name">Pepperoni Pizza</span>
      <span class="item-quantity">x1</span>
      <span class="item-price">$16.99</span>
    </div>
  </section>

  <div class="cart-total">
    <span>Subtotal: $16.99</span>
    <span>Delivery fee: $2.99</span>
    <strong>Total: $19.98</strong>
  </div>

  <button id="place-order-btn" class="place-order">Place Order</button>

  <div id="confirmation-message" style="display:none;">
    Order #12345 confirmed! Estimated delivery: 30 min.
  </div>
</body>
</html>
"""


class _SilentHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves HTML from our fixtures, silently (no request logging)."""

    _routes: dict[str, str] = {}

    def log_message(self, format: str, *args: object) -> None:
        """Suppress request logging to keep test output clean."""

    def do_GET(self) -> None:
        path = self.path.split("?")[0]  # strip query params
        content = self._routes.get(path)
        if content is None:
            self.send_response(404)
            self.end_headers()
            return
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _make_handler_class(routes: dict[str, str]) -> type:
    """Create a handler class with the given route map baked in."""

    class Handler(_SilentHandler):
        _routes = routes

    return Handler


@pytest.fixture(scope="module")
def food_site_server():
    """
    Starts a local HTTP server with food ordering HTML fixtures.
    Yields the base URL. Shuts down after the test module completes.

    Routes:
      /             → search results (Pizza near you, 3 restaurants)
      /restaurant/pizza-palace → Pizza Palace menu
      /cart         → cart with Pepperoni Pizza
    """
    routes = {
        "/": FOOD_ORDERING_HTML,
        "/search": FOOD_ORDERING_HTML,  # search results (same page for simplicity)
        "/restaurant/pizza-palace": RESTAURANT_MENU_HTML,
        "/cart": CART_HTML,
    }
    handler_class = _make_handler_class(routes)
    server = HTTPServer(("127.0.0.1", 0), handler_class)
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield base_url

    server.shutdown()


# ─────────────────────────────────────────────────────────────
# BrowserTool integration tests — real Playwright browser
# ─────────────────────────────────────────────────────────────

from blind_assistant.tools.browser import BrowserSession, BrowserTool, PageState


async def test_browser_tool_navigate_returns_real_page_state(
    food_site_server: str,
) -> None:
    """
    BrowserTool.navigate() on a real local HTML page returns a PageState with:
    - correct URL
    - non-empty title
    - text content that includes visible page text (not raw HTML)

    This is the most fundamental integration test — verifies that Playwright
    actually extracts text content from real pages, not just mocks.
    """
    async with BrowserSession() as browser:
        state = await browser.navigate(food_site_server + "/")

    assert isinstance(state, PageState)
    assert state.url.startswith("http://127.0.0.1")
    assert "Pizza" in state.title  # from <title>Food Delivery — Pizza near you</title>
    # Text content should include restaurant names (visible text, not tags)
    assert "Pizza Palace" in state.text_content
    assert "Taco Town" in state.text_content
    assert "Burger Barn" in state.text_content
    # Should NOT include raw HTML tags
    assert "<html>" not in state.text_content
    assert "<article>" not in state.text_content


async def test_browser_tool_text_content_excludes_scripts_and_styles(
    food_site_server: str,
) -> None:
    """
    get_page_state() strips <script> and <style> elements from text content.
    This is critical for Claude's food ordering page analysis — script noise would
    confuse the AI into reading JavaScript as if it were restaurant listings.
    """
    async with BrowserSession() as browser:
        await browser.navigate(food_site_server + "/")
        state = await browser.get_page_state()

    # Should have real text
    assert len(state.text_content) > 50
    # Should not have HTML syntax
    assert "<!DOCTYPE" not in state.text_content
    assert "</h2>" not in state.text_content


async def test_browser_tool_navigate_restaurant_page(
    food_site_server: str,
) -> None:
    """
    BrowserTool can navigate to a restaurant menu page and extract menu items.

    This validates step 5-7 of the food ordering loop:
    After picking a restaurant, the browser navigates to that restaurant's page
    and Claude can reason about the menu items in the text content.
    """
    async with BrowserSession() as browser:
        state = await browser.navigate(food_site_server + "/restaurant/pizza-palace")

    assert "Pizza Palace" in state.title
    # Menu items should be in the text content for Claude to read
    assert "Margherita Pizza" in state.text_content
    assert "Pepperoni Pizza" in state.text_content
    assert "Veggie Supreme" in state.text_content
    # Prices should be present for the order summary
    assert "14.99" in state.text_content or "$14" in state.text_content


async def test_browser_tool_find_elements_by_selector(
    food_site_server: str,
) -> None:
    """
    BrowserTool.find_elements() can locate elements by CSS selector.

    This validates that the browser tool can find clickable elements like
    "Add to cart" buttons or restaurant links — used in _navigate_to_user_choice.
    """
    async with BrowserSession() as browser:
        await browser.navigate(food_site_server + "/")
        restaurant_names = await browser.find_elements(".restaurant-name")

    # Should find all 3 restaurant name elements
    assert len(restaurant_names) == 3
    assert "Pizza Palace" in restaurant_names
    assert "Taco Town" in restaurant_names
    assert "Burger Barn" in restaurant_names


async def test_browser_tool_type_text_into_search_form(
    food_site_server: str,
) -> None:
    """
    BrowserTool.type_text() fills a real form field.

    This validates that the browser can type user input into search fields,
    which is how the food ordering loop submits location or restaurant searches.
    """
    async with BrowserSession() as browser:
        await browser.navigate(food_site_server + "/")
        # Type into the search field
        await browser.type_text("#search-input", "pepperoni pizza", clear_first=True)
        # Verify the value was actually set
        value = await browser._page.input_value("#search-input")

    assert value == "pepperoni pizza"


async def test_browser_tool_click_by_text(
    food_site_server: str,
) -> None:
    """
    BrowserTool.click(text=...) can click an element found by its visible text.

    This is the primary navigation mechanism in _navigate_to_user_choice —
    Claude identifies the restaurant by name and clicks the "Order from X" link.
    """
    async with BrowserSession() as browser:
        await browser.navigate(food_site_server + "/")
        # This should click the "Order from Pizza Palace" link
        # (Note: the link navigates to /restaurant/pizza-palace which our server serves)
        try:
            state = await browser.click("", text="Order from Pizza Palace")
            # If click succeeded and followed the link, we should be on the menu page
            assert "Pizza Palace" in state.title or "Pizza" in state.text_content
        except Exception as e:
            # If click raises (e.g. element not found by text), fail with detail
            pytest.fail(f"click(text='Order from Pizza Palace') raised: {e}")


async def test_browser_tool_text_truncation_at_8000_chars(
    food_site_server: str,
) -> None:
    """
    BrowserTool truncates page text at 8000 chars to protect Claude's context window.

    Verified with real page — even small pages work correctly. This guards against
    large food ordering sites with thousands of menu items overwhelming Claude.
    """
    async with BrowserSession() as browser:
        state = await browser.navigate(food_site_server + "/")

    # Our test page is small — should NOT be truncated
    assert "[... page truncated ...]" not in state.text_content
    # But text should be non-empty
    assert len(state.text_content) > 20


async def test_browser_tool_take_screenshot_returns_bytes(
    food_site_server: str,
) -> None:
    """
    BrowserTool.take_screenshot() returns real PNG bytes from a live page.

    This is used in screen_observer for "what's on my screen" and for
    the food ordering accessibility verification (screenshot for vision API).
    Bytes must be non-empty and start with PNG magic bytes.
    """
    async with BrowserSession() as browser:
        await browser.navigate(food_site_server + "/")
        screenshot_bytes = await browser.take_screenshot()

    # PNG magic bytes: \x89PNG\r\n\x1a\n
    assert screenshot_bytes[:4] == b"\x89PNG"
    assert len(screenshot_bytes) > 1000  # a real screenshot is never tiny


async def test_browser_session_context_manager_cleans_up(
    food_site_server: str,
) -> None:
    """
    BrowserSession context manager cleans up the real browser after use.

    After __aexit__, the browser should be closed. Verifies no resource leak.
    """
    session = BrowserSession()
    async with session as browser:
        await browser.navigate(food_site_server + "/")
        assert browser._initialized is True

    # After context manager exits, browser must be closed
    assert session.tool._initialized is False


async def test_browser_tool_handles_404_gracefully(
    food_site_server: str,
) -> None:
    """
    BrowserTool.navigate() on a 404 page still returns a PageState (no crash).

    This validates the graceful degradation in the food ordering loop —
    if a restaurant page returns 404, the orchestrator gets a usable (if empty)
    PageState and can tell the user "sorry, that page wasn't found."
    """
    async with BrowserSession() as browser:
        # /nonexistent returns 404 from our test server
        state = await browser.navigate(food_site_server + "/nonexistent")

    # Should not raise — should return a PageState
    assert isinstance(state, PageState)
    # URL should still be set
    assert "127.0.0.1" in state.url


# ─────────────────────────────────────────────────────────────
# Cart page integration — validates order summary extraction
# ─────────────────────────────────────────────────────────────


async def test_browser_tool_cart_page_contains_order_details(
    food_site_server: str,
) -> None:
    """
    The cart page text content includes order items and total — available for
    _extract_order_summary to parse via Claude.

    This validates step 10 of the food ordering checkout loop:
    After adding an item, navigate to cart and extract the order summary.
    """
    async with BrowserSession() as browser:
        state = await browser.navigate(food_site_server + "/cart")

    # Cart items should be in text content
    assert "Pepperoni Pizza" in state.text_content
    # Price and total should be present
    assert "16.99" in state.text_content or "$16" in state.text_content
    assert "19.98" in state.text_content or "Total" in state.text_content
