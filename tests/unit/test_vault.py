"""
Unit tests for blind_assistant.second_brain.vault and .query

Coverage target: 80%+ (non-security critical but core user-facing feature)

Tests verify:
- Adding a note writes an encrypted file
- Searching returns matching notes
- Locked vault raises RuntimeError
- Category inference (query.py)
- Voice query formatting (query.py)
- Braille formatting (query.py)
"""

from __future__ import annotations

import os
import pytest
from pathlib import Path

from blind_assistant.second_brain.encryption import VaultKey, generate_salt
from blind_assistant.second_brain.vault import EncryptedVault
from blind_assistant.second_brain.query import (
    VaultQuery,
    _infer_category,
    _trim_for_speech,
    _format_date_label,
    _format_for_braille,
    _extract_topic_hint,
    BRAILLE_LINE_WIDTH,
)

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────
# EncryptedVault — lifecycle
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def vault_key(sample_passphrase):
    vk = VaultKey()
    vk.unlock(sample_passphrase, generate_salt())
    return vk


@pytest.fixture
async def vault(temp_vault_dir, vault_key):
    v = EncryptedVault(vault_path=temp_vault_dir, vault_key=vault_key)
    await v.initialize()
    return v


class TestEncryptedVaultInit:
    async def test_creates_vault_directory(self, temp_vault_dir, vault_key):
        path = temp_vault_dir / "my_vault"
        v = EncryptedVault(vault_path=path, vault_key=vault_key)
        await v.initialize()
        assert path.exists()

    async def test_creates_subdirectories(self, temp_vault_dir, vault_key):
        v = EncryptedVault(vault_path=temp_vault_dir, vault_key=vault_key)
        await v.initialize()
        assert (temp_vault_dir / "health").exists()
        assert (temp_vault_dir / "finance").exists()
        assert (temp_vault_dir / "general").exists()


class TestEncryptedVaultAddNote:
    async def test_add_note_returns_filename(self, vault):
        filename = await vault.add_note("Test note content")
        assert filename.endswith(".md.enc")
        assert len(filename) > 10

    async def test_add_note_creates_encrypted_file(self, vault, temp_vault_dir):
        filename = await vault.add_note("Doctor appointment note", category="health")
        # Find the file in the vault
        enc_files = list(temp_vault_dir.rglob("*.md.enc"))
        assert len(enc_files) == 1

    async def test_encrypted_file_does_not_contain_plaintext(self, vault, temp_vault_dir):
        secret_content = "my secret appointment details"
        await vault.add_note(secret_content, category="health")
        enc_files = list(temp_vault_dir.rglob("*.md.enc"))
        raw_bytes = enc_files[0].read_bytes()
        assert secret_content.encode() not in raw_bytes

    async def test_add_note_uses_category_subdirectory(self, vault, temp_vault_dir):
        await vault.add_note("Financial note", category="finance")
        enc_files = list((temp_vault_dir / "finance").rglob("*.md.enc"))
        assert len(enc_files) == 1

    async def test_add_note_uses_general_for_unknown_category(self, vault, temp_vault_dir):
        await vault.add_note("Random note", category="nonexistent_category")
        enc_files = list((temp_vault_dir / "general").rglob("*.md.enc"))
        assert len(enc_files) == 1

    async def test_add_note_raises_when_locked(self, temp_vault_dir):
        locked_key = VaultKey()  # not unlocked
        v = EncryptedVault(vault_path=temp_vault_dir, vault_key=locked_key)
        # Initialize without encryption (should fail at add_note)
        with pytest.raises((RuntimeError, Exception)):
            await v.add_note("this should fail")

    async def test_add_multiple_notes(self, vault):
        for i in range(5):
            await vault.add_note(f"Note number {i}")
        results = await vault.search("note", limit=10)
        assert len(results) == 5


class TestEncryptedVaultSearch:
    async def test_search_returns_matching_note(self, vault, sample_note_content):
        await vault.add_note(sample_note_content, category="health")
        results = await vault.search("doctor appointment")
        assert len(results) >= 1

    async def test_search_returns_empty_for_no_match(self, vault):
        await vault.add_note("Note about cooking recipes")
        results = await vault.search("banking investment")
        assert results == []

    async def test_search_returns_dict_with_required_keys(self, vault, sample_note_content):
        await vault.add_note(sample_note_content)
        results = await vault.search("doctor")
        assert len(results) > 0
        note = results[0]
        assert "title" in note
        assert "content" in note
        assert "date" in note
        assert "category" in note

    async def test_search_respects_limit(self, vault):
        for i in range(10):
            await vault.add_note(f"Meeting with person number {i}")
        results = await vault.search("meeting person", limit=3)
        assert len(results) <= 3

    async def test_search_raises_when_locked(self, temp_vault_dir):
        locked_key = VaultKey()
        v = EncryptedVault(vault_path=temp_vault_dir, vault_key=locked_key)
        with pytest.raises(RuntimeError, match="locked"):
            await v.search("anything")

    async def test_search_content_is_decrypted(self, vault, sample_note_content):
        await vault.add_note(sample_note_content, category="health")
        results = await vault.search("doctor appointment")
        assert len(results) > 0
        # The returned content should be readable plaintext, not ciphertext
        content = results[0]["content"]
        assert isinstance(content, str)
        # The original content keywords should appear in the note body
        assert "doctor" in content.lower() or "Dr" in content


# ─────────────────────────────────────────────────────────────
# VaultQuery — category inference
# ─────────────────────────────────────────────────────────────

class TestInferCategory:
    @pytest.mark.parametrize("content,expected", [
        ("Doctor appointment at 2pm", "health"),
        ("prescription renewal needed", "health"),
        ("blood pressure reading today", "health"),
        ("pay the rent invoice", "finance"),
        ("my bank account balance", "finance"),
        ("credit card bill is due", "finance"),
        ("remember to call the plumber", "tasks"),
        ("need to follow up with John", "tasks"),
        ("met with Sarah today", "people"),
        ("happy birthday reminder", "general"),  # 'birthday' alone → general
        ("today was a good day", "general"),
    ])
    def test_category_inference(self, content, expected):
        result = _infer_category(content)
        assert result == expected, f"'{content}' → got '{result}', expected '{expected}'"

    def test_returns_general_for_empty(self):
        assert _infer_category("") == "general"

    def test_returns_string(self):
        assert isinstance(_infer_category("any text"), str)


# ─────────────────────────────────────────────────────────────
# VaultQuery — speech formatting
# ─────────────────────────────────────────────────────────────

class TestTrimForSpeech:
    def test_short_text_unchanged(self):
        text = "Short text."
        result = _trim_for_speech(text, 300)
        assert result == text

    def test_long_text_trimmed_to_max(self):
        text = "Word " * 200  # 1000 chars
        result = _trim_for_speech(text, 100)
        assert len(result) <= 110  # allow for ellipsis

    def test_trim_at_sentence_boundary(self):
        text = "First sentence. Second sentence. Third sentence."
        result = _trim_for_speech(text, 35)
        # Should break at sentence boundary, not mid-word
        assert result.endswith(".") or result.endswith("...")

    def test_strips_markdown(self):
        text = "# Heading\n**Bold text** and _italic_"
        result = _trim_for_speech(text, 300)
        assert "#" not in result
        assert "**" not in result
        assert "_" not in result

    def test_empty_string(self):
        assert _trim_for_speech("", 300) == ""


class TestFormatDateLabel:
    def test_unknown_date(self):
        label = _format_date_label("")
        assert "unknown" in label.lower() or label == "Date unknown"

    def test_invalid_date_returns_original(self):
        label = _format_date_label("not-a-date")
        assert label == "not-a-date"

    def test_today(self):
        from datetime import datetime
        today = datetime.now().isoformat()
        label = _format_date_label(today)
        assert "today" in label.lower()

    def test_yesterday(self):
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        label = _format_date_label(yesterday)
        assert "yesterday" in label.lower()

    def test_days_ago(self):
        from datetime import datetime, timedelta
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        label = _format_date_label(three_days_ago)
        assert "3" in label or "three" in label.lower() or "days" in label.lower()


class TestFormatForBraille:
    def test_lines_fit_in_40_chars(self):
        text = "This is a longer sentence that needs to be broken down for a braille display properly."
        result = _format_for_braille(text)
        for line in result.split("\n"):
            assert len(line) <= BRAILLE_LINE_WIDTH, (
                f"Line too long for braille ({len(line)} chars): '{line}'"
            )

    def test_strips_markdown(self):
        text = "# Header\n**Bold** and _italic_"
        result = _format_for_braille(text)
        assert "#" not in result
        assert "**" not in result

    def test_empty_string(self):
        assert _format_for_braille("") == ""


class TestExtractTopicHint:
    def test_returns_string(self):
        assert isinstance(_extract_topic_hint("some content about doctor"), str)

    def test_returns_max_three_words(self):
        hint = _extract_topic_hint("meeting about insurance policy renewal tomorrow")
        word_count = len(hint.split())
        assert word_count <= 3

    def test_returns_general_for_empty(self):
        hint = _extract_topic_hint("")
        assert hint == "this topic"

    def test_returns_lowercase(self):
        hint = _extract_topic_hint("Doctor Appointment Tomorrow")
        assert hint == hint.lower()


# ─────────────────────────────────────────────────────────────
# VaultQuery — answer_query and add_note_from_voice
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_user_context():
    from unittest.mock import MagicMock
    ctx = MagicMock()
    ctx.braille_mode = False
    ctx.verbosity = "standard"
    return ctx


@pytest.fixture
def mock_braille_context():
    from unittest.mock import MagicMock
    ctx = MagicMock()
    ctx.braille_mode = True
    ctx.verbosity = "standard"
    return ctx


class TestVaultQueryAnswerQuery:
    async def test_returns_not_found_message_when_empty(self, vault, mock_user_context):
        q = VaultQuery(vault)
        result = await q.answer_query("insurance claim", mock_user_context)
        assert "didn't find" in result.lower() or "not find" in result.lower()

    async def test_returns_locked_message_when_vault_locked(self, temp_vault_dir, mock_user_context):
        locked_key = VaultKey()
        v = EncryptedVault(vault_path=temp_vault_dir, vault_key=locked_key)
        q = VaultQuery(v)
        result = await q.answer_query("anything", mock_user_context)
        assert "locked" in result.lower() or "passphrase" in result.lower()

    async def test_returns_note_when_found(self, vault, sample_note_content, mock_user_context):
        await vault.add_note(sample_note_content, category="health")
        q = VaultQuery(vault)
        result = await q.answer_query("doctor appointment", mock_user_context)
        assert isinstance(result, str)
        assert len(result) > 10

    async def test_multiple_results_mentions_count(self, vault, mock_user_context):
        for i in range(3):
            await vault.add_note(f"Meeting with doctor number {i}")
        q = VaultQuery(vault)
        result = await q.answer_query("meeting doctor", mock_user_context)
        # Should mention there are multiple results
        assert any(char.isdigit() for char in result) or "note" in result.lower()

    async def test_braille_mode_formats_for_braille(
        self, vault, sample_note_content, mock_braille_context
    ):
        await vault.add_note(sample_note_content)
        q = VaultQuery(vault)
        result = await q.answer_query("doctor", mock_braille_context)
        # Braille mode: each line should fit in BRAILLE_LINE_WIDTH
        for line in result.split("\n"):
            assert len(line) <= BRAILLE_LINE_WIDTH


class TestVaultQueryAddNote:
    async def test_add_note_returns_confirmation(self, vault, mock_user_context):
        q = VaultQuery(vault)
        result = await q.add_note_from_voice("Doctor called about prescription", mock_user_context)
        assert isinstance(result, str)
        assert len(result) > 5

    async def test_add_note_confirmation_says_saved(self, vault, mock_user_context):
        q = VaultQuery(vault)
        result = await q.add_note_from_voice("Insurance renewal deadline is March 31", mock_user_context)
        assert "saved" in result.lower() or "got it" in result.lower() or "noted" in result.lower()

    async def test_add_note_returns_error_when_locked(self, temp_vault_dir, mock_user_context):
        locked_key = VaultKey()
        v = EncryptedVault(vault_path=temp_vault_dir, vault_key=locked_key)
        q = VaultQuery(v)
        result = await q.add_note_from_voice("some note", mock_user_context)
        assert "locked" in result.lower() or "unlock" in result.lower()
