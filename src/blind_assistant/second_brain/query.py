"""
Second Brain Query Interface

Voice-friendly query layer over the encrypted vault.
Converts natural language queries into vault searches and formats
results for speech or braille display.

Per USER_STORIES.md:
- Alex: "What did I note about the renter's insurance claim last week?"
  → Should find note by topic + recency, read excerpt aloud
- Dorothy: "Remind me what my doctor said last Tuesday"
  → Should find by date + keyword, speak slowly and clearly
- Jordan (braille): Results formatted in short, navigable chunks
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Maximum characters in a spoken excerpt (to avoid reading walls of text)
MAX_SPOKEN_EXCERPT_LENGTH = 300

# Maximum characters per braille line chunk
BRAILLE_LINE_WIDTH = 40


class VaultQuery:
    """
    High-level query interface for the Second Brain vault.

    Handles the full voice query flow:
    1. Parse natural language query
    2. Search the vault
    3. Format results for voice or braille
    4. Handle "no results" gracefully
    """

    def __init__(self, vault) -> None:
        self.vault = vault

    async def answer_query(
        self,
        query: str,
        context,
    ) -> str:
        """
        Answer a natural language query against the vault.

        Args:
            query: Natural language query (e.g., "what did I say about insurance?")
            context: UserContext for output mode preferences

        Returns:
            A natural language response (for speech or braille)
        """
        if not self.vault.key.is_unlocked:
            locked_msg = (
                "Your notes vault is locked. "
                "I need your vault passphrase to access your notes. "
                "What is your vault passphrase?"
            )
            if context.braille_mode:
                return _format_for_braille(locked_msg)
            return locked_msg

        results = await self.vault.search(query, limit=3)

        if not results:
            no_results_msg = (
                f"I searched your notes for '{query}' but didn't find anything. "
                "Would you like to add a note about this?"
            )
            if context.braille_mode:
                return _format_for_braille(no_results_msg)
            return no_results_msg

        # Format results based on count
        if len(results) == 1:
            return self._format_single_result(results[0], context)
        return self._format_multiple_results(results, context)

    async def add_note_from_voice(
        self,
        content: str,
        context,
    ) -> str:
        """
        Add a note from voice input and confirm back to the user.

        Intelligently categorizes the note based on content.

        Args:
            content: The note content as transcribed from voice
            context: UserContext

        Returns:
            Confirmation message to speak to the user
        """
        if not self.vault.key.is_unlocked:
            return (
                "Your notes vault is locked. "
                "Please unlock your vault first."
            )

        # Infer category from content
        category = _infer_category(content)

        try:
            filename = await self.vault.add_note(
                content=content,
                category=category,
            )

            category_label = _category_spoken_label(category)
            return (
                f"Got it. I've saved that to your {category_label} notes. "
                f"You can find it by asking me: 'What did I note about "
                f"{_extract_topic_hint(content)}'."
            )

        except Exception as e:
            logger.error(f"Failed to add note: {e}", exc_info=True)
            return (
                "I had trouble saving that note. "
                "Please try again."
            )

    def _format_single_result(self, note: dict, context) -> str:
        """Format a single vault search result for speech."""
        title = note.get("title", "Untitled note")
        content = note.get("content", "")
        date_str = note.get("date", "")

        # Parse and format date
        date_label = _format_date_label(date_str)

        # Trim content for speech
        excerpt = _trim_for_speech(content, MAX_SPOKEN_EXCERPT_LENGTH)

        if context.braille_mode:
            return _format_for_braille(
                f"Note: {title}\n{date_label}\n{excerpt}"
            )

        return f"Here's what I found. {date_label}: {title}. {excerpt}"

    def _format_multiple_results(
        self, results: list[dict], context
    ) -> str:
        """Format multiple vault search results for speech."""
        count = len(results)
        intro = f"I found {count} notes that might be relevant."

        # For voice: read the most recent/relevant one and offer to continue
        top = results[0]
        title = top.get("title", "Untitled")
        date_str = top.get("date", "")
        date_label = _format_date_label(date_str)
        excerpt = _trim_for_speech(top.get("content", ""), MAX_SPOKEN_EXCERPT_LENGTH)

        if context.braille_mode:
            parts = [f"Found {count} notes:"]
            for i, note in enumerate(results, 1):
                parts.append(
                    f"{i}. {note.get('title','Untitled')} — "
                    f"{_format_date_label(note.get('date', ''))}"
                )
            return _format_for_braille("\n".join(parts))

        other_count = count - 1
        suffix = (
            f"There {'is' if other_count == 1 else 'are'} also "
            f"{other_count} other {'note' if other_count == 1 else 'notes'}. "
            "Say 'read the next one' to hear more."
            if other_count > 0 else ""
        )

        return (
            f"{intro} The most relevant: {date_label}, titled {title}. "
            f"{excerpt} {suffix}".strip()
        )


# ──────────────────────────────────────────────
# Utility functions
# ──────────────────────────────────────────────

def _infer_category(content: str) -> str:
    """
    Infer a note category from its content.
    Returns one of: health, finance, people, tasks, daily, general
    """
    content_lower = content.lower()

    health_keywords = {
        "doctor", "appointment", "medication", "prescription", "hospital",
        "health", "blood pressure", "diagnosis", "symptoms", "insurance",
        "pharmacy", "specialist", "therapy", "treatment",
    }
    finance_keywords = {
        "bank", "payment", "invoice", "bill", "credit", "debit", "loan",
        "mortgage", "rent", "tax", "budget", "insurance", "claim", "money",
        "dollars", "price", "cost", "expense", "account",
    }
    people_keywords = {
        "called", "texted", "emailed", "met with", "birthday", "address",
        "phone number", "contact",
    }
    tasks_keywords = {
        "todo", "to-do", "to do", "need to", "must", "remember to",
        "don't forget", "follow up", "call back", "schedule",
    }

    if any(kw in content_lower for kw in health_keywords):
        return "health"
    if any(kw in content_lower for kw in finance_keywords):
        return "finance"
    if any(kw in content_lower for kw in tasks_keywords):
        return "tasks"
    if any(kw in content_lower for kw in people_keywords):
        return "people"

    return "general"


def _category_spoken_label(category: str) -> str:
    """Return a natural spoken label for a category."""
    labels = {
        "health": "health",
        "finance": "financial",
        "people": "contacts and people",
        "tasks": "to-do",
        "daily": "daily",
        "general": "general",
    }
    return labels.get(category, "general")


def _extract_topic_hint(content: str) -> str:
    """Extract a 2-3 word topic hint from note content for the confirmation message."""
    # Use the first few significant words
    import re
    words = re.findall(r"\b[a-zA-Z]{4,}\b", content)
    stop_words = {"that", "this", "with", "from", "have", "will", "said"}
    significant = [w for w in words if w.lower() not in stop_words]
    if significant:
        return " ".join(significant[:3]).lower()
    return "this topic"


def _trim_for_speech(text: str, max_length: int) -> str:
    """
    Trim text to a comfortable spoken length, breaking at sentence boundaries.
    """
    import re

    # Remove markdown formatting
    text = re.sub(r"[#*_`]", "", text)
    text = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL)
    text = text.strip()

    if len(text) <= max_length:
        return text

    # Try to break at a sentence boundary
    sentences = re.split(r"(?<=[.!?])\s+", text)
    result = ""
    for sentence in sentences:
        if len(result) + len(sentence) + 1 <= max_length:
            result += (" " if result else "") + sentence
        else:
            break

    if not result:
        # No sentence fit — just truncate at a word boundary
        result = text[:max_length].rsplit(" ", 1)[0] + "..."

    return result


def _format_date_label(date_str: str) -> str:
    """Convert an ISO date string to a natural spoken label."""
    if not date_str:
        return "Date unknown"

    try:
        dt = datetime.fromisoformat(date_str)
        now = datetime.now()
        delta = now - dt

        if delta.days == 0:
            return "Earlier today"
        if delta.days == 1:
            return "Yesterday"
        if delta.days < 7:
            return f"{delta.days} days ago"
        if delta.days < 30:
            weeks = delta.days // 7
            return f"About {weeks} week{'s' if weeks > 1 else ''} ago"
        if delta.days < 365:
            return dt.strftime("%-d %B")  # e.g., "14 March"
        return dt.strftime("%-d %B %Y")

    except (ValueError, TypeError):
        return date_str


def _format_for_braille(text: str) -> str:
    """
    Format text for a 40-cell braille display.
    Breaks at word boundaries, respects sentence structure.
    """
    import re

    # Remove markdown
    text = re.sub(r"[#*_`]", "", text)
    lines = []

    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # Break into 40-char lines at word boundaries
        words = paragraph.split()
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= BRAILLE_LINE_WIDTH:
                current_line += (" " if current_line else "") + word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

    return "\n".join(lines)
