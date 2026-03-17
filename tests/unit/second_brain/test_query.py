"""
Unit tests for VaultQuery and helper utilities — second_brain/query.py

Tests cover:
- answer_query: locked vault returns unlock prompt
- answer_query: braille mode formats locked message for braille
- answer_query: no results returns friendly "not found" message
- answer_query: single result formatted for voice
- answer_query: multiple results formatted with count + top note
- answer_query: braille mode formats multiple results as numbered list
- add_note_from_voice: locked vault returns error
- add_note_from_voice: successful save returns confirmation with topic hint
- add_note_from_voice: vault exception returns user-friendly error
- _infer_category: health / finance / tasks / people / general keywords
- _category_spoken_label: all categories return natural spoken labels
- _extract_topic_hint: extracts significant words from content
- _trim_for_speech: truncates at sentence boundary; hard-truncates if no sentence fits
- _format_date_label: today / yesterday / days ago / weeks / month / year
- _format_for_braille: wraps at 40 chars; removes markdown; handles paragraphs
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from blind_assistant.second_brain.query import (
    MAX_SPOKEN_EXCERPT_LENGTH,
    VaultQuery,
    _category_spoken_label,
    _extract_topic_hint,
    _format_date_label,
    _format_for_braille,
    _infer_category,
    _trim_for_speech,
)

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _make_vault(is_unlocked: bool = True, search_results: list[dict] | None = None) -> MagicMock:
    vault = MagicMock()
    vault.key = MagicMock()
    vault.key.is_unlocked = is_unlocked
    vault.search = AsyncMock(return_value=search_results or [])
    vault.add_note = AsyncMock()
    return vault


def _make_context(braille_mode: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.braille_mode = braille_mode
    return ctx


def _make_note(title: str = "Test Note", content: str = "Some content.", date: str = "2026-03-10") -> dict:
    return {"title": title, "content": content, "date": date}


# ─────────────────────────────────────────────────────────────
# answer_query — locked vault
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_answer_query_locked_vault_returns_unlock_prompt():
    vq = VaultQuery(_make_vault(is_unlocked=False))
    result = await vq.answer_query("what is my doctor's name", _make_context())
    assert "locked" in result.lower()
    assert "passphrase" in result.lower()


@pytest.mark.asyncio
async def test_answer_query_locked_vault_braille_mode_formats_for_braille():
    vq = VaultQuery(_make_vault(is_unlocked=False))
    result = await vq.answer_query("notes", _make_context(braille_mode=True))
    # braille lines must be ≤ 40 chars
    for line in result.split("\n"):
        assert len(line) <= 40, f"Line too long for braille: '{line}'"


# ─────────────────────────────────────────────────────────────
# answer_query — no results
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_answer_query_no_results_returns_not_found_message():
    vq = VaultQuery(_make_vault(is_unlocked=True, search_results=[]))
    result = await vq.answer_query("unicorn recipes", _make_context())
    assert "didn't find" in result.lower() or "not find" in result.lower()


@pytest.mark.asyncio
async def test_answer_query_no_results_includes_query_in_response():
    vq = VaultQuery(_make_vault(is_unlocked=True, search_results=[]))
    result = await vq.answer_query("flight schedule", _make_context())
    assert "flight schedule" in result


@pytest.mark.asyncio
async def test_answer_query_no_results_braille_mode():
    vq = VaultQuery(_make_vault(is_unlocked=True, search_results=[]))
    result = await vq.answer_query("nothing", _make_context(braille_mode=True))
    for line in result.split("\n"):
        assert len(line) <= 40


# ─────────────────────────────────────────────────────────────
# answer_query — single result
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_answer_query_single_result_contains_title():
    note = _make_note(title="Rental Insurance Claim", content="Filed the claim on Tuesday.")
    vq = VaultQuery(_make_vault(is_unlocked=True, search_results=[note]))
    result = await vq.answer_query("insurance", _make_context())
    assert "Rental Insurance Claim" in result


@pytest.mark.asyncio
async def test_answer_query_single_result_contains_content_excerpt():
    note = _make_note(content="Filed the claim on Tuesday.")
    vq = VaultQuery(_make_vault(is_unlocked=True, search_results=[note]))
    result = await vq.answer_query("insurance", _make_context())
    assert "Filed the claim on Tuesday" in result


@pytest.mark.asyncio
async def test_answer_query_single_result_braille_mode_lines_short():
    note = _make_note(title="Long title about something important and relevant today")
    vq = VaultQuery(_make_vault(is_unlocked=True, search_results=[note]))
    result = await vq.answer_query("something", _make_context(braille_mode=True))
    for line in result.split("\n"):
        assert len(line) <= 40


# ─────────────────────────────────────────────────────────────
# answer_query — multiple results
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_answer_query_multiple_results_mentions_count():
    notes = [_make_note(title=f"Note {i}") for i in range(3)]
    vq = VaultQuery(_make_vault(is_unlocked=True, search_results=notes))
    result = await vq.answer_query("notes", _make_context())
    assert "3" in result


@pytest.mark.asyncio
async def test_answer_query_multiple_results_mentions_other_notes():
    notes = [_make_note(title=f"Note {i}") for i in range(3)]
    vq = VaultQuery(_make_vault(is_unlocked=True, search_results=notes))
    result = await vq.answer_query("notes", _make_context())
    assert "other" in result.lower() or "more" in result.lower() or "also" in result.lower()


@pytest.mark.asyncio
async def test_answer_query_multiple_results_braille_shows_numbered_list():
    notes = [_make_note(title=f"Note {i}") for i in range(2)]
    vq = VaultQuery(_make_vault(is_unlocked=True, search_results=notes))
    result = await vq.answer_query("notes", _make_context(braille_mode=True))
    assert "1." in result
    assert "2." in result


# ─────────────────────────────────────────────────────────────
# add_note_from_voice
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_note_from_voice_locked_vault_returns_error():
    vq = VaultQuery(_make_vault(is_unlocked=False))
    result = await vq.add_note_from_voice("my note content", _make_context())
    assert "locked" in result.lower()


@pytest.mark.asyncio
async def test_add_note_from_voice_returns_confirmation_with_category():
    vault = _make_vault(is_unlocked=True)
    vq = VaultQuery(vault)
    result = await vq.add_note_from_voice("Doctor appointment on Friday", _make_context())
    # Should mention the category (health notes)
    assert "health" in result.lower() or "saved" in result.lower() or "got it" in result.lower()
    vault.add_note.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_note_from_voice_passes_correct_category_to_vault():
    vault = _make_vault(is_unlocked=True)
    vq = VaultQuery(vault)
    await vq.add_note_from_voice("Need to call the bank about my mortgage", _make_context())
    call_kwargs = vault.add_note.call_args.kwargs
    assert call_kwargs["category"] == "finance"


@pytest.mark.asyncio
async def test_add_note_from_voice_handles_vault_exception():
    vault = _make_vault(is_unlocked=True)
    vault.add_note = AsyncMock(side_effect=OSError("disk full"))
    vq = VaultQuery(vault)
    result = await vq.add_note_from_voice("some note", _make_context())
    assert "trouble" in result.lower() or "failed" in result.lower() or "try again" in result.lower()


# ─────────────────────────────────────────────────────────────
# _infer_category
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "content,expected",
    [
        ("saw my doctor about the diagnosis", "health"),
        ("paid the mortgage and credit card", "finance"),
        ("need to remember to call back tomorrow", "tasks"),
        ("called my friend about the birthday party", "people"),
        ("just a random thought I wanted to save", "general"),
        ("insurance claim with the bank", "health"),  # health keyword wins first
        ("Doctor's pharmacy prescription", "health"),
    ],
)
def test_infer_category_keywords(content: str, expected: str):
    assert _infer_category(content) == expected


# ─────────────────────────────────────────────────────────────
# _category_spoken_label
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "category,expected_label",
    [
        ("health", "health"),
        ("finance", "financial"),
        ("people", "contacts and people"),
        ("tasks", "to-do"),
        ("daily", "daily"),
        ("general", "general"),
        ("unknown_category", "general"),  # fallback
    ],
)
def test_category_spoken_label_all_categories(category: str, expected_label: str):
    assert _category_spoken_label(category) == expected_label


# ─────────────────────────────────────────────────────────────
# _extract_topic_hint
# ─────────────────────────────────────────────────────────────


def test_extract_topic_hint_returns_significant_words():
    hint = _extract_topic_hint("My doctor said I need prescription medication")
    # Significant words (4+ chars, not stop words) should be present
    assert len(hint) > 0
    assert hint != "this topic"


def test_extract_topic_hint_falls_back_when_no_significant_words():
    # All short or stop words
    hint = _extract_topic_hint("hi no")
    assert hint == "this topic"


def test_extract_topic_hint_returns_max_three_words():
    hint = _extract_topic_hint("appointment prescription medication therapy specialist treatment")
    word_count = len(hint.split())
    assert word_count <= 3


def test_extract_topic_hint_result_is_lowercase():
    hint = _extract_topic_hint("Doctor Appointment Thursday afternoon")
    assert hint == hint.lower()


# ─────────────────────────────────────────────────────────────
# _trim_for_speech
# ─────────────────────────────────────────────────────────────


def test_trim_for_speech_short_text_returned_unchanged():
    text = "Short note."
    assert _trim_for_speech(text, 300) == "Short note."


def test_trim_for_speech_long_text_truncated_to_max():
    text = "This is a sentence. " * 30  # ~600 chars
    result = _trim_for_speech(text, MAX_SPOKEN_EXCERPT_LENGTH)
    assert len(result) <= MAX_SPOKEN_EXCERPT_LENGTH + 5  # small margin for trailing word


def test_trim_for_speech_breaks_at_sentence_boundary():
    text = "First sentence. Second sentence that is much longer and takes it over the limit please."
    result = _trim_for_speech(text, 20)
    # Should end cleanly (not mid-word with ...)
    assert result.endswith((".", "...")) or len(result) <= 20


def test_trim_for_speech_removes_markdown_hashes():
    text = "# Title\nSome content here."
    result = _trim_for_speech(text, 300)
    assert "#" not in result


def test_trim_for_speech_removes_markdown_bold():
    text = "**Bold text** and *italic*."
    result = _trim_for_speech(text, 300)
    assert "*" not in result


# ─────────────────────────────────────────────────────────────
# _format_date_label
# ─────────────────────────────────────────────────────────────


def test_format_date_label_today():
    today = datetime.now().isoformat()
    result = _format_date_label(today)
    assert result == "Earlier today"


def test_format_date_label_yesterday():
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    result = _format_date_label(yesterday)
    assert result == "Yesterday"


def test_format_date_label_days_ago():
    three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
    result = _format_date_label(three_days_ago)
    assert "3 days ago" in result


def test_format_date_label_weeks_ago():
    two_weeks_ago = (datetime.now() - timedelta(days=14)).isoformat()
    result = _format_date_label(two_weeks_ago)
    assert "week" in result.lower()


def test_format_date_label_empty_string_returns_unknown():
    result = _format_date_label("")
    assert result == "Date unknown"


def test_format_date_label_none_returns_unknown():
    result = _format_date_label(None)  # type: ignore[arg-type]
    assert result == "Date unknown"


def test_format_date_label_invalid_iso_returns_original():
    result = _format_date_label("not-a-date")
    assert result == "not-a-date"


# ─────────────────────────────────────────────────────────────
# _format_for_braille
# ─────────────────────────────────────────────────────────────


def test_format_for_braille_all_lines_within_40_chars():
    text = "This is a longer piece of text that should be wrapped correctly at forty characters."
    result = _format_for_braille(text)
    for line in result.split("\n"):
        assert len(line) <= 40, f"Braille line too long: '{line}'"


def test_format_for_braille_removes_markdown_formatting():
    text = "# Heading\n**Bold** and *italic* content."
    result = _format_for_braille(text)
    assert "#" not in result
    assert "*" not in result


def test_format_for_braille_skips_empty_lines():
    text = "First paragraph.\n\nSecond paragraph."
    result = _format_for_braille(text)
    # Empty lines are consumed, result is non-empty
    assert "First" in result
    assert "Second" in result


def test_format_for_braille_single_long_word_is_preserved():
    """A single word longer than 40 chars should still appear (not silently dropped)."""
    long_word = "supercalifragilisticexpialidocious-longword"
    result = _format_for_braille(long_word)
    assert long_word in result
