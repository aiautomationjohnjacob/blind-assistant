"""
Unit tests for blind_assistant.security.disclosure

Coverage target: 100% (security-critical — risk disclosure is non-negotiable)

These tests verify that:
- Confirmation and cancellation detection works for all keywords
- Edge cases (case, whitespace, partial match) are handled correctly
- The disclosure texts contain the required information
- Templates have the correct placeholder variables
"""

from __future__ import annotations

import pytest

from blind_assistant.security.disclosure import (
    ACTION_CONFIRMATION_TEMPLATE,
    CANCELLATION_KEYWORDS,
    CONFIRMATION_KEYWORDS,
    FINANCIAL_RISK_DISCLOSURE,
    FINANCIAL_RISK_DISCLOSURE_BRIEF,
    FINANCIAL_SCREEN_PROTECTION_NOTICE,
    INSTALL_CONSENT_TEMPLATE,
    ORDER_CONFIRMATION_TEMPLATE,
    TELEGRAM_SECURITY_NOTICE,
    is_cancellation,
    is_confirmation,
)

pytestmark = pytest.mark.security


# ─────────────────────────────────────────────────────────────
# is_confirmation
# ─────────────────────────────────────────────────────────────

class TestIsConfirmation:
    @pytest.mark.parametrize("keyword", list(CONFIRMATION_KEYWORDS))
    def test_returns_true_for_all_confirmation_keywords(self, keyword):
        assert is_confirmation(keyword) is True

    @pytest.mark.parametrize("keyword", list(CONFIRMATION_KEYWORDS))
    def test_case_insensitive(self, keyword):
        assert is_confirmation(keyword.upper()) is True
        assert is_confirmation(keyword.title()) is True

    @pytest.mark.parametrize("keyword", list(CONFIRMATION_KEYWORDS))
    def test_strips_surrounding_whitespace(self, keyword):
        assert is_confirmation(f"  {keyword}  ") is True

    def test_returns_false_for_empty_string(self):
        assert is_confirmation("") is False

    def test_returns_false_for_partial_match(self):
        # "yes please" is not a bare confirmation keyword
        assert is_confirmation("yes please") is False

    def test_returns_false_for_cancellation_keywords(self):
        for word in CANCELLATION_KEYWORDS:
            assert is_confirmation(word) is False

    def test_returns_false_for_gibberish(self):
        assert is_confirmation("xxxxxx") is False
        assert is_confirmation("maybe") is False


# ─────────────────────────────────────────────────────────────
# is_cancellation
# ─────────────────────────────────────────────────────────────

class TestIsCancellation:
    @pytest.mark.parametrize("keyword", list(CANCELLATION_KEYWORDS))
    def test_returns_true_for_all_cancellation_keywords(self, keyword):
        assert is_cancellation(keyword) is True

    @pytest.mark.parametrize("keyword", list(CANCELLATION_KEYWORDS))
    def test_case_insensitive(self, keyword):
        assert is_cancellation(keyword.upper()) is True

    def test_matches_keyword_within_phrase(self):
        # "cancel" inside a phrase should still be caught
        assert is_cancellation("actually cancel that") is True
        assert is_cancellation("please stop") is True

    def test_returns_false_for_empty_string(self):
        assert is_cancellation("") is False

    def test_returns_false_for_confirmation_keywords(self):
        assert is_cancellation("yes") is False
        assert is_cancellation("confirm") is False

    def test_returns_false_for_neutral_phrase(self):
        assert is_cancellation("what time is it") is False


# ─────────────────────────────────────────────────────────────
# Disclosure text content requirements
# (non-negotiable safety properties)
# ─────────────────────────────────────────────────────────────

class TestFinancialRiskDisclosure:
    def test_disclosure_is_not_empty(self):
        assert FINANCIAL_RISK_DISCLOSURE.strip() != ""

    def test_disclosure_mentions_risk(self):
        text = FINANCIAL_RISK_DISCLOSURE.lower()
        assert "risk" in text, "Disclosure must mention 'risk'"

    def test_disclosure_mentions_encryption(self):
        text = FINANCIAL_RISK_DISCLOSURE.lower()
        assert "encrypt" in text, "Disclosure must mention encryption"

    def test_disclosure_says_no_card_numbers_stored(self):
        text = FINANCIAL_RISK_DISCLOSURE.lower()
        assert "card" in text, "Disclosure must mention card numbers"
        assert "store" in text or "never" in text, "Disclosure must say we don't store card numbers"

    def test_disclosure_offers_removal(self):
        text = FINANCIAL_RISK_DISCLOSURE.lower()
        assert "remove" in text or "delete" in text, "Disclosure must explain how to remove payment info"

    def test_disclosure_asks_for_consent(self):
        text = FINANCIAL_RISK_DISCLOSURE.lower()
        assert "continue" in text or "?" in text, "Disclosure must ask user whether to continue"

    def test_brief_disclosure_is_shorter_than_full(self):
        assert len(FINANCIAL_RISK_DISCLOSURE_BRIEF) < len(FINANCIAL_RISK_DISCLOSURE)

    def test_brief_disclosure_is_not_empty(self):
        assert FINANCIAL_RISK_DISCLOSURE_BRIEF.strip() != ""

    def test_brief_disclosure_still_mentions_risk(self):
        assert "risk" in FINANCIAL_RISK_DISCLOSURE_BRIEF.lower()

    def test_brief_disclosure_still_mentions_encryption(self):
        assert "encrypt" in FINANCIAL_RISK_DISCLOSURE_BRIEF.lower()


class TestFinancialScreenProtectionNotice:
    def test_notice_is_not_empty(self):
        assert FINANCIAL_SCREEN_PROTECTION_NOTICE.strip() != ""

    def test_notice_says_screen_is_protected(self):
        text = FINANCIAL_SCREEN_PROTECTION_NOTICE.lower()
        assert "protect" in text or "not send" in text or "won't send" in text

    def test_notice_mentions_financial_context(self):
        text = FINANCIAL_SCREEN_PROTECTION_NOTICE.lower()
        assert "financial" in text or "payment" in text or "bank" in text


class TestTelegramSecurityNotice:
    def test_notice_is_not_empty(self):
        assert TELEGRAM_SECURITY_NOTICE.strip() != ""

    def test_warns_about_bot_message_visibility(self):
        text = TELEGRAM_SECURITY_NOTICE.lower()
        assert "telegram" in text

    def test_advises_not_to_send_passwords_via_telegram(self):
        text = TELEGRAM_SECURITY_NOTICE.lower()
        assert "password" in text or "card" in text


# ─────────────────────────────────────────────────────────────
# Template format tests
# ─────────────────────────────────────────────────────────────

class TestTemplates:
    def test_order_confirmation_has_order_summary_placeholder(self):
        assert "{order_summary}" in ORDER_CONFIRMATION_TEMPLATE

    def test_order_confirmation_has_total_amount_placeholder(self):
        assert "{total_amount}" in ORDER_CONFIRMATION_TEMPLATE

    def test_order_confirmation_is_formattable(self):
        result = ORDER_CONFIRMATION_TEMPLATE.format(
            order_summary="1x Large Pizza",
            total_amount="$18.50"
        )
        assert "1x Large Pizza" in result
        assert "$18.50" in result

    def test_install_consent_has_required_placeholders(self):
        for placeholder in ["{task_description}", "{package_name}", "{package_description}"]:
            assert placeholder in INSTALL_CONSENT_TEMPLATE

    def test_install_consent_is_formattable(self):
        result = INSTALL_CONSENT_TEMPLATE.format(
            task_description="order food",
            package_name="doordash-api",
            package_description="food delivery integration"
        )
        assert "order food" in result
        assert "doordash-api" in result

    def test_action_confirmation_has_action_description_placeholder(self):
        assert "{action_description}" in ACTION_CONFIRMATION_TEMPLATE

    def test_action_confirmation_is_formattable(self):
        result = ACTION_CONFIRMATION_TEMPLATE.format(action_description="send an email")
        assert "send an email" in result


# ─────────────────────────────────────────────────────────────
# Keyword set completeness
# ─────────────────────────────────────────────────────────────

class TestKeywordSets:
    def test_confirmation_keywords_not_empty(self):
        assert len(CONFIRMATION_KEYWORDS) >= 5

    def test_cancellation_keywords_not_empty(self):
        assert len(CANCELLATION_KEYWORDS) >= 5

    def test_no_overlap_between_sets(self):
        overlap = CONFIRMATION_KEYWORDS & CANCELLATION_KEYWORDS
        assert overlap == set(), (
            f"Keywords appear in both confirmation and cancellation sets: {overlap}"
        )

    def test_all_keywords_are_lowercase(self):
        for kw in CONFIRMATION_KEYWORDS | CANCELLATION_KEYWORDS:
            assert kw == kw.lower(), f"Keyword '{kw}' is not lowercase"
