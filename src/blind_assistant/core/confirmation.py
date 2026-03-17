"""
Confirmation Gate

All high-stakes actions (financial transactions, installations, communications)
require explicit user confirmation before execution.

Per ETHICS_REQUIREMENTS.md:
- Financial actions require per-transaction confirmation — not session-level
- Risk disclosure spoken before any payment details collected
- Artificial urgency is FORBIDDEN

Per SECURITY_MODEL.md:
- Financial risk disclosure fires every time, without exception
"""

import asyncio
import logging
from typing import Optional

from blind_assistant.security.disclosure import (
    FINANCIAL_RISK_DISCLOSURE,
    FINANCIAL_RISK_DISCLOSURE_BRIEF,
    ACTION_CONFIRMATION_TEMPLATE,
    ORDER_CONFIRMATION_TEMPLATE,
    is_confirmation,
    is_cancellation,
)

logger = logging.getLogger(__name__)

# How long to wait for a user response before timing out (seconds)
DEFAULT_TIMEOUT = 60


class ConfirmationGate:
    """
    Manages the confirmation flow for high-stakes actions.

    This is intentionally not a simple yes/no prompt — it is a full
    conversational flow that ensures the user understands what they're
    confirming before they do it.
    """

    def __init__(self) -> None:
        # Maps session_id → asyncio.Queue for receiving user responses
        self._response_queues: dict[str, asyncio.Queue] = {}

    def register_session(self, session_id: str) -> None:
        """Register a session for confirmation responses."""
        if session_id not in self._response_queues:
            self._response_queues[session_id] = asyncio.Queue()

    def submit_response(self, session_id: str, response: str) -> None:
        """
        Called when the user sends a message during a confirmation wait.
        Routes the response to the waiting confirmation flow.
        """
        if session_id in self._response_queues:
            self._response_queues[session_id].put_nowait(response)

    async def wait_for_confirmation(
        self,
        context,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Wait for the user to confirm or cancel.

        Returns:
            True if confirmed, False if cancelled or timed out
        """
        self.register_session(context.session_id)
        queue = self._response_queues[context.session_id]

        try:
            response = await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.info(f"Confirmation timed out for session {context.session_id}")
            return False

        return is_confirmation(response)

    async def confirm_action(
        self,
        action_description: str,
        context,
        response_callback=None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Request confirmation for a generic action.

        Args:
            action_description: Plain English description of the action
            context: User context
            response_callback: Async callable to send message to user
            timeout: Seconds to wait for response

        Returns:
            True if confirmed, False otherwise
        """
        message = ACTION_CONFIRMATION_TEMPLATE.format(
            action_description=action_description
        )

        if response_callback:
            await response_callback(message)

        return await self.wait_for_confirmation(context, timeout=timeout)

    async def confirm_financial_action(
        self,
        order_summary: str,
        total_amount: str,
        context,
        response_callback=None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Full financial action confirmation flow:
        1. Mandatory risk disclosure
        2. Order confirmation

        This is non-negotiable. Both steps must complete.
        NO artificial urgency. NO "order now before it sells out!".
        """
        if response_callback is None:
            logger.warning(
                "confirm_financial_action called without response_callback — "
                "user will not hear the risk disclosure"
            )
            return False

        # Step 1: Risk disclosure — ALWAYS fires, every time
        disclosure = (
            FINANCIAL_RISK_DISCLOSURE_BRIEF
            if context.verbosity == "brief"
            else FINANCIAL_RISK_DISCLOSURE
        )
        await response_callback(disclosure)
        understood = await self.wait_for_confirmation(context, timeout=timeout)

        if not understood:
            await response_callback("No problem. I won't process any payment.")
            return False

        # Step 2: Specific order confirmation
        order_message = ORDER_CONFIRMATION_TEMPLATE.format(
            order_summary=order_summary,
            total_amount=total_amount,
        )
        await response_callback(order_message)
        return await self.wait_for_confirmation(context, timeout=timeout)

    async def confirm_financial_details_collection(
        self,
        context,
        response_callback=None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Before collecting any financial details (card numbers, bank info):
        speak the risk disclosure and wait for explicit acknowledgment.

        Per SECURITY_MODEL.md §4.1: fires every time, without exception.
        """
        if response_callback is None:
            return False

        disclosure = (
            FINANCIAL_RISK_DISCLOSURE_BRIEF
            if context.verbosity == "brief"
            else FINANCIAL_RISK_DISCLOSURE
        )
        await response_callback(disclosure)
        return await self.wait_for_confirmation(context, timeout=timeout)
