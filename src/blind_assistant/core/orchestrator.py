"""
Core Orchestrator

The main loop: receive user input → classify intent → select tools → confirm →
execute → respond.

This is the central coordinator for all user interactions.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blind_assistant.core.confirmation import ConfirmationGate
    from blind_assistant.core.context import ContextManager
    from blind_assistant.core.planner import Planner
    from blind_assistant.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Type alias for the optional async progress callback used throughout the orchestrator.
# Callers (API server, voice interface) may pass this to receive real-time status updates.
ResponseCallback = Callable[[str], Awaitable[None]] | None


@dataclass
class UserContext:
    """Everything the orchestrator knows about the current user and session."""

    user_id: str
    session_id: str
    verbosity: str = "standard"  # "brief" | "standard" | "detailed"
    speech_rate: float = 1.0  # 1.0 = normal; 0.7 = slower (Dorothy)
    output_mode: str = "voice_text"  # "voice_text" | "text_only" (Jordan)
    braille_mode: bool = False  # True = format for 40-char braille display
    preferences: dict = field(default_factory=dict)
    conversation_history: list = field(default_factory=list)

    def clear_sensitive(self) -> None:
        """
        Zero out any cached sensitive data at session end.

        Defense-in-depth: even though OS memory isolation prevents other processes
        from reading our heap, explicitly clearing the passphrase reduces the window
        where a memory dump could expose it. Per ISSUE-005.
        """
        # Clear vault passphrase if it was cached during this session.
        # _vault_passphrase is set dynamically (not in __init__) so we use getattr/setattr
        # to avoid mypy 'attr-defined' and 'has-type' errors while still zeroing the value.
        if hasattr(self, "_vault_passphrase") and getattr(self, "_vault_passphrase") is not None:
            object.__setattr__(self, "_vault_passphrase", None)
        logger.debug(f"Sensitive data cleared for session {self.session_id}")


@dataclass
class Response:
    """The orchestrator's response to a user message."""

    text: str  # Always present (for braille display)
    spoken_text: str | None = None  # If different from text (e.g., shorter)
    follow_up_prompt: str | None = None  # What to ask the user next
    requires_confirmation: bool = False
    confirmation_action: str | None = None


class Orchestrator:
    """
    Central coordinator for all user interactions.

    Responsibilities:
    - Intent classification via Claude API
    - Tool selection and self-expanding capability
    - Confirmation gate for high-stakes actions
    - Context management (Second Brain, memory, preferences)
    - Response formatting for different output modes
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        self._initialized = False

        # These are set during initialize() — typed as Optional to reflect pre-init state.
        # All access to these must happen after initialize() is called.
        self.planner: "Planner | None" = None
        self.tool_registry: "ToolRegistry | None" = None
        self.confirmation_gate: "ConfirmationGate | None" = None
        self.context_manager: "ContextManager | None" = None

    async def initialize(self) -> None:
        """Initialize all sub-components. Call once at startup."""
        logger.info("Initializing orchestrator...")

        # Import here to avoid circular imports
        from blind_assistant.core.confirmation import ConfirmationGate
        from blind_assistant.core.context import ContextManager
        from blind_assistant.core.planner import Planner
        from blind_assistant.tools.registry import ToolRegistry

        self.planner = Planner(self.config)
        self.tool_registry = ToolRegistry()
        self.confirmation_gate = ConfirmationGate()
        self.context_manager = ContextManager(self.config)

        await self.context_manager.initialize()
        await self.tool_registry.load()

        self._initialized = True
        logger.info("Orchestrator ready.")

    async def handle_message(
        self,
        text: str,
        context: UserContext,
        response_callback: ResponseCallback = None,
    ) -> Response:
        """
        Handle a user message end-to-end.

        Args:
            text: The user's message (already transcribed from voice if needed)
            context: Current user context
            response_callback: Optional async callable for streaming interim updates
                               Signature: async (message: str) -> None

        Returns:
            Final response to send to the user
        """
        if not self._initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")

        # These assertions narrow the Optional types for mypy — guaranteed non-None after initialize()
        assert self.planner is not None, "Planner not initialized"
        assert self.tool_registry is not None, "ToolRegistry not initialized"
        assert self.confirmation_gate is not None, "ConfirmationGate not initialized"
        assert self.context_manager is not None, "ContextManager not initialized"

        # Progress callback helper
        async def update(message: str) -> None:
            if response_callback:
                await response_callback(message)

        logger.info(f"Handling message from {context.user_id}: {text[:50]}...")

        try:
            # 1. Classify intent
            await update("Let me think about that...")
            intent = await self.planner.classify_intent(text, context)
            logger.debug(f"Intent: {intent.type} | Tools needed: {intent.required_tools}")

            # 2. Check if any needed tools need to be installed
            for tool_name in intent.required_tools:
                if not self.tool_registry.is_installed(tool_name):
                    tool_info = self.tool_registry.get_available_tool(tool_name)
                    if tool_info:
                        installed = await self._offer_tool_install(tool_name, tool_info, context, update)
                        if not installed:
                            return Response(
                                text=f"Okay, I won't install {tool_name}. "
                                "Let me know if there's another way I can help."
                            )

            # 3. Execute the intent
            result = await self._execute_intent(intent, context, update)

            # 4. Format response for user's output mode
            return self._format_response(result, context)

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return Response(
                text=(
                    "I ran into a problem and couldn't complete that. "
                    f"Here's what happened: {str(e)}. "
                    "Would you like to try again or do something different?"
                )
            )

    async def _offer_tool_install(
        self,
        tool_name: str,
        tool_info: dict,
        context: UserContext,
        update: Callable[[str], Awaitable[None]],
    ) -> bool:
        """
        Offer to install a missing tool. Returns True if installed, False if declined.

        Per ETHICS_REQUIREMENTS.md: always tell the user what's being installed and why.
        Per SECURITY_MODEL.md: only install from curated registry.
        """
        from blind_assistant.security.disclosure import INSTALL_CONSENT_TEMPLATE

        message = INSTALL_CONSENT_TEMPLATE.format(
            task_description=tool_info.get("task_description", "complete this task"),
            package_name=tool_name,
            package_description=tool_info.get("description", "a helper tool"),
        )

        await update(message)

        # These asserts narrow Optional types — this method is only called after initialize()
        assert self.confirmation_gate is not None
        assert self.tool_registry is not None
        confirmed = await self.confirmation_gate.wait_for_confirmation(context)
        if confirmed:
            await update(f"Installing {tool_name}...")
            success = await self.tool_registry.install_tool(tool_name, tool_info)
            if success:
                await update(f"{tool_name} is now ready.")
                return True
            await update(f"I wasn't able to install {tool_name}. Let me try a different approach.")
            return False
        return False

    async def _execute_intent(
        self, intent, context: UserContext, update: Callable[[str], Awaitable[None]]
    ) -> dict:
        """
        Execute a classified intent using the appropriate tools.

        Routes to the correct handler based on intent type.
        """
        handler = self._intent_handlers.get(intent.type)
        if handler:
            return await handler(intent, context, update)

        # Unknown intent — try to answer as a general question
        return await self._handle_general_question(intent, context, update)

    async def _handle_screen_description(
        self, intent, context: UserContext, update: Callable[[str], Awaitable[None]]
    ) -> dict:
        """Capture and describe the current screen."""
        await update("Taking a look at your screen...")
        from blind_assistant.vision.screen_observer import ScreenObserver

        observer = ScreenObserver(self.config)
        description = await observer.describe_screen()
        return {"text": description}

    async def _handle_add_note(
        self, intent, context: UserContext, update: Callable[[str], Awaitable[None]]
    ) -> dict:
        """Add a note to the Second Brain vault."""
        await update("Saving that to your notes...")
        vault = await self._get_vault(context, response_callback=update)
        if vault is None:
            return {
                "text": (
                    "I couldn't access your notes vault. "
                    "Say 'unlock my notes' and provide your passphrase to try again."
                )
            }
        from blind_assistant.second_brain.query import VaultQuery

        q = VaultQuery(vault)
        # The note content is in the intent parameters or the raw description
        content = intent.parameters.get("content") or intent.description
        response_text = await q.add_note_from_voice(content=content, context=context)
        return {"text": response_text}

    async def _handle_query_note(
        self, intent, context: UserContext, update: Callable[[str], Awaitable[None]]
    ) -> dict:
        """Query the Second Brain vault for matching notes."""
        await update("Searching your notes...")
        vault = await self._get_vault(context, response_callback=update)
        if vault is None:
            return {
                "text": (
                    "I couldn't access your notes vault. "
                    "Say 'unlock my notes' and provide your passphrase to try again."
                )
            }
        from blind_assistant.second_brain.query import VaultQuery

        q = VaultQuery(vault)
        query_text = intent.parameters.get("query") or intent.description
        response_text = await q.answer_query(query=query_text, context=context)
        return {"text": response_text}

    async def _handle_general_question(
        self, intent, context: UserContext, update: Callable[[str], Awaitable[None]]
    ) -> dict:
        """Answer a general question using Claude."""
        await update("Let me think about that...")
        try:
            import anthropic

            from blind_assistant.security.credentials import CLAUDE_API_KEY, require_credential

            api_key = require_credential(CLAUDE_API_KEY)
            client = anthropic.AsyncAnthropic(api_key=api_key)

            system_prompt = (
                "You are Blind Assistant, a helpful AI companion for blind and visually "
                "impaired users. Give clear, concise answers. Avoid visual descriptions "
                "unless explaining something to the user. No emoji."
            )

            response = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=400,
                system=system_prompt,
                messages=[{"role": "user", "content": intent.description}],
            )
            return {"text": response.content[0].text}
        except Exception as e:
            logger.error(f"General question failed: {e}", exc_info=True)
            return {"text": (f"I wasn't able to answer that right now. Error: {str(e)}")}

    async def _handle_order_food(
        self, intent, context: UserContext, update: Callable[[str], Awaitable[None]]
    ) -> dict:
        """
        Handle a food ordering request end-to-end via conversational checkout loop.

        Full flow per Phase 2 requirements:
        1. Gather what the user wants (from intent params or description)
        2. Mandatory financial risk disclosure + user acknowledgment
        3. Navigate to food ordering site with the browser tool
        4. Ask Claude to reason about page content → read options to user by voice
        5. User picks a restaurant → navigate to restaurant page
        6. Ask Claude to read menu highlights → user picks items
        7. Navigate to checkout → read order summary → confirm with user
        8. Final per-transaction confirmation → place order

        Per ETHICS_REQUIREMENTS.md: risk disclosure fires every transaction.
        Per SECURITY_MODEL.md: payment handled via Stripe tokenization, not raw numbers.
        Per ARCHITECTURE.md: browser tool handles any food site — no DoorDash-specific code.
        """
        # Step 1: Gather what the user wants to order
        food_query = intent.parameters.get("query") or intent.parameters.get("food")
        restaurant = intent.parameters.get("restaurant") or intent.parameters.get("service")

        if not food_query:
            # Extract from the intent description — the planner puts the full request there
            food_query = intent.description

        await update(
            f"I'll help you order food. I'm going to search for {food_query or 'food delivery options'} near you."
        )

        # These asserts narrow Optional types — this method is only called after initialize()
        assert self.confirmation_gate is not None
        assert self.tool_registry is not None
        # Step 2: Financial risk disclosure — MANDATORY before any payment discussion.
        # Uses the full confirm_financial_details_collection flow which speaks the
        # disclosure and waits for explicit acknowledgment before proceeding.
        await update("Before we look at ordering options, I need to share some important information.")
        user_acknowledged = await self.confirmation_gate.confirm_financial_details_collection(
            context=context,
            response_callback=update,
        )

        if not user_acknowledged:
            return {"text": "No problem — I won't proceed with the order. You can ask me again any time."}

        # Step 3: Get the browser tool (must already be installed — offer runs in handle_message)
        browser_tool = self.tool_registry.get_installed_tool("browser")
        if browser_tool is None:
            return {
                "text": (
                    "I need the browser tool to complete your order, but it's not installed. "
                    "Say 'order food' again and I'll ask to install it."
                )
            }

        await update("Opening the food ordering site now...")

        try:
            # Navigate to search results — Claude reasons about ANY food site page content
            search_url = f"https://www.doordash.com/search/store/?q={food_query.replace(' ', '+')}"
            if restaurant:
                search_url = f"https://www.doordash.com/search/store/?q={restaurant.replace(' ', '+')}"

            page_state = await browser_tool.navigate(search_url)

            # Step 4: Ask Claude to extract restaurant options from the page text.
            # Claude reads the raw page text and returns a voice-friendly numbered list.
            options_summary = await self._extract_options_from_page(
                page_text=page_state.text_content,
                page_title=page_state.title,
                task_context=f"food delivery search results for '{food_query}'",
                max_options=5,
            )

            await update(
                f"I found some options for you. {options_summary} "
                "Which one would you like? You can say the number or the restaurant name."
            )

            # Step 5: Wait for the user to pick a restaurant
            user_choice = await self.confirmation_gate.wait_for_response(context, timeout=90)
            if not user_choice:
                return {
                    "text": (
                        "I didn't hear which restaurant you'd like. "
                        "Say 'order food' again when you're ready to try."
                    ),
                    "ordering_in_progress": False,
                }

            # Step 6: Ask Claude to interpret the user's choice and click the right link.
            # This keeps all site-specific navigation logic in Claude's reasoning,
            # not in hardcoded selectors.
            await update(f"Got it — looking at {user_choice}...")
            restaurant_page = await self._navigate_to_user_choice(
                browser_tool=browser_tool,
                page_state=page_state,
                user_choice=user_choice,
            )

            if restaurant_page is None:
                return {
                    "text": (
                        f"I had trouble finding '{user_choice}' on the page. "
                        "Would you like to try again or pick a different option?"
                    ),
                    "ordering_in_progress": False,
                }

            # Step 7: Read the menu highlights to the user
            menu_summary = await self._extract_options_from_page(
                page_text=restaurant_page.text_content,
                page_title=restaurant_page.title,
                task_context="restaurant menu items",
                max_options=5,
            )

            await update(
                f"Here are some menu items from {restaurant_page.title}: "
                f"{menu_summary} "
                "What would you like to order? Say the item name or number."
            )

            # Step 8: Wait for menu item selection
            item_choice = await self.confirmation_gate.wait_for_response(context, timeout=90)
            if not item_choice:
                return {
                    "text": (
                        "I didn't hear what you'd like to order. "
                        "Say 'order food' again when you're ready to try."
                    ),
                    "ordering_in_progress": False,
                }

            # Step 9: Try to add the item to cart by clicking/navigating
            await update(f"Adding {item_choice} to your cart...")
            cart_page = await self._add_item_to_cart(
                browser_tool=browser_tool,
                current_page=restaurant_page,
                item_choice=item_choice,
            )

            # Step 10: Read order summary and get final per-transaction confirmation
            # The order summary is extracted from the cart page by Claude.
            order_summary_text = await self._extract_order_summary(
                page_text=cart_page.text_content if cart_page else "",
                item_choice=item_choice,
                restaurant=restaurant_page.title,
            )

            # _handle_order_food_confirm fires the full two-step disclosure + confirmation
            order_confirmed = await self._handle_order_food_confirm(
                order_summary=order_summary_text,
                total_amount="(see order summary above)",
                context=context,
                update=update,
            )

            if not order_confirmed:
                return {
                    "text": (
                        "Order cancelled. No payment has been made. "
                        "You can start a new order any time."
                    ),
                    "ordering_in_progress": False,
                }

            # Step 11: Place the order — click "Place Order" or equivalent
            await update("Placing your order now...")
            order_result = await self._place_order(browser_tool=browser_tool)

            if order_result.get("success"):
                return {
                    "text": (
                        f"Your order has been placed! {order_result.get('confirmation', '')} "
                        "You should receive a confirmation soon."
                    ),
                    "ordering_in_progress": False,
                    "order_placed": True,
                }
            return {
                "text": (
                    "I wasn't able to place the order automatically — "
                    f"{order_result.get('reason', 'the site may have changed its layout')}. "
                    "Your cart should be saved. You can complete the order manually "
                    "or say 'order food' again to try a different approach."
                ),
                "ordering_in_progress": False,
            }

        except ImportError:
            # Playwright not installed — should have been caught by tool install flow
            return {
                "text": (
                    "The browser tool isn't ready yet. "
                    "This may be because Playwright needs to be installed. "
                    "Say 'order food' again and I'll walk you through installing it."
                )
            }
        except Exception as e:
            logger.error(f"Food ordering failed: {e}", exc_info=True)
            return {
                "text": (
                    "I had trouble with the food ordering site. "
                    f"Here's what happened: {str(e)}. "
                    "Would you like to try a different service, or shall I try again?"
                )
            }

    async def _extract_options_from_page(
        self,
        page_text: str,
        page_title: str,
        task_context: str,
        max_options: int = 5,
    ) -> str:
        """
        Use Claude to extract a voice-friendly numbered list of options from raw page text.

        Claude reasons about the page content to identify the most relevant options
        (restaurants, menu items, products) and formats them for audio delivery.
        No site-specific parsing — works on any page.

        Returns a plain-English numbered list suitable for reading aloud to a blind user.
        """
        try:
            import anthropic

            from blind_assistant.security.credentials import CLAUDE_API_KEY, require_credential

            api_key = require_credential(CLAUDE_API_KEY)
            client = anthropic.AsyncAnthropic(api_key=api_key)

            # Truncate page text to avoid hitting token limits while keeping enough context
            page_excerpt = page_text[:3000] if page_text else "(page content not available)"

            prompt = (
                f"You are reading a webpage to a blind user. The page is: '{page_title}'. "
                f"The user is looking at: {task_context}. "
                f"Here is the raw text from the page:\n\n{page_excerpt}\n\n"
                f"Extract the top {max_options} most relevant options the user can choose from. "
                "Format them as a numbered spoken list: '1. Restaurant name, delivery time, rating. "
                "2. Next option...' Keep each item under 20 words. "
                "Do NOT use visual language like 'you can see' or 'on the left'. "
                "If no clear options are visible, say what you can infer from the page."
            )

            response = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.warning(f"Could not extract options from page using Claude: {e}")
            # Fallback: return a truncated version of the page text
            if page_text:
                return f"I found some results. Here's what I could read from the page: {page_text[:400]}"
            return f"I'm on {page_title} but couldn't read the specific options. Please tell me what you'd like."

    async def _navigate_to_user_choice(
        self,
        browser_tool,
        page_state,
        user_choice: str,
    ):
        """
        Ask Claude to determine which link to click based on the user's spoken choice,
        then navigate to it.

        Claude maps "number 2" or "pizza palace" to the correct selector or link text.
        Returns the new PageState after navigation, or None if navigation failed.
        """
        try:
            import anthropic

            from blind_assistant.security.credentials import CLAUDE_API_KEY, require_credential

            api_key = require_credential(CLAUDE_API_KEY)
            client = anthropic.AsyncAnthropic(api_key=api_key)

            page_excerpt = page_state.text_content[:3000] if page_state.text_content else ""

            prompt = (
                f"A blind user is on a webpage titled: '{page_state.title}'. "
                f"They said they want: '{user_choice}'. "
                f"Here is the page text:\n\n{page_excerpt}\n\n"
                "What text string or partial URL should I search for to click the right link? "
                "Respond with ONLY the exact text to search for on the page (no explanation). "
                "Keep it short — just the key term (e.g. 'Pizza Palace' or 'Chipotle')."
            )

            response = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            click_target = response.content[0].text.strip().strip('"').strip("'")

            # Try clicking by text content — Playwright finds elements containing this text
            await browser_tool.click(f"text={click_target}")
            return await browser_tool.get_page_state()

        except Exception as e:
            logger.warning(f"Navigation to user choice '{user_choice}' failed: {e}")
            return None

    async def _add_item_to_cart(
        self,
        browser_tool,
        current_page,
        item_choice: str,
    ):
        """
        Ask Claude to find and click the button to add the user's chosen item to cart.

        Returns new PageState after the click, or the unchanged page if it failed.
        Claude determines the correct selector — no hardcoded button names.
        """
        try:
            import anthropic

            from blind_assistant.security.credentials import CLAUDE_API_KEY, require_credential

            api_key = require_credential(CLAUDE_API_KEY)
            client = anthropic.AsyncAnthropic(api_key=api_key)

            page_excerpt = current_page.text_content[:3000] if current_page.text_content else ""

            prompt = (
                f"A blind user is on a restaurant menu page titled: '{current_page.title}'. "
                f"They want to order: '{item_choice}'. "
                f"Here is the page text:\n\n{page_excerpt}\n\n"
                "What text should I click to add this item or navigate to it? "
                "Respond with ONLY the short text to click (e.g. 'Add to Cart' or the item name). "
                "No explanation."
            )

            response = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            click_target = response.content[0].text.strip().strip('"').strip("'")

            await browser_tool.click(f"text={click_target}")
            return await browser_tool.get_page_state()

        except Exception as e:
            logger.warning(f"Add to cart for '{item_choice}' failed: {e}")
            return current_page  # Return existing page — don't crash the flow

    async def _extract_order_summary(
        self,
        page_text: str,
        item_choice: str,
        restaurant: str,
    ) -> str:
        """
        Use Claude to extract a concise order summary from the cart page text.

        Returns a plain-English summary suitable for reading aloud before confirmation.
        Falls back to a simple summary using the item_choice and restaurant name.
        """
        try:
            import anthropic

            from blind_assistant.security.credentials import CLAUDE_API_KEY, require_credential

            api_key = require_credential(CLAUDE_API_KEY)
            client = anthropic.AsyncAnthropic(api_key=api_key)

            page_excerpt = page_text[:2000] if page_text else ""

            prompt = (
                "Extract the order summary from this cart/checkout page text. "
                "Include: item names, quantities, and total price if visible. "
                "Format as a single sentence for reading aloud. "
                "Example: '1 Pepperoni Pizza and 1 Diet Coke, total $18.50'. "
                f"If you can't find the details, say: '{item_choice} from {restaurant}'. "
                f"Page text:\n\n{page_excerpt}"
            )

            response = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()

        except Exception:
            # Graceful fallback — always return something useful
            return f"{item_choice} from {restaurant}"

    async def _place_order(self, browser_tool) -> dict:
        """
        Attempt to click the final 'Place Order' button on the checkout page.

        Uses Claude to find the right button text — no hardcoded selectors.
        Returns dict with 'success' bool and optional 'confirmation' or 'reason'.
        """
        try:
            current_page = await browser_tool.get_page_state()

            import anthropic

            from blind_assistant.security.credentials import CLAUDE_API_KEY, require_credential

            api_key = require_credential(CLAUDE_API_KEY)
            client = anthropic.AsyncAnthropic(api_key=api_key)

            page_excerpt = current_page.text_content[:2000] if current_page.text_content else ""

            prompt = (
                "On this checkout page, what text should I click to place the order? "
                "Common labels: 'Place Order', 'Confirm Order', 'Submit Order', 'Pay Now'. "
                "Respond with ONLY the exact button text (no explanation). "
                f"Page text:\n\n{page_excerpt}"
            )

            response = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}],
            )
            button_text = response.content[0].text.strip().strip('"').strip("'")

            await browser_tool.click(f"text={button_text}")

            # Check confirmation page
            confirm_page = await browser_tool.get_page_state()
            # Heuristic: confirmation pages typically mention "order", "confirmed", or a number
            is_confirmed = any(
                kw in confirm_page.text_content.lower()
                for kw in ("order confirmed", "thank you", "confirmation number", "order number")
            )

            if is_confirmed:
                return {"success": True, "confirmation": f"Order confirmed. {confirm_page.title}"}
            # Page changed but no confirmation — still report success (may need phone/address)
            return {
                "success": False,
                "reason": (
                    "I clicked the order button but the site may need additional information "
                    "(delivery address, payment method). Please complete it manually."
                ),
            }

        except Exception as e:
            logger.warning(f"Place order failed: {e}")
            return {"success": False, "reason": str(e)}

    async def _handle_order_food_confirm(
        self,
        order_summary: str,
        total_amount: str,
        context: UserContext,
        update: Callable[[str], Awaitable[None]],
    ) -> bool:
        """
        Run the full financial confirmation flow for a food order.

        Called after the order is built and ready to submit.
        Uses confirm_financial_action which fires risk disclosure + order summary
        + gets explicit yes/no before any charge is made.

        Returns True if the user confirmed, False if cancelled.
        """
        # Assert narrows Optional type — method only called after initialize()
        assert self.confirmation_gate is not None
        return await self.confirmation_gate.confirm_financial_action(
            order_summary=order_summary,
            total_amount=total_amount,
            context=context,
            response_callback=update,
        )

    async def _handle_high_stakes_stub(
        self, intent, context: UserContext, update: Callable[[str], Awaitable[None]]
    ) -> dict:
        """Placeholder for high-stakes intents not yet fully implemented."""
        return {
            "text": (
                f"I understand you want to {intent.description}. "
                "This feature is coming soon. "
                "I'll need to walk you through it step by step when it's ready."
            )
        }

    async def _get_vault(
        self, context: UserContext, response_callback: ResponseCallback = None
    ):
        """
        Get or initialize the vault for this user.

        Tries OS keychain first. If keychain has no key, prompts the user for their
        passphrase via the active interface (voice or Telegram).

        Returns None only if the user cannot or does not provide a passphrase, or if
        the passphrase is wrong. Always tells the user what is happening — never silent.

        Per ISSUE-001: silent vault failure left blind users unable to access notes with
        no explanation. This fix speaks a passphrase prompt so they can self-recover.
        """
        import os
        from pathlib import Path

        from blind_assistant.second_brain.encryption import VaultKey
        from blind_assistant.second_brain.vault import EncryptedVault

        vault_path = Path(self.config.get("vault_path", os.path.expanduser("~/.blind-assistant/vault")))

        key = VaultKey()

        # Try OS keychain first (no user interaction needed)
        if key.unlock_from_keychain():
            vault = EncryptedVault(vault_path=vault_path, vault_key=key)
            await vault.initialize()
            return vault

        # Keychain has no key — prompt the user for their passphrase
        logger.warning("Vault key not in keychain — prompting user for passphrase")

        if response_callback is None:
            # No interface available to ask the user — log but cannot self-recover
            logger.error(
                "Cannot unlock vault: keychain has no key and no response_callback "
                "available to prompt user for passphrase."
            )
            return None

        # Check if passphrase was collected earlier in this session
        session_passphrase: str | None = getattr(context, "_vault_passphrase", None)

        if session_passphrase is None:
            # Register the response queue BEFORE sending the prompt so that if the
            # user responds instantly (e.g. automated tests), the response is captured.
            # Assert narrows Optional type — _get_vault only called after initialize()
            assert self.confirmation_gate is not None
            self.confirmation_gate.register_session(context.session_id)
            await response_callback(
                "To access your notes, I need your vault passphrase. "
                "Please say or type your passphrase now. "
                "Your passphrase will not be stored — it only unlocks your notes for this session."
            )
            session_passphrase = await self._collect_vault_passphrase(context)

            if session_passphrase is None:
                await response_callback(
                    "I did not receive a passphrase. Your notes remain locked. "
                    "Say 'unlock my notes' any time to try again."
                )
                return None

            # Cache in context so we don't prompt again during the same session.
            # _vault_passphrase is a dynamic attribute not declared in the dataclass —
            # using object.__setattr__ to bypass mypy's attr-defined and assignment checks.
            object.__setattr__(context, "_vault_passphrase", session_passphrase)

        # Derive vault key from passphrase + stored salt
        salt_path = vault_path / ".salt"
        if not salt_path.exists():
            # First time: create vault directory and generate salt
            vault_path.mkdir(parents=True, exist_ok=True)
            from blind_assistant.second_brain.encryption import generate_salt

            salt = generate_salt()
            salt_path.write_bytes(salt)
            logger.info("New vault initialised: generated and stored salt.")
        else:
            salt = salt_path.read_bytes()

        try:
            key.unlock(session_passphrase, salt)
        except Exception as e:
            logger.error(f"Vault key derivation failed: {e}")
            await response_callback(
                "I could not unlock your notes with that passphrase. "
                "Please check your passphrase and say 'unlock my notes' to try again."
            )
            # Clear the cached wrong passphrase so next attempt can re-prompt
            if hasattr(context, "_vault_passphrase"):
                del context._vault_passphrase  # type: ignore[attr-defined]
            return None

        vault = EncryptedVault(vault_path=vault_path, vault_key=key)
        await vault.initialize()

        # Let the user know notes are unlocked, and offer to remember for next session
        await response_callback(
            "Notes unlocked. Say 'remember my passphrase' to store it securely so you don't need to enter it next time."
        )
        return vault

    async def _collect_vault_passphrase(self, context: UserContext) -> str | None:
        """
        Wait for the user to provide their vault passphrase.

        Reuses the confirmation gate's response queue so Telegram messages and
        local voice input are both routed here automatically.
        Timeout is read from config.yaml `voice.prompt_timeout_seconds` (default 120).
        Per ISSUE-006: hardcoded timeout was inaccessible; now configurable for Dorothy
        (elder, needs more time) and Marcus (power user, wants less).
        """
        # Read timeout from config — allows per-user customisation in config.yaml
        timeout_seconds: float = float(self.config.get("voice", {}).get("prompt_timeout_seconds", 120))
        # Assert narrows Optional type — _collect_vault_passphrase only called after initialize()
        assert self.confirmation_gate is not None
        self.confirmation_gate.register_session(context.session_id)
        queue = self.confirmation_gate._response_queues[context.session_id]
        try:
            response = await asyncio.wait_for(queue.get(), timeout=timeout_seconds)
            return response.strip() if response and response.strip() else None
        except TimeoutError:
            logger.info(f"Vault passphrase prompt timed out after {timeout_seconds}s")
            return None

    @property
    def _intent_handlers(self) -> dict:
        """Map of intent type → handler method."""
        return {
            "screen_description": self._handle_screen_description,
            "navigate_app": self._handle_screen_description,  # Starts with screen look
            "add_note": self._handle_add_note,
            "query_note": self._handle_query_note,
            "general_question": self._handle_general_question,
            # Food/grocery ordering: real implementation — browser tool + risk disclosure
            "order_food": self._handle_order_food,
            "order_groceries": self._handle_order_food,  # Same flow, different food query
            # High-stakes intents — stubs until travel/smart home tools built
            "book_travel": self._handle_high_stakes_stub,
            "fill_form": self._handle_high_stakes_stub,
            "smart_home": self._handle_high_stakes_stub,
            "search_web": self._handle_high_stakes_stub,
        }

    def _format_response(self, result: dict, context: UserContext) -> Response:
        """Format a result dict into a Response appropriate for the user's output mode."""
        text = result.get("text", "Done.")

        # For braille mode (Jordan): format in 40-char friendly chunks
        if context.braille_mode:
            text = self._format_for_braille(text)

        # For brief mode (Marcus): trim preamble
        if context.verbosity == "brief":
            text = self._trim_preamble(text)

        return Response(text=text)

    def _format_for_braille(self, text: str) -> str:
        """
        Format text for a 40-cell braille display.
        Break at sentence boundaries; avoid emoji and special chars.
        """
        import re

        # Remove emoji
        emoji_pattern = re.compile(
            "[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff]+",
            flags=re.UNICODE,
        )
        text = emoji_pattern.sub("", text)

        # Break into sentences for navigable chunks
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return "\n".join(sentences)

    def _trim_preamble(self, text: str) -> str:
        """Remove common AI preambles for brief mode."""
        preambles = [
            "Certainly! ",
            "Of course! ",
            "Great question! ",
            "Sure! ",
            "I'd be happy to help with that. ",
            "Absolutely! ",
        ]
        for preamble in preambles:
            if text.startswith(preamble):
                text = text[len(preamble) :]
        return text
