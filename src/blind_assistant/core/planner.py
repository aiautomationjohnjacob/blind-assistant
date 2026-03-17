"""
Intent Planner

Uses Claude API to classify user intent and determine which tools are needed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    """A classified user intent."""

    type: str  # e.g., "screen_description", "order_food", "add_note"
    description: str  # Plain English description
    required_tools: list[str] = field(default_factory=list)
    parameters: dict = field(default_factory=dict)
    is_high_stakes: bool = False  # True if requires confirmation
    confidence: float = 1.0


# Intent types and their tool requirements.
#
# Tool names must match keys in tools/registry.yaml (capabilities + integrations sections).
# Per ARCHITECTURE.md: Claude handles ordering, travel, home control autonomously via the
# browser tool — no service-specific wrappers. So "order_food" requires ["browser"],
# not a DoorDash-specific tool. Payments may also require ["stripe_payments"].
#
# Tools with no registry entry (screen_observer, second_brain, desktop_commander) are
# built-in — they do not trigger the install flow.
INTENT_TOOL_MAP = {
    "screen_description": ["screen_observer"],
    "navigate_app": ["screen_observer", "desktop_control"],
    "fill_form": ["screen_observer", "browser"],
    "order_food": ["browser"],  # Claude navigates the ordering site via browser
    "order_groceries": ["browser"],  # Same: any grocery site navigated via browser
    "book_travel": ["browser"],  # Any travel site navigated via browser
    "add_note": ["second_brain"],
    "query_note": ["second_brain"],
    "smart_home": ["home_assistant"],
    "search_web": ["browser"],
    "general_question": [],
}

HIGH_STAKES_INTENTS = {
    "order_food",
    "order_groceries",
    "book_travel",
    "send_email",
    "delete_files",
    "install_tool",
}

# System prompt for intent classification
CLASSIFICATION_PROMPT = """You are the intent classifier for Blind Assistant, an AI life
companion for blind and visually impaired users. Your job is to classify the user's
message into one of these intent types and determine what tools are needed.

Intent types:
- screen_description: User wants to know what's on their screen
- navigate_app: User wants help navigating an application
- fill_form: User wants to fill out a form
- order_food: User wants to order food delivery
- order_groceries: User wants to order groceries
- book_travel: User wants to research or book travel
- add_note: User wants to add something to their personal notes
- query_note: User wants to recall something from their notes
- smart_home: User wants to control a smart home device
- search_web: User wants to search the web
- general_question: User has a general question (no tools needed)

Respond with JSON only:
{
  "type": "<intent_type>",
  "description": "<plain English description of what the user wants>",
  "required_tools": ["<tool_name>", ...],
  "parameters": {},
  "confidence": 0.0-1.0
}"""


class Planner:
    """
    Classifies user intent using Claude API.
    Determines which tools are needed for the intent.
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        self._client = None

    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            import anthropic

            from blind_assistant.security.credentials import CLAUDE_API_KEY, require_credential

            api_key = require_credential(CLAUDE_API_KEY)
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._client

    async def classify_intent(self, text: str, context) -> Intent:
        """
        Classify the user's message into an intent.

        Args:
            text: User's message
            context: UserContext with conversation history

        Returns:
            Classified Intent
        """
        import json

        try:
            client = self._get_client()
            response = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=256,
                system=CLASSIFICATION_PROMPT,
                messages=[{"role": "user", "content": text}],
            )

            result = json.loads(response.content[0].text)
            intent_type = result.get("type", "general_question")

            return Intent(
                type=intent_type,
                description=result.get("description", text),
                required_tools=result.get("required_tools", INTENT_TOOL_MAP.get(intent_type, [])),
                parameters=result.get("parameters", {}),
                is_high_stakes=intent_type in HIGH_STAKES_INTENTS,
                confidence=result.get("confidence", 1.0),
            )

        except Exception as e:
            logger.error(f"Intent classification failed: {e}", exc_info=True)
            # Fallback: treat as general question
            return Intent(
                type="general_question",
                description=text,
                required_tools=[],
                is_high_stakes=False,
                confidence=0.0,
            )
