"""
Risk Disclosure Flows

Spoken risk disclosures for financial actions.
These are non-negotiable per SECURITY_MODEL.md and ETHICS_REQUIREMENTS.md.

The disclosure fires EVERY time financial details are requested — not just the first time.
A user may forget prior warnings. Repetition is safer than assumption.
"""

# The canonical financial risk disclosure text.
# Must be spoken aloud before any payment details are accepted.
# Must be available as text for braille display users.
FINANCIAL_RISK_DISCLOSURE = """
Before you share payment details, I need to tell you something important.

Providing financial information to any app — including this one — carries some risk.
We protect your data with encryption and never store card numbers.
But please only share payment information you're comfortable sharing with a digital assistant.

You can remove your payment information at any time by saying "delete my payment information."

Do you want to continue?
"""

# Short version for verbose-off users (Marcus)
FINANCIAL_RISK_DISCLOSURE_BRIEF = (
    "Before sharing payment details: any app carries some risk. "
    "We encrypt your data and never store card numbers. "
    "Remove it anytime. Continue?"
)

# Screen protection notice for financial pages
FINANCIAL_SCREEN_PROTECTION_NOTICE = (
    "I can see a financial page. I'm protecting this screen — I won't send screenshots of it to any external service."
)

# Order confirmation template
ORDER_CONFIRMATION_TEMPLATE = (
    "I'm about to place this order: {order_summary} for {total_amount}. "
    "Say confirm to place the order, or cancel to stop."
)

# Installation consent template
INSTALL_CONSENT_TEMPLATE = (
    "To {task_description}, I need to install {package_name} — {package_description}. "
    "This is from our approved list of tools. "
    "Say yes to install it, or no to cancel."
)

# Action confirmation template
ACTION_CONFIRMATION_TEMPLATE = "I'm about to {action_description}. Say confirm to proceed, or cancel to stop."

# Telegram non-E2E notice (shown at setup)
TELEGRAM_SECURITY_NOTICE = """
One thing to know about using me through Telegram:
Telegram messages to bots are encrypted in transit, but Telegram can read them.
This is fine for most tasks. But please don't send passwords or full credit card
numbers as Telegram messages. I'll always ask for sensitive information through
a secure channel instead.
"""

# Confirmation keywords (case-insensitive)
CONFIRMATION_KEYWORDS = {
    "yes",
    "confirm",
    "ok",
    "okay",
    "do it",
    "go ahead",
    "sure",
    "proceed",
    "continue",
    "i understand",
    "yep",
    "yeah",
}

CANCELLATION_KEYWORDS = {
    "no",
    "cancel",
    "stop",
    "never mind",
    "nevermind",
    "abort",
    "don't",
    "dont",
    "skip",
    "nope",
    "nah",
}


def is_confirmation(text: str) -> bool:
    """Check if user response is a confirmation."""
    return text.lower().strip() in CONFIRMATION_KEYWORDS


def is_cancellation(text: str) -> bool:
    """Check if user response is a cancellation."""
    normalized = text.lower().strip()
    return any(keyword in normalized for keyword in CANCELLATION_KEYWORDS)
