"""
Vault Encryption — AES-256-GCM

Encrypts and decrypts the Second Brain vault contents.

Per SECURITY_MODEL.md §1.1:
- AES-256-GCM encryption
- PBKDF2-HMAC-SHA256 with 600,000 iterations for key derivation
- Salt stored alongside vault (not secret)
- Key NEVER stored on disk — derived each session from passphrase
- Alternatively: OS keychain stores derived key (unlocked by system login)
"""

import base64
import logging
import os

logger = logging.getLogger(__name__)

# Key derivation parameters
PBKDF2_ITERATIONS = 600_000
SALT_SIZE = 32  # bytes
KEY_SIZE = 32  # 256 bits for AES-256


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """
    Derive an AES-256 key from a passphrase using PBKDF2-HMAC-SHA256.

    Args:
        passphrase: User's vault passphrase (never stored)
        salt: Per-vault random salt (stored alongside vault, not secret)

    Returns:
        32-byte key suitable for AES-256-GCM

    Security: 600,000 iterations makes brute-force prohibitively expensive.
    """
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def generate_salt() -> bytes:
    """Generate a random salt for a new vault."""
    return os.urandom(SALT_SIZE)


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """
    Encrypt bytes using AES-256-GCM.

    Returns:
        nonce (12 bytes) + ciphertext + tag (16 bytes), all concatenated.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext  # nonce prepended for decryption


def decrypt(ciphertext_with_nonce: bytes, key: bytes) -> bytes:
    """
    Decrypt AES-256-GCM ciphertext.

    Args:
        ciphertext_with_nonce: nonce (12 bytes) + ciphertext + tag
        key: AES-256 key

    Returns:
        Decrypted plaintext bytes

    Raises:
        cryptography.exceptions.InvalidTag: If decryption fails (wrong key or tampered)
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = ciphertext_with_nonce[:12]
    ciphertext = ciphertext_with_nonce[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def encrypt_string(text: str, key: bytes) -> bytes:
    """Convenience: encrypt a UTF-8 string."""
    return encrypt(text.encode("utf-8"), key)


def decrypt_string(ciphertext: bytes, key: bytes) -> str:
    """Convenience: decrypt to a UTF-8 string."""
    return decrypt(ciphertext, key).decode("utf-8")


class VaultKey:
    """
    Manages the vault encryption key for a session.

    The key is derived from the user's passphrase and never stored on disk.
    Alternative: store in OS keychain (unlocked by system login).
    """

    def __init__(self) -> None:
        self._key: bytes | None = None

    def unlock(self, passphrase: str, salt: bytes) -> None:
        """Derive and cache the vault key for this session."""
        self._key = derive_key(passphrase, salt)
        logger.debug("Vault unlocked.")

    def unlock_from_keychain(self) -> bool:
        """
        Try to load the vault key from the OS keychain.
        Returns True if successful.
        """
        from blind_assistant.security.credentials import get_credential

        encoded_key = get_credential("vault_key")
        if encoded_key:
            self._key = base64.b64decode(encoded_key)
            logger.debug("Vault key loaded from keychain.")
            return True
        return False

    def store_in_keychain(self) -> None:
        """Store the current key in the OS keychain for future sessions."""
        if self._key is None:
            raise RuntimeError("No key to store — unlock the vault first.")
        from blind_assistant.security.credentials import store_credential

        store_credential("vault_key", base64.b64encode(self._key).decode())
        logger.debug("Vault key stored in keychain.")

    def lock(self) -> None:
        """Clear the key from memory."""
        self._key = None
        logger.debug("Vault locked.")

    @property
    def is_unlocked(self) -> bool:
        return self._key is not None

    def get_key(self) -> bytes:
        if self._key is None:
            raise RuntimeError("Vault is locked. Please unlock with your passphrase first.")
        return self._key
