"""
Unit tests for blind_assistant.second_brain.encryption

Coverage target: 100% (security-critical — vault encryption)

These tests verify that:
- Key derivation is correct and deterministic
- Encrypt/decrypt roundtrip works
- Wrong keys fail with an exception (tamper detection via GCM auth tag)
- VaultKey lifecycle (lock/unlock/keychain) works correctly
- Ciphertext never contains plaintext (encryption is happening)
"""

from __future__ import annotations

import base64
import os
from unittest.mock import patch

import pytest
from cryptography.exceptions import InvalidTag

from blind_assistant.second_brain.encryption import (
    KEY_SIZE,
    PBKDF2_ITERATIONS,
    SALT_SIZE,
    VaultKey,
    decrypt,
    decrypt_string,
    derive_key,
    encrypt,
    encrypt_string,
    generate_salt,
)

pytestmark = pytest.mark.security


# ─────────────────────────────────────────────────────────────
# generate_salt
# ─────────────────────────────────────────────────────────────


class TestGenerateSalt:
    def test_returns_bytes(self):
        assert isinstance(generate_salt(), bytes)

    def test_returns_correct_size(self):
        assert len(generate_salt()) == SALT_SIZE

    def test_each_call_returns_different_value(self):
        salt1 = generate_salt()
        salt2 = generate_salt()
        assert salt1 != salt2  # random, should not collide


# ─────────────────────────────────────────────────────────────
# derive_key
# ─────────────────────────────────────────────────────────────


class TestDeriveKey:
    def test_returns_bytes(self, sample_passphrase):
        salt = generate_salt()
        key = derive_key(sample_passphrase, salt)
        assert isinstance(key, bytes)

    def test_returns_correct_key_size(self, sample_passphrase):
        salt = generate_salt()
        key = derive_key(sample_passphrase, salt)
        assert len(key) == KEY_SIZE  # 32 bytes = 256 bits

    def test_deterministic_with_same_inputs(self, sample_passphrase):
        salt = os.urandom(32)
        key1 = derive_key(sample_passphrase, salt)
        key2 = derive_key(sample_passphrase, salt)
        assert key1 == key2

    def test_different_passphrases_produce_different_keys(self):
        salt = os.urandom(32)
        key1 = derive_key("passphrase_one", salt)
        key2 = derive_key("passphrase_two", salt)
        assert key1 != key2

    def test_different_salts_produce_different_keys(self, sample_passphrase):
        salt1 = os.urandom(32)
        salt2 = os.urandom(32)
        key1 = derive_key(sample_passphrase, salt1)
        key2 = derive_key(sample_passphrase, salt2)
        assert key1 != key2

    def test_uses_high_iteration_count(self):
        # 600,000 iterations is the NIST recommendation for PBKDF2-SHA256
        assert PBKDF2_ITERATIONS >= 600_000, f"PBKDF2 iterations ({PBKDF2_ITERATIONS}) below NIST minimum of 600,000"

    def test_key_does_not_contain_passphrase(self, sample_passphrase):
        salt = os.urandom(32)
        key = derive_key(sample_passphrase, salt)
        assert sample_passphrase.encode() not in key


# ─────────────────────────────────────────────────────────────
# encrypt / decrypt
# ─────────────────────────────────────────────────────────────


class TestEncryptDecrypt:
    def test_roundtrip_preserves_plaintext(self):
        key = os.urandom(32)
        plaintext = b"hello world"
        assert decrypt(encrypt(plaintext, key), key) == plaintext

    def test_roundtrip_with_empty_bytes(self):
        key = os.urandom(32)
        assert decrypt(encrypt(b"", key), key) == b""

    def test_roundtrip_with_large_data(self):
        key = os.urandom(32)
        plaintext = os.urandom(100_000)  # 100 KB
        assert decrypt(encrypt(plaintext, key), key) == plaintext

    def test_roundtrip_with_unicode_content(self):
        key = os.urandom(32)
        plaintext = "日本語テスト — 中文 — العربية".encode()
        assert decrypt(encrypt(plaintext, key), key) == plaintext

    def test_ciphertext_is_not_plaintext(self):
        key = os.urandom(32)
        plaintext = b"sensitive banking info: 1234"
        ciphertext = encrypt(plaintext, key)
        assert plaintext not in ciphertext

    def test_ciphertext_is_longer_than_plaintext(self):
        key = os.urandom(32)
        plaintext = b"short message"
        ciphertext = encrypt(plaintext, key)
        assert len(ciphertext) > len(plaintext)

    def test_each_encryption_produces_different_ciphertext(self):
        key = os.urandom(32)
        plaintext = b"same message"
        cipher1 = encrypt(plaintext, key)
        cipher2 = encrypt(plaintext, key)
        assert cipher1 != cipher2  # different nonces each time

    def test_wrong_key_raises_invalid_tag(self):
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        ciphertext = encrypt(b"secret", key1)
        with pytest.raises(InvalidTag):
            decrypt(ciphertext, key2)

    def test_tampered_ciphertext_raises_invalid_tag(self):
        key = os.urandom(32)
        ciphertext = bytearray(encrypt(b"data", key))
        # Flip a bit in the ciphertext body (after the 12-byte nonce)
        ciphertext[15] ^= 0xFF
        with pytest.raises(InvalidTag):
            decrypt(bytes(ciphertext), key)

    def test_truncated_ciphertext_raises(self):
        key = os.urandom(32)
        ciphertext = encrypt(b"data", key)
        with pytest.raises((InvalidTag, Exception)):  # cryptography raises InvalidTag or ValueError
            decrypt(ciphertext[:5], key)  # too short — missing tag

    def test_encrypt_returns_bytes(self):
        key = os.urandom(32)
        result = encrypt(b"test", key)
        assert isinstance(result, bytes)


# ─────────────────────────────────────────────────────────────
# encrypt_string / decrypt_string
# ─────────────────────────────────────────────────────────────


class TestEncryptDecryptString:
    def test_roundtrip(self):
        key = os.urandom(32)
        text = "Meeting with Dr. Smith on Thursday."
        assert decrypt_string(encrypt_string(text, key), key) == text

    def test_roundtrip_with_empty_string(self):
        key = os.urandom(32)
        assert decrypt_string(encrypt_string("", key), key) == ""

    def test_roundtrip_with_special_characters(self):
        key = os.urandom(32)
        text = 'Password: p@$$w0rd! Account: "checking" \\n newline'
        assert decrypt_string(encrypt_string(text, key), key) == text

    def test_wrong_key_raises(self):
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        ciphertext = encrypt_string("my note", key1)
        with pytest.raises(InvalidTag):
            decrypt_string(ciphertext, key2)


# ─────────────────────────────────────────────────────────────
# VaultKey
# ─────────────────────────────────────────────────────────────


class TestVaultKey:
    def test_initially_locked(self):
        vk = VaultKey()
        assert vk.is_unlocked is False

    def test_get_key_raises_when_locked(self):
        vk = VaultKey()
        with pytest.raises(RuntimeError, match="locked"):
            vk.get_key()

    def test_unlock_sets_unlocked(self, sample_passphrase):
        vk = VaultKey()
        salt = generate_salt()
        vk.unlock(sample_passphrase, salt)
        assert vk.is_unlocked is True

    def test_unlock_get_key_returns_bytes(self, sample_passphrase):
        vk = VaultKey()
        salt = generate_salt()
        vk.unlock(sample_passphrase, salt)
        key = vk.get_key()
        assert isinstance(key, bytes)
        assert len(key) == KEY_SIZE

    def test_lock_clears_key(self, sample_passphrase):
        vk = VaultKey()
        vk.unlock(sample_passphrase, generate_salt())
        vk.lock()
        assert vk.is_unlocked is False

    def test_lock_then_get_key_raises(self, sample_passphrase):
        vk = VaultKey()
        vk.unlock(sample_passphrase, generate_salt())
        vk.lock()
        with pytest.raises(RuntimeError):
            vk.get_key()

    def test_same_passphrase_same_salt_produces_same_key(self, sample_passphrase):
        salt = generate_salt()
        vk1 = VaultKey()
        vk1.unlock(sample_passphrase, salt)

        vk2 = VaultKey()
        vk2.unlock(sample_passphrase, salt)

        assert vk1.get_key() == vk2.get_key()

    def test_different_passphrases_produce_different_keys(self):
        salt = generate_salt()
        vk1 = VaultKey()
        vk1.unlock("passphrase_a", salt)

        vk2 = VaultKey()
        vk2.unlock("passphrase_b", salt)

        assert vk1.get_key() != vk2.get_key()

    def test_unlock_from_keychain_returns_true_when_key_exists(self, mock_keyring):
        stored_key = os.urandom(32)
        encoded = base64.b64encode(stored_key).decode()

        with patch("blind_assistant.security.credentials.get_credential", return_value=encoded):
            vk = VaultKey()
            result = vk.unlock_from_keychain()

        assert result is True
        assert vk.is_unlocked is True
        assert vk.get_key() == stored_key

    def test_unlock_from_keychain_returns_false_when_no_key(self, mock_keyring):
        with patch("blind_assistant.security.credentials.get_credential", return_value=None):
            vk = VaultKey()
            result = vk.unlock_from_keychain()

        assert result is False
        assert vk.is_unlocked is False

    def test_store_in_keychain_raises_when_locked(self, mock_keyring):
        vk = VaultKey()
        with pytest.raises(RuntimeError, match="unlock the vault first"):
            vk.store_in_keychain()

    def test_store_in_keychain_calls_store_credential(self, mock_keyring, sample_passphrase):
        vk = VaultKey()
        vk.unlock(sample_passphrase, generate_salt())

        with patch("blind_assistant.security.credentials.store_credential") as mock_store:
            vk.store_in_keychain()

        mock_store.assert_called_once()
        key_name, encoded_value = mock_store.call_args[0]
        assert key_name == "vault_key"
        # Verify the stored value is base64-encoded
        decoded = base64.b64decode(encoded_value)
        assert decoded == vk.get_key()

    def test_unlock_from_keychain_then_encrypt_decrypt(self, mock_keyring, sample_passphrase):
        # Full integration: store key → retrieve → use for encryption
        vk_original = VaultKey()
        vk_original.unlock(sample_passphrase, generate_salt())
        original_key = vk_original.get_key()

        # Store the key in the mock keychain
        encoded = base64.b64encode(original_key).decode()

        with patch("blind_assistant.security.credentials.get_credential", return_value=encoded):
            vk_loaded = VaultKey()
            vk_loaded.unlock_from_keychain()

        # Both should produce same encryption results
        plaintext = b"my vault note"
        ciphertext = encrypt(plaintext, vk_loaded.get_key())
        assert decrypt(ciphertext, original_key) == plaintext
