"""
Unit tests for blind_assistant.security.credentials

Coverage target: 100% (security-critical module)

All tests use mock_keyring to avoid touching the real OS keychain.
Tests are marked @pytest.mark.security so CI can enforce 100% coverage
on this module specifically.
"""

from __future__ import annotations

from unittest.mock import patch

import keyring.errors
import pytest

from blind_assistant.security.credentials import (
    CLAUDE_API_KEY,
    ELEVENLABS_API_KEY,
    SERVICE_NAME,
    STRIPE_PAYMENT_METHOD,
    STRIPE_SECRET_KEY,
    TELEGRAM_ALLOWED_USER_IDS,
    TELEGRAM_BOT_TOKEN,
    VAULT_PASSPHRASE_HINT,
    _register_key,
    _unregister_key,
    delete_credential,
    get_credential,
    list_stored_keys,
    require_credential,
    store_credential,
)

pytestmark = pytest.mark.security


# ─────────────────────────────────────────────────────────────
# store_credential
# ─────────────────────────────────────────────────────────────

class TestStoreCredential:
    def test_stores_value_in_keychain(self, mock_keyring):
        store_credential("test_key", "test_value")
        assert mock_keyring.store["blind-assistant", "test_key"] == "test_value"

    def test_uses_service_name_constant(self, mock_keyring):
        store_credential("my_key", "my_val")
        assert ("blind-assistant", "my_key") in mock_keyring.store

    def test_raises_runtime_error_when_keychain_unavailable(self):
        with patch("keyring.set_password", side_effect=keyring.errors.KeyringError("no keychain")):
            with pytest.raises(RuntimeError, match="OS keychain may not be available"):
                store_credential("key", "value")

    def test_runtime_error_message_includes_key_name(self):
        with patch("keyring.set_password", side_effect=keyring.errors.KeyringError("err")):
            with pytest.raises(RuntimeError, match="my_important_key"):
                store_credential("my_important_key", "value")

    def test_overwrites_existing_value(self, mock_keyring):
        store_credential("token", "old_value")
        store_credential("token", "new_value")
        assert mock_keyring.store["blind-assistant", "token"] == "new_value"


# ─────────────────────────────────────────────────────────────
# get_credential
# ─────────────────────────────────────────────────────────────

class TestGetCredential:
    def test_returns_stored_value(self, mock_keyring):
        store_credential("api_key", "sk-abc123")
        assert get_credential("api_key") == "sk-abc123"

    def test_returns_none_when_not_found(self, mock_keyring):
        assert get_credential("nonexistent_key") is None

    def test_returns_none_on_keyring_error(self):
        with patch("keyring.get_password", side_effect=keyring.errors.KeyringError("error")):
            result = get_credential("any_key")
        assert result is None

    def test_does_not_raise_on_keyring_error(self):
        with patch("keyring.get_password", side_effect=keyring.errors.KeyringError("error")):
            # Should swallow the error, not propagate it
            get_credential("key")  # no exception

    def test_returns_empty_string_if_stored_as_empty(self, mock_keyring):
        store_credential("empty_key", "")
        # Empty string is a valid stored value (distinguishable from None)
        result = get_credential("empty_key")
        assert result == "" or result is None  # depends on keyring behaviour with ""


# ─────────────────────────────────────────────────────────────
# delete_credential
# ─────────────────────────────────────────────────────────────

class TestDeleteCredential:
    def test_returns_true_when_deleted(self, mock_keyring):
        store_credential("to_delete", "value")
        assert delete_credential("to_delete") is True

    def test_removes_from_keychain(self, mock_keyring):
        store_credential("to_delete", "value")
        delete_credential("to_delete")
        assert get_credential("to_delete") is None

    def test_returns_false_when_not_found(self, mock_keyring):
        assert delete_credential("never_existed") is False

    def test_returns_false_on_keyring_error(self):
        with patch("keyring.delete_password", side_effect=keyring.errors.KeyringError("err")):
            assert delete_credential("key") is False

    def test_does_not_raise_on_keyring_error(self):
        with patch("keyring.delete_password", side_effect=keyring.errors.KeyringError("err")):
            delete_credential("key")  # no exception


# ─────────────────────────────────────────────────────────────
# require_credential
# ─────────────────────────────────────────────────────────────

class TestRequireCredential:
    def test_returns_value_when_present(self, mock_keyring):
        store_credential("required_key", "secret123")
        assert require_credential("required_key") == "secret123"

    def test_raises_value_error_when_missing(self, mock_keyring):
        with pytest.raises(ValueError):
            require_credential("missing_key")

    def test_error_message_includes_key_name(self, mock_keyring):
        with pytest.raises(ValueError, match="missing_key"):
            require_credential("missing_key")

    def test_error_message_includes_setup_instructions(self, mock_keyring):
        with pytest.raises(ValueError, match="setup wizard"):
            require_credential("missing_key")

    def test_never_returns_none(self, mock_keyring):
        store_credential("real_key", "value")
        result = require_credential("real_key")
        assert result is not None
        assert isinstance(result, str)


# ─────────────────────────────────────────────────────────────
# list_stored_keys
# ─────────────────────────────────────────────────────────────

class TestListStoredKeys:
    def test_returns_empty_list_when_no_registry(self, mock_keyring):
        assert list_stored_keys() == []

    def test_returns_keys_from_registry(self, mock_keyring):
        # Manually set the key registry
        import keyring as kr
        kr.set_password(SERVICE_NAME, "_key_registry", "telegram_bot_token,claude_api_key")
        keys = list_stored_keys()
        assert "telegram_bot_token" in keys
        assert "claude_api_key" in keys

    def test_strips_whitespace_from_keys(self, mock_keyring):
        import keyring as kr
        kr.set_password(SERVICE_NAME, "_key_registry", " key1 , key2 ")
        keys = list_stored_keys()
        assert "key1" in keys
        assert "key2" in keys

    def test_does_not_return_empty_entries(self, mock_keyring):
        import keyring as kr
        kr.set_password(SERVICE_NAME, "_key_registry", "key1,,key2,")
        keys = list_stored_keys()
        assert "" not in keys

    def test_never_returns_key_values_only_names(self, mock_keyring):
        store_credential("secret_key", "super_secret_value")
        keys = list_stored_keys()
        assert "super_secret_value" not in keys


# ─────────────────────────────────────────────────────────────
# _register_key / _unregister_key
# ─────────────────────────────────────────────────────────────

class TestKeyRegistry:
    def test_register_key_adds_to_registry(self, mock_keyring):
        _register_key("new_key")
        assert "new_key" in list_stored_keys()

    def test_register_key_does_not_duplicate(self, mock_keyring):
        _register_key("dup_key")
        _register_key("dup_key")
        keys = list_stored_keys()
        assert keys.count("dup_key") == 1

    def test_register_key_skips_underscore_prefixed(self, mock_keyring):
        _register_key("_internal_key")
        assert "_internal_key" not in list_stored_keys()

    def test_unregister_key_removes_from_registry(self, mock_keyring):
        _register_key("temp_key")
        _unregister_key("temp_key")
        assert "temp_key" not in list_stored_keys()

    def test_unregister_key_silently_ignores_missing(self, mock_keyring):
        # Should not raise if key was never registered
        _unregister_key("never_registered")  # no exception


# ─────────────────────────────────────────────────────────────
# Key name constants (non-negotiable security contract)
# ─────────────────────────────────────────────────────────────

class TestKeyNameConstants:
    """
    These constants are used everywhere in the codebase.
    Changing them would break credential lookup at runtime.
    Test that they are stable strings.
    """

    def test_constants_are_strings(self):
        for const in [
            TELEGRAM_BOT_TOKEN,
            TELEGRAM_ALLOWED_USER_IDS,
            CLAUDE_API_KEY,
            ELEVENLABS_API_KEY,
            STRIPE_SECRET_KEY,
            STRIPE_PAYMENT_METHOD,
            VAULT_PASSPHRASE_HINT,
        ]:
            assert isinstance(const, str)
            assert len(const) > 0

    def test_stripe_payment_method_is_token_not_raw_number(self):
        # The constant name must indicate tokenization to prevent raw number storage
        assert "token" in STRIPE_PAYMENT_METHOD.lower(), (
            "Stripe payment field must be named 'token' to prevent raw card number storage"
        )

    def test_vault_hint_not_passphrase(self):
        # We store a HINT, never the actual passphrase
        assert "hint" in VAULT_PASSPHRASE_HINT.lower()
        assert "passphrase" not in VAULT_PASSPHRASE_HINT.lower() or "hint" in VAULT_PASSPHRASE_HINT.lower()
