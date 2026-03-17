"""
E2E test: Food ordering flow — Phase 2 completion gate.

Tests the complete "order me food" user flow from user request through:
  1. Intent classification (order_food)
  2. Tool install offer (browser)
  3. Financial risk disclosure (mandatory)
  4. Browser navigation
  5. Per-transaction order confirmation
  6. Response returned

External APIs mocked: Claude (intent classifier), Playwright (browser navigation).
Real: orchestrator, planner, confirmation gate, disclosure texts, tool registry logic.

Per ARCHITECTURE.md: "browser as universal adapter" — Claude navigates any food
ordering site. No DoorDash-specific code. Tests verify the flow, not the site.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from blind_assistant.core.confirmation import ConfirmationGate
from blind_assistant.core.orchestrator import Orchestrator, UserContext
from blind_assistant.tools.browser import BrowserTool, PageState

pytestmark = pytest.mark.e2e


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def config() -> dict:
    """Minimal config for E2E food ordering tests."""
    return {
        "telegram_enabled": False,
        "voice_local_enabled": False,
        "vault_path": "/tmp/test_vault_e2e_food",  # noqa: S108
        "voice": {"prompt_timeout_seconds": 5},
    }


@pytest.fixture
def user_context() -> UserContext:
    """Standard user context for food ordering E2E tests."""
    return UserContext(
        user_id="test_blind_user",
        session_id="food_order_session",
        verbosity="standard",
        speech_rate=1.0,
        output_mode="voice_text",
        braille_mode=False,
    )


@pytest.fixture
def brief_user_context() -> UserContext:
    """Brief verbosity context (power user)."""
    return UserContext(
        user_id="marcus_power",
        session_id="brief_food_session",
        verbosity="brief",
        speech_rate=1.5,
        output_mode="voice_text",
        braille_mode=False,
    )


@pytest.fixture
def mock_food_page_state() -> PageState:
    """Simulates a DoorDash search results page."""
    return PageState(
        url="https://www.doordash.com/search/store/?q=pizza",
        title="DoorDash — Pizza near you",
        text_content=(
            "Pizza Palace — 4.5 stars — 25-35 min — $2.99 delivery\n"
            "Taco Town — 4.2 stars — 20-30 min — $0 delivery\n"
            "Burger Barn — 4.0 stars — 30-45 min — $1.99 delivery\n"
        ),
    )


def _make_orchestrator_with_mock_browser(
    config: dict,
    mock_page_state: PageState,
    installed: bool = True,
) -> tuple[Orchestrator, MagicMock, ConfirmationGate]:
    """
    Build an Orchestrator with all dependencies mocked:
    - ConfirmationGate: real (so confirmation queues work)
    - ToolRegistry: mocked (controls whether browser is "installed")
    - BrowserTool: mocked with a fake navigation response
    - Planner: mocked to always return order_food intent

    Returns (orchestrator, mock_browser_tool, confirmation_gate).
    """
    from blind_assistant.core.planner import Intent

    gate = ConfirmationGate()
    orc = Orchestrator(config)
    orc.confirmation_gate = gate
    orc._initialized = True

    # Mock planner to classify any message as "order_food"
    mock_planner = MagicMock()
    mock_planner.classify_intent = AsyncMock(
        return_value=Intent(
            type="order_food",
            description="order a pizza",
            required_tools=["browser"],
            parameters={"food": "pizza"},
            is_high_stakes=True,
            confidence=0.95,
        )
    )
    orc.planner = mock_planner

    # Mock tool registry
    mock_registry = MagicMock()
    mock_registry.is_installed.return_value = installed  # browser already installed

    mock_browser = MagicMock(spec=BrowserTool)
    mock_browser.navigate = AsyncMock(return_value=mock_page_state)
    # get_page_state is called during checkout navigation steps
    mock_browser.get_page_state = AsyncMock(return_value=mock_page_state)
    mock_browser.click = AsyncMock()

    if installed:
        mock_registry.get_installed_tool.return_value = mock_browser
    else:
        mock_registry.get_installed_tool.return_value = None
        # For the tool install flow (not installed):
        mock_registry.get_available_tool.return_value = {
            "name": "browser",
            "package": "playwright",
            "version": "1.40.0",
            "description": "a web browser I can control to navigate any website on your behalf",
            "task_description": "navigate websites to complete tasks",
        }
        mock_registry.install_tool = AsyncMock(return_value=True)

    orc.tool_registry = mock_registry

    return orc, mock_browser, gate


# ─────────────────────────────────────────────────────────────
# E2E test 1: Happy path — user accepts risk disclosure, browser navigates
# ─────────────────────────────────────────────────────────────


async def test_food_order_happy_path_disclosure_accepted(
    config: dict,
    user_context: UserContext,
    mock_food_page_state: PageState,
) -> None:
    """
    Full happy path: user says "order me food" →
    risk disclosure → user says "yes" →
    browser navigates to food site → checkout loop completes.

    Verifies: disclosure fires, browser navigates, order completes.
    The Claude-powered page analysis helpers are patched so this test
    does not require the anthropic package in the test environment.
    """
    orc, mock_browser, gate = _make_orchestrator_with_mock_browser(config, mock_food_page_state, installed=True)
    gate.register_session(user_context.session_id)

    updates: list[str] = []
    response_count = [0]

    # Patch all Claude-powered helpers — E2E tests verify the flow, not the AI reasoning
    with (
        patch.object(orc, "_extract_options_from_page", new=AsyncMock(return_value="1. Pizza Palace. 2. Taco Town.")),
        patch.object(orc, "_navigate_to_user_choice", new=AsyncMock(return_value=mock_food_page_state)),
        patch.object(orc, "_add_item_to_cart", new=AsyncMock(return_value=mock_food_page_state)),
        patch.object(orc, "_extract_order_summary", new=AsyncMock(return_value="1x Pepperoni Pizza, $18.50")),
        patch.object(orc, "_place_order", new=AsyncMock(return_value={"success": True, "confirmation": "Order #12345"})),
    ):

        async def update_cb(msg: str) -> None:
            updates.append(msg)
            response_count[0] += 1
            # Accept all prompts (disclosure + restaurant pick + item pick + confirmations)
            gate.submit_response(user_context.session_id, "yes")

        result = await orc._handle_order_food(
            MagicMock(
                type="order_food",
                description="order me a pizza",
                parameters={"food": "pizza"},
                is_high_stakes=True,
                required_tools=["browser"],
            ),
            user_context,
            update_cb,
        )

    # Risk disclosure must have been sent
    all_updates = " ".join(updates).lower()
    assert any(keyword in all_updates for keyword in ("risk", "payment", "financial", "financial information")), (
        f"Risk disclosure not found in updates: {updates}"
    )

    # Browser must have been asked to navigate
    mock_browser.navigate.assert_called_once()
    call_url = mock_browser.navigate.call_args[0][0]
    assert "doordash" in call_url.lower(), f"Expected doordash URL, got: {call_url}"

    # Order should have completed (order_placed or order placed message)
    assert result.get("order_placed") is True or "placed" in result["text"].lower() or "confirmed" in result["text"].lower(), (
        f"Expected order to be placed, got: {result}"
    )


# ─────────────────────────────────────────────────────────────
# E2E test 2: User declines risk disclosure — order cancelled
# ─────────────────────────────────────────────────────────────


async def test_food_order_risk_disclosure_declined(
    config: dict,
    user_context: UserContext,
    mock_food_page_state: PageState,
) -> None:
    """
    User says "no" to risk disclosure → order cancelled →
    browser never called → reassuring message returned.
    """
    orc, mock_browser, gate = _make_orchestrator_with_mock_browser(config, mock_food_page_state, installed=True)
    gate.register_session(user_context.session_id)

    updates: list[str] = []
    response_count = [0]

    async def update_cb(msg: str) -> None:
        updates.append(msg)
        response_count[0] += 1
        if response_count[0] == 2:  # Second update = risk disclosure arrives
            gate.submit_response(user_context.session_id, "no")

    result = await orc._handle_order_food(
        MagicMock(
            type="order_food",
            description="order me a pizza",
            parameters={"food": "pizza"},
            is_high_stakes=True,
            required_tools=["browser"],
        ),
        user_context,
        update_cb,
    )

    # Browser must NOT have been called
    mock_browser.navigate.assert_not_called()

    # Response should be a cancellation message (reassuring, no pressure)
    response_text = result["text"].lower()
    assert any(phrase in response_text for phrase in ("no problem", "won't proceed", "any time", "cancel")), (
        f"Expected cancellation message, got: {result['text']}"
    )

    # CRITICAL: No artificial urgency (ETHICS_REQUIREMENTS.md)
    assert "now or never" not in response_text
    assert "hurry" not in response_text
    assert "expires" not in response_text


# ─────────────────────────────────────────────────────────────
# E2E test 3: Tool install flow — browser not installed, user confirms install
# ─────────────────────────────────────────────────────────────


async def test_food_order_triggers_browser_install_when_not_installed(
    config: dict,
    user_context: UserContext,
    mock_food_page_state: PageState,
) -> None:
    """
    When browser tool is not installed, the orchestrator offers to install it.
    User says "yes" → tool installs → then asks user to request food again.
    """
    orc, mock_browser, gate = _make_orchestrator_with_mock_browser(config, mock_food_page_state, installed=False)
    gate.register_session(user_context.session_id)

    updates: list[str] = []

    async def update_cb(msg: str) -> None:
        updates.append(msg)
        # Respond "yes" to install consent
        gate.submit_response(user_context.session_id, "yes")

    # Call _offer_tool_install directly (the part of handle_message that fires for missing tools)
    tool_info = orc.tool_registry.get_available_tool("browser")
    await orc._offer_tool_install(
        tool_name="browser",
        tool_info=tool_info,
        context=user_context,
        update=update_cb,
    )

    # Should have offered to install and user said yes
    install_mentions = [u for u in updates if "install" in u.lower() or "browser" in u.lower()]
    assert install_mentions, "Install consent prompt was not sent"

    # install_tool should have been called
    orc.tool_registry.install_tool.assert_called_once_with("browser", tool_info)


# ─────────────────────────────────────────────────────────────
# E2E test 4: Accessibility assertion — no visual-only language
# ─────────────────────────────────────────────────────────────


async def test_food_order_responses_contain_no_visual_only_language(
    config: dict,
    user_context: UserContext,
    mock_food_page_state: PageState,
) -> None:
    """
    All messages sent to the user during food ordering must be free of
    visual-only language. Per ETHICS_REQUIREMENTS.md: the assistant speaks
    to a blind user — "look at the screen", "you can see", etc. are meaningless.

    This is the accessibility assertion required for all E2E tests.
    """
    orc, mock_browser, gate = _make_orchestrator_with_mock_browser(config, mock_food_page_state, installed=True)
    gate.register_session(user_context.session_id)

    updates: list[str] = []
    response_count = [0]

    async def update_cb(msg: str) -> None:
        updates.append(msg)
        response_count[0] += 1
        if response_count[0] == 2:
            gate.submit_response(user_context.session_id, "yes")

    await orc._handle_order_food(
        MagicMock(
            type="order_food",
            description="order me food",
            parameters={"food": "pizza"},
            is_high_stakes=True,
            required_tools=["browser"],
        ),
        user_context,
        update_cb,
    )

    # Check ALL messages sent to user for visual-only language
    visual_only_phrases = [
        "look at the screen",
        "you can see",
        "as you can see",
        "the blue button",
        "click the red",
        "tap the icon",
        "visible on screen",
    ]

    for update in updates:
        update_lower = update.lower()
        for phrase in visual_only_phrases:
            assert phrase not in update_lower, (
                f"Visual-only phrase '{phrase}' found in message to blind user: '{update}'"
            )


# ─────────────────────────────────────────────────────────────
# E2E test 5: Brief verbosity — disclosure is shorter but still fires
# ─────────────────────────────────────────────────────────────


async def test_food_order_brief_user_gets_shorter_disclosure(
    config: dict,
    brief_user_context: UserContext,
    mock_food_page_state: PageState,
) -> None:
    """
    Power user (brief verbosity) gets a shorter risk disclosure but it MUST still fire.
    The assistant cannot silently skip the disclosure for "experienced" users.
    """
    from blind_assistant.security.disclosure import FINANCIAL_RISK_DISCLOSURE

    orc, mock_browser, gate = _make_orchestrator_with_mock_browser(config, mock_food_page_state, installed=True)
    gate.register_session(brief_user_context.session_id)

    risk_messages: list[str] = []
    response_count = [0]

    async def update_cb(msg: str) -> None:
        response_count[0] += 1
        if "risk" in msg.lower() or "payment" in msg.lower() or "financial" in msg.lower():
            risk_messages.append(msg)
        gate.submit_response(brief_user_context.session_id, "yes")

    await orc._handle_order_food(
        MagicMock(
            type="order_food",
            description="order pizza",
            parameters={"food": "pizza"},
            is_high_stakes=True,
            required_tools=["browser"],
        ),
        brief_user_context,
        update_cb,
    )

    # Disclosure MUST fire even for brief users
    assert risk_messages, "Risk disclosure did not fire for brief/power user — this is a compliance violation"

    # Brief disclosure should be shorter than the full version
    if risk_messages:
        assert len(risk_messages[0]) < len(FINANCIAL_RISK_DISCLOSURE), (
            "Brief user received full-length disclosure; expected shorter version"
        )


# ─────────────────────────────────────────────────────────────
# E2E test 6: Order confirmation uses correct financial flow
# ─────────────────────────────────────────────────────────────


async def test_food_order_confirm_fires_full_financial_confirmation(
    config: dict,
    user_context: UserContext,
    mock_food_page_state: PageState,
) -> None:
    """
    _handle_order_food_confirm fires both steps:
    1. Risk disclosure + acknowledgment
    2. Order summary + per-transaction confirmation

    This test verifies that BOTH confirmations are required before any order completes.
    Per ETHICS_REQUIREMENTS.md: per-transaction confirmation, not session-level.
    """
    orc, _, gate = _make_orchestrator_with_mock_browser(config, mock_food_page_state, installed=True)
    gate.register_session(user_context.session_id)

    updates: list[str] = []
    confirmation_count = [0]

    async def update_cb(msg: str) -> None:
        updates.append(msg)
        confirmation_count[0] += 1
        # Always respond "yes" — want to test that BOTH steps are asked
        gate.submit_response(user_context.session_id, "yes")

    result = await orc._handle_order_food_confirm(
        order_summary="1x Pepperoni Pizza, 1x Diet Coke",
        total_amount="$21.98",
        context=user_context,
        update=update_cb,
    )

    # Must have received at least 2 messages: disclosure + order confirmation
    assert confirmation_count[0] >= 2, (
        f"Expected at least 2 confirmation messages (disclosure + order), got {confirmation_count[0]}"
    )

    # The order summary must appear in one of the messages
    all_text = " ".join(updates)
    assert "Pepperoni Pizza" in all_text or "21.98" in all_text, "Order summary not shown to user before confirmation"

    # Result should be True (user confirmed both steps)
    assert result is True


# ─────────────────────────────────────────────────────────────
# E2E test 7: Navigation error — graceful degradation
# ─────────────────────────────────────────────────────────────


async def test_food_order_navigation_error_does_not_crash(
    config: dict,
    user_context: UserContext,
) -> None:
    """
    If the browser tool raises during navigation (network issue, site down),
    the orchestrator returns a helpful error message — never crashes.
    """
    orc, mock_browser, gate = _make_orchestrator_with_mock_browser(
        config,
        PageState(url="", title="", text_content=""),
        installed=True,
    )
    # Override navigate to raise
    mock_browser.navigate = AsyncMock(side_effect=Exception("Connection refused"))
    gate.register_session(user_context.session_id)

    response_count = [0]

    async def update_cb(msg: str) -> None:
        response_count[0] += 1
        gate.submit_response(user_context.session_id, "yes")

    # Should not raise — should return helpful error message
    result = await orc._handle_order_food(
        MagicMock(
            type="order_food",
            description="order food",
            parameters={"food": "pizza"},
            is_high_stakes=True,
            required_tools=["browser"],
        ),
        user_context,
        update_cb,
    )

    assert "text" in result
    response_lower = result["text"].lower()
    assert any(phrase in response_lower for phrase in ("trouble", "connection refused", "try", "different")), (
        f"Expected helpful error message, got: {result['text']}"
    )


# ─────────────────────────────────────────────────────────────
# E2E test 8: handle_message routes "order food" to food handler
# ─────────────────────────────────────────────────────────────


async def test_handle_message_routes_order_food_through_pipeline(
    config: dict,
    user_context: UserContext,
    mock_food_page_state: PageState,
) -> None:
    """
    When user says "order me a pizza", handle_message:
    1. Classifies intent as order_food
    2. Checks if browser is installed (it is — mocked as installed)
    3. Calls _handle_order_food which fires risk disclosure
    4. Returns a response

    This is the highest-level integration test for the food ordering path.
    """
    orc, mock_browser, gate = _make_orchestrator_with_mock_browser(config, mock_food_page_state, installed=True)
    gate.register_session(user_context.session_id)

    response_count = [0]

    async def update_cb(msg: str) -> None:
        response_count[0] += 1
        # Accept any confirmation
        gate.submit_response(user_context.session_id, "yes")

    # The full handle_message call
    response = await orc.handle_message(
        text="order me a pizza",
        context=user_context,
        response_callback=update_cb,
    )

    # Should have gotten some response back
    assert response is not None
    assert response.text  # non-empty

    # Planner classify_intent was called
    orc.planner.classify_intent.assert_called_once()
