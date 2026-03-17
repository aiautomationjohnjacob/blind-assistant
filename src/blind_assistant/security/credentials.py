"""
Credential Management — OS Keychain Access

All secrets (API keys, bot tokens, user IDs) are stored in the OS keychain.
NEVER stored in .env files, config files, or environment variables.

Uses:
- Linux: libsecret (SecretService backend)
- macOS: macOS Keychain
- Windows: Windows Credential Manager

All via the `keyring` library for cross-platform compatibility.
"""

import logging

import keyring
import keyring.errors

logger = logging.getLogger(__name__)

SERVICE_NAME = "blind-assistant"


def store_credential(key: str, value: str) -> None:
    """
    Store a credential in the OS keychain.

    Args:
        key: Credential identifier (e.g., "telegram_bot_token")
        value: The secret value to store

    Raises:
        RuntimeError: If the keychain is unavailable
    """
    try:
        keyring.set_password(SERVICE_NAME, key, value)
        logger.debug(f"Credential stored: {key}")
    except keyring.errors.KeyringError as e:
        raise RuntimeError(f"Could not store credential '{key}'. The OS keychain may not be available: {e}") from e


def get_credential(key: str) -> str | None:
    """
    Retrieve a credential from the OS keychain.

    Args:
        key: Credential identifier

    Returns:
        The stored value, or None if not found
    """
    try:
        value = keyring.get_password(SERVICE_NAME, key)
        if value is None:
            logger.debug(f"Credential not found: {key}")
        return value
    except keyring.errors.KeyringError as e:
        logger.error(f"Could not retrieve credential '{key}': {e}")
        return None


def delete_credential(key: str) -> bool:
    """
    Delete a credential from the OS keychain.

    Args:
        key: Credential identifier

    Returns:
        True if deleted, False if not found
    """
    try:
        keyring.delete_password(SERVICE_NAME, key)
        logger.info(f"Credential deleted: {key}")
        return True
    except keyring.errors.PasswordDeleteError:
        logger.debug(f"Credential not found for deletion: {key}")
        return False
    except keyring.errors.KeyringError as e:
        logger.error(f"Could not delete credential '{key}': {e}")
        return False


def require_credential(key: str) -> str:
    """
    Get a credential, raising a clear error if missing.
    Use this at startup to validate all required credentials exist.

    Args:
        key: Credential identifier

    Returns:
        The stored value

    Raises:
        ValueError: If the credential is not found (with setup instructions)
    """
    value = get_credential(key)
    if value is None:
        raise ValueError(
            f"Required credential '{key}' not found in keychain. "
            f"Please run the setup wizard: python installer/install.py --setup"
        )
    return value


def list_stored_keys() -> list[str]:
    """
    Return a list of credential keys stored for this service.
    Used for "what do you know about me?" transparency feature.

    Note: Returns key names only, never values.
    """
    # keyring doesn't provide a standard list API across backends.
    # We maintain our own key registry.
    key_registry = get_credential("_key_registry")
    if key_registry is None:
        return []
    return [k.strip() for k in key_registry.split(",") if k.strip()]


def _register_key(key: str) -> None:
    """Internal: track stored key names in the registry."""
    existing = list_stored_keys()
    if key not in existing and not key.startswith("_"):
        existing.append(key)
        keyring.set_password(SERVICE_NAME, "_key_registry", ",".join(existing))


def _unregister_key(key: str) -> None:
    """Internal: remove a key from the registry."""
    existing = list_stored_keys()
    updated = [k for k in existing if k != key]
    keyring.set_password(SERVICE_NAME, "_key_registry", ",".join(updated))


# Key name constants — use these everywhere, never raw strings
TELEGRAM_BOT_TOKEN = "telegram_bot_token"
TELEGRAM_ALLOWED_USER_IDS = "telegram_allowed_user_ids"  # comma-separated
CLAUDE_API_KEY = "claude_api_key"
ELEVENLABS_API_KEY = "elevenlabs_api_key"
STRIPE_SECRET_KEY = "stripe_secret_key"
STRIPE_PAYMENT_METHOD = "stripe_payment_method_token"
VAULT_PASSPHRASE_HINT = "vault_passphrase_hint"  # Hint only, never the passphrase itself
API_SERVER_TOKEN = "api_server_token"  # Bearer token for the REST API server
