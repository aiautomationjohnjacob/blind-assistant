"""
Shared accessibility assertion helpers for Blind Assistant test suite.

These helpers are used across persona scenario tests (Dorothy, Alex, Jordan, Marcus, Sam)
to verify that spoken and text responses meet accessibility requirements:
- No technical jargon that would confuse newly-blind or elderly users
- No visual-only language that is meaningless to a blind or DeafBlind user
- Braille-friendly formatting (40-char line lengths, no emoji)

Usage:
    from tests.accessibility.helpers import (
        assert_no_jargon,
        assert_no_visual_only_language,
        assert_braille_friendly,
        FORBIDDEN_JARGON,
        VISUAL_ONLY_PHRASES,
    )

Issue #94 requested that these helpers be extracted from test_dorothy_scenario.py
so that food ordering, Second Brain, and other scenario tests can all share them
without duplicating logic.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────
# Jargon word list
#
# These technical terms must NEVER appear in spoken or braille
# responses to blind users (Dorothy, Alex, Jordan, Marcus, Sam).
# They are accessibility barriers: if the user hears "API token"
# they cannot resolve the problem without sighted help.
#
# Extend this list when new jargon is found in real user testing.
# ─────────────────────────────────────────────────────────────

FORBIDDEN_JARGON: list[str] = [
    "api",
    "backend",
    "keychain",
    "subprocess",
    "endpoint",
    "bearer",
    "json",
    "http",
    "daemon",
    "terminal",
    "config",
    "environment variable",
    "webhook",
    "localhost",
    "port",
]

# ─────────────────────────────────────────────────────────────
# Visual-only phrases
#
# These phrases are meaningless to blind and DeafBlind users:
# - "click here" presupposes a mouse and a visible element
# - "you can see" presupposes vision
# - "as shown" / "shown below" presupposes a visual display
# - "in the image" presupposes the user can view the image
#
# Extend when new visual-only language is found in responses.
# ─────────────────────────────────────────────────────────────

VISUAL_ONLY_PHRASES: list[str] = [
    "click here",
    "you can see",
    "as shown",
    "in the image",
    "shown below",
    "look at",
    "as you can see",
    "visible on",
    "on the screen you",
    "shown above",
]


def assert_no_jargon(text: str, persona: str = "user") -> None:
    """Assert that a spoken or text response contains no technical jargon.

    Uses word-boundary matching so that 'port' does not match 'important',
    'http' does not match 'https' in a URL context, etc.

    Fails with a descriptive message naming the jargon word and the persona
    affected, so contributors can fix the right string in src/.
    """
    import re

    text_lower = text.lower()
    for word in FORBIDDEN_JARGON:
        # Use word boundary (\b) to avoid false positives like
        # "port" matching "important", "api" matching "rapid", etc.
        pattern = r"\b" + re.escape(word) + r"\b"
        if re.search(pattern, text_lower):
            raise AssertionError(
                f"{persona} accessibility FAILED: Response contains jargon '{word}' "
                f"which would confuse a newly-blind or elderly user.\n"
                f"Response was: {text!r}\n"
                f"Fix: remove or replace this term in the src/ file that generates this response."
            )


def assert_no_visual_only_language(text: str, persona: str = "user") -> None:
    """Assert that a spoken or text response contains no visual-only language.

    Visual-only phrases (e.g., 'click here', 'you can see') are meaningless
    to blind and DeafBlind users and must never appear in responses.
    """
    text_lower = text.lower()
    for phrase in VISUAL_ONLY_PHRASES:
        assert phrase not in text_lower, (
            f"{persona} accessibility FAILED: Response uses visual-only language '{phrase}' "
            f"which is meaningless to a blind or DeafBlind user.\n"
            f"Response was: {text!r}\n"
            f"Fix: replace with non-visual equivalent in the src/ file generating this response."
        )


def assert_braille_friendly(text: str, max_line_length: int = 40) -> None:
    """Assert that text is formatted for a 40-cell braille display.

    Braille displays show one line at a time. Text that is not broken into
    short lines forces Jordan (DeafBlind) to scroll left-right, which is
    disorienting and slow.

    Checks:
    - No line exceeds max_line_length characters (default: 40)
    - No emoji characters (braille displays cannot render emoji)
    """
    import re

    # Emoji check: emoji characters cannot be rendered on a braille display
    emoji_pattern = re.compile(
        r"[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff"
        r"\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff]+"
    )
    emoji_matches = emoji_pattern.findall(text)
    assert not emoji_matches, (
        f"Jordan (DeafBlind) accessibility FAILED: braille response contains emoji "
        f"{emoji_matches!r} which cannot be rendered on a braille display.\n"
        f"Response was: {text!r}"
    )

    # Line length check: no line should exceed the braille display width
    lines = text.split("\n")
    for i, line in enumerate(lines):
        assert len(line) <= max_line_length, (
            f"Jordan (DeafBlind) accessibility FAILED: braille response line {i + 1} "
            f"is {len(line)} chars, exceeding the {max_line_length}-cell display width.\n"
            f"Line was: {line!r}\n"
            f"Full response: {text!r}"
        )


def assert_financial_disclosure_present(spoken_text: str, persona: str = "user") -> None:
    """Assert that the financial risk disclosure was spoken before a payment action.

    Per SECURITY_MODEL.md and ETHICS_REQUIREMENTS.md: the financial risk
    disclosure is mandatory and must fire before any payment is processed.
    The disclosure must be understandable (no jargon) and must be audible
    before the user can confirm.
    """
    keywords = ["financial", "payment", "risk", "warning", "sharing", "details"]
    text_lower = spoken_text.lower()
    assert any(kw in text_lower for kw in keywords), (
        f"{persona} accessibility FAILED: Financial risk disclosure was not spoken "
        f"before payment action. At least one of {keywords} must appear in the spoken text.\n"
        f"Spoken text was: {spoken_text!r}\n"
        f"Fix: ensure _handle_order_food calls disclosure before confirmation gate."
    )
