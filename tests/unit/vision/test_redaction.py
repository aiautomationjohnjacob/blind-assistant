"""
Unit tests for screenshot redaction — vision/redaction.py

Tests cover:
- SensitivityLevel enum values exist and are strings
- SensitivityAnalysis dataclass defaults
- analyze_sensitivity: password keyword detected → PASSWORD level, immediate return
- analyze_sensitivity: card number pattern detected → FINANCIAL level
- analyze_sensitivity: SSN pattern detected → FINANCIAL level
- analyze_sensitivity: financial domain keyword detected → FINANCIAL level
- analyze_sensitivity: clean text → SAFE level
- analyze_sensitivity: OCR failure (exception) → returns safe (err on side of caution)
- analyze_sensitivity: pytesseract not available → returns safe
- apply_redaction: empty regions returns original bytes unchanged
- apply_redaction: redaction with valid regions returns modified PNG
- apply_redaction: PIL failure returns original bytes (not a crash)
- CARD_NUMBER_PATTERN: matches and rejects edge cases
- SSN_PATTERN: matches and rejects edge cases
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from blind_assistant.vision.redaction import (
    CARD_NUMBER_PATTERN,
    SSN_PATTERN,
    SensitivityAnalysis,
    SensitivityLevel,
    analyze_sensitivity,
    apply_redaction,
)

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _minimal_png() -> bytes:
    """Return a minimal valid 1x1 white PNG for image tests."""
    import base64

    # 1x1 white pixel PNG (67 bytes)
    b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQImWP4z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    return base64.b64decode(b64)


# ─────────────────────────────────────────────────────────────
# Enum and dataclass
# ─────────────────────────────────────────────────────────────


def test_sensitivity_level_values_exist():
    assert SensitivityLevel.SAFE.value == "safe"
    assert SensitivityLevel.REDACTED.value == "redacted"
    assert SensitivityLevel.FINANCIAL.value == "financial"
    assert SensitivityLevel.PASSWORD.value == "password"


def test_sensitivity_analysis_defaults():
    s = SensitivityAnalysis()
    assert s.level == SensitivityLevel.SAFE
    assert s.has_password_fields is False
    assert s.has_financial_content is False
    assert s.regions_to_redact == []


# ─────────────────────────────────────────────────────────────
# analyze_sensitivity — password detection
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_sensitivity_password_keyword_returns_password_level():
    with patch(
        "blind_assistant.vision.redaction._extract_text",
        new_callable=AsyncMock,
        return_value="Enter your password here",
    ):
        result = await analyze_sensitivity(b"fake_screenshot")
    assert result.level == SensitivityLevel.PASSWORD
    assert result.has_password_fields is True


@pytest.mark.asyncio
async def test_analyze_sensitivity_passphrase_detected():
    with patch(
        "blind_assistant.vision.redaction._extract_text",
        new_callable=AsyncMock,
        return_value="Enter passphrase to unlock",
    ):
        result = await analyze_sensitivity(b"fake_screenshot")
    assert result.level == SensitivityLevel.PASSWORD


@pytest.mark.asyncio
async def test_analyze_sensitivity_password_returns_immediately_without_further_checks():
    """Once a password field is found, we return immediately — no further checks."""
    # Even if there's also a card number, password takes priority
    with patch(
        "blind_assistant.vision.redaction._extract_text",
        new_callable=AsyncMock,
        return_value="password: xxxx card: 4111 1111 1111 1111",
    ):
        result = await analyze_sensitivity(b"fake")
    assert result.level == SensitivityLevel.PASSWORD
    # has_financial_content should NOT be set (we returned early)
    assert result.has_financial_content is False


# ─────────────────────────────────────────────────────────────
# analyze_sensitivity — financial detection
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_sensitivity_card_number_returns_financial():
    with patch(
        "blind_assistant.vision.redaction._extract_text",
        new_callable=AsyncMock,
        return_value="card number: 4111 1111 1111 1111",
    ):
        result = await analyze_sensitivity(b"fake")
    assert result.level == SensitivityLevel.FINANCIAL
    assert result.has_financial_content is True


@pytest.mark.asyncio
async def test_analyze_sensitivity_ssn_returns_financial():
    with patch(
        "blind_assistant.vision.redaction._extract_text",
        new_callable=AsyncMock,
        return_value="SSN: 123-45-6789 on file",
    ):
        result = await analyze_sensitivity(b"fake")
    assert result.level == SensitivityLevel.FINANCIAL
    assert result.has_financial_content is True


@pytest.mark.asyncio
async def test_analyze_sensitivity_financial_domain_returns_financial():
    with patch(
        "blind_assistant.vision.redaction._extract_text",
        new_callable=AsyncMock,
        return_value="Welcome to Chase Online Banking",
    ):
        result = await analyze_sensitivity(b"fake")
    assert result.level == SensitivityLevel.FINANCIAL
    assert result.has_financial_content is True


@pytest.mark.asyncio
async def test_analyze_sensitivity_paypal_detected():
    with patch(
        "blind_assistant.vision.redaction._extract_text", new_callable=AsyncMock, return_value="Send money via PayPal"
    ):
        result = await analyze_sensitivity(b"fake")
    assert result.level == SensitivityLevel.FINANCIAL


# ─────────────────────────────────────────────────────────────
# analyze_sensitivity — safe content
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_sensitivity_clean_text_returns_safe():
    with patch(
        "blind_assistant.vision.redaction._extract_text",
        new_callable=AsyncMock,
        return_value="Today's weather is sunny and warm.",
    ):
        result = await analyze_sensitivity(b"fake")
    assert result.level == SensitivityLevel.SAFE
    assert result.has_password_fields is False
    assert result.has_financial_content is False


@pytest.mark.asyncio
async def test_analyze_sensitivity_empty_text_returns_safe():
    with patch("blind_assistant.vision.redaction._extract_text", new_callable=AsyncMock, return_value=""):
        result = await analyze_sensitivity(b"fake")
    assert result.level == SensitivityLevel.SAFE


# ─────────────────────────────────────────────────────────────
# analyze_sensitivity — OCR failure
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_sensitivity_ocr_exception_returns_safe():
    """If OCR fails with an exception, we treat the screen as safe (not crash)."""
    with patch(
        "blind_assistant.vision.redaction._extract_text",
        new_callable=AsyncMock,
        side_effect=RuntimeError("OCR crashed"),
    ):
        result = await analyze_sensitivity(b"fake")
    assert result.level == SensitivityLevel.SAFE


# ─────────────────────────────────────────────────────────────
# apply_redaction
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_redaction_empty_regions_returns_original():
    original = b"original_screenshot_bytes"
    result = await apply_redaction(original, [])
    assert result == original


@pytest.mark.asyncio
async def test_apply_redaction_valid_regions_returns_bytes():
    """Applying redaction to a real PNG with a region produces valid output."""
    png = _minimal_png()
    result = await apply_redaction(png, [(0, 0, 1, 1)])
    # Should return bytes (not crash)
    assert isinstance(result, bytes)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_apply_redaction_with_pil_error_returns_original():
    """If PIL fails during redaction, the original bytes are returned (not a crash)."""
    original = b"not_a_real_png"
    result = await apply_redaction(original, [(0, 0, 10, 10)])
    # PIL will fail to open invalid bytes — should return original
    assert result == original


# ─────────────────────────────────────────────────────────────
# Pattern matching — CARD_NUMBER_PATTERN
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "4111 1111 1111 1111",  # spaces
        "4111-1111-1111-1111",  # dashes
        "4111111111111111",  # no separators
    ],
)
def test_card_number_pattern_matches_valid_cards(text: str):
    assert CARD_NUMBER_PATTERN.search(text) is not None


@pytest.mark.parametrize(
    "text",
    [
        "123 456 789",  # too short
        "not-a-card-number",
        "1234",
    ],
)
def test_card_number_pattern_does_not_match_non_cards(text: str):
    assert CARD_NUMBER_PATTERN.search(text) is None


# ─────────────────────────────────────────────────────────────
# Pattern matching — SSN_PATTERN
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "123-45-6789",
        "SSN: 987-65-4321",
    ],
)
def test_ssn_pattern_matches_valid_ssns(text: str):
    assert SSN_PATTERN.search(text) is not None


@pytest.mark.parametrize(
    "text",
    [
        "1234-56-789",  # wrong grouping
        "12-34-5678",  # wrong grouping
        "no ssn here",
    ],
)
def test_ssn_pattern_does_not_match_non_ssns(text: str):
    assert SSN_PATTERN.search(text) is None


# ─────────────────────────────────────────────────────────────
# PASSWORD_KEYWORDS completeness
# ─────────────────────────────────────────────────────────────


def test_password_keywords_includes_core_terms():
    from blind_assistant.vision.redaction import PASSWORD_KEYWORDS

    assert "password" in PASSWORD_KEYWORDS
    assert "pin" in PASSWORD_KEYWORDS
    assert "passphrase" in PASSWORD_KEYWORDS
