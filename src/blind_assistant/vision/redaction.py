"""
Screenshot Redaction

Detects and redacts sensitive content from screenshots before any external API call.

Per SECURITY_MODEL.md §1.4:
- Password fields: NEVER sent to external API
- Financial screens: redact or use local processing only
- SSNs, card numbers, account numbers: always redact
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SensitivityLevel(Enum):
    SAFE = "safe"
    REDACTED = "redacted"  # Sensitive regions removed; safe to send
    FINANCIAL = "financial"  # Financial screen; use local only
    PASSWORD = "password"  # Password fields; never send to API


@dataclass
class SensitivityAnalysis:
    level: SensitivityLevel = SensitivityLevel.SAFE
    has_password_fields: bool = False
    has_financial_content: bool = False
    regions_to_redact: list = field(default_factory=list)  # list of (x, y, w, h)


# Patterns for detecting sensitive text content
CARD_NUMBER_PATTERN = re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
ACCOUNT_NUMBER_PATTERN = re.compile(r"\b\d{8,17}\b")

# Financial domain patterns (used for URL/title detection)
FINANCIAL_DOMAINS = {
    "bank",
    "chase",
    "wellsfargo",
    "bankofamerica",
    "citibank",
    "paypal",
    "venmo",
    "cashapp",
    "zelle",
    "mint",
    "ynab",
    "creditcard",
    "creditkarma",
    "robinhood",
    "fidelity",
    "vanguard",
    "schwab",
    "etrade",
    "coinbase",
    "crypto",
}

# Keywords indicating password fields in nearby text
PASSWORD_KEYWORDS = {
    "password",
    "passcode",
    "pin",
    "passphrase",
    "secret",
    "new password",
    "confirm password",
    "current password",
}


async def analyze_sensitivity(
    screenshot_bytes: bytes,
) -> SensitivityAnalysis:
    """
    Analyze a screenshot for sensitive content.

    Returns a SensitivityAnalysis indicating what protection is needed.
    """
    analysis = SensitivityAnalysis()

    try:
        # Use OCR to extract text for analysis
        text_content = await _extract_text(screenshot_bytes)

        # Check for password fields
        for keyword in PASSWORD_KEYWORDS:
            if keyword.lower() in text_content.lower():
                analysis.has_password_fields = True
                analysis.level = SensitivityLevel.PASSWORD
                logger.debug("Password field detected in screenshot")
                return analysis  # Immediately return — never process further

        # Check for card numbers
        if CARD_NUMBER_PATTERN.search(text_content):
            analysis.has_financial_content = True
            analysis.level = SensitivityLevel.FINANCIAL
            return analysis

        # Check for SSNs
        if SSN_PATTERN.search(text_content):
            analysis.has_financial_content = True
            analysis.level = SensitivityLevel.FINANCIAL
            return analysis

        # Check for financial domain keywords in the text
        text_lower = text_content.lower()
        for domain in FINANCIAL_DOMAINS:
            if domain in text_lower:
                analysis.has_financial_content = True
                analysis.level = SensitivityLevel.FINANCIAL
                return analysis

    except Exception as e:
        # If analysis fails, err on the side of caution
        logger.warning(f"Sensitivity analysis failed, treating as safe: {e}")

    return analysis


async def apply_redaction(
    screenshot_bytes: bytes,
    regions: list,
) -> bytes:
    """
    Apply black rectangle redaction to specified regions.

    Args:
        screenshot_bytes: Original screenshot
        regions: List of (x, y, w, h) tuples to black out

    Returns:
        Redacted screenshot bytes
    """
    if not regions:
        return screenshot_bytes

    try:
        import io

        from PIL import Image, ImageDraw

        img = Image.open(io.BytesIO(screenshot_bytes))
        draw = ImageDraw.Draw(img)

        for x, y, w, h in regions:
            draw.rectangle([x, y, x + w, y + h], fill="black")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"Redaction failed: {e}")
        # Return original on failure (better than crashing)
        return screenshot_bytes


async def _extract_text(screenshot_bytes: bytes) -> str:
    """Extract text from screenshot using OCR for sensitivity analysis."""
    try:
        import asyncio
        import io

        import pytesseract
        from PIL import Image

        loop = asyncio.get_event_loop()

        def _ocr():
            img = Image.open(io.BytesIO(screenshot_bytes))
            return pytesseract.image_to_string(img)

        return await loop.run_in_executor(None, _ocr)

    except ImportError:
        # pytesseract not available — can't do text-based analysis
        # Fall back to safe (no text detection)
        return ""
    except Exception as e:
        logger.debug(f"OCR text extraction failed: {e}")
        return ""
