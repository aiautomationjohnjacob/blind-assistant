"""
Tests for the vault passphrase prompt recovery flow (ISSUE-001 fix).

Covers:
- _get_vault: returns vault when keychain has key (happy path)
- _get_vault: prompts for passphrase when keychain is empty
- _get_vault: returns None with message if no response_callback and no keychain key
- _get_vault: returns None with voice message if passphrase times out
- _get_vault: returns None with voice message if passphrase is wrong
- _get_vault: caches passphrase in context to avoid re-prompting same session
- _collect_vault_passphrase: returns passphrase on queue response
- _collect_vault_passphrase: returns None on timeout
"""

from __future__ import annotations

import asyncio
import base64
from unittest.mock import patch

import pytest

from blind_assistant.core.confirmation import ConfirmationGate
from blind_assistant.core.orchestrator import Orchestrator, UserContext
from blind_assistant.second_brain.encryption import VaultKey, derive_key, generate_salt

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_vault_path(tmp_path):
    return tmp_path / "vault"


@pytest.fixture
def orchestrator_with_gate(tmp_vault_path):
    """Orchestrator with a real ConfirmationGate and temp vault path."""
    config = {"vault_path": str(tmp_vault_path)}
    orch = Orchestrator(config)
    orch.confirmation_gate = ConfirmationGate()
    return orch


@pytest.fixture
def standard_context():
    return UserContext(
        user_id="test_user",
        session_id="test_session",
        verbosity="standard",
        speech_rate=1.0,
        output_mode="voice_text",
        braille_mode=False,
    )


# ─────────────────────────────────────────────────────────────
# Happy path: keychain has the vault key
# ─────────────────────────────────────────────────────────────


class TestGetVaultKeychainHappyPath:
    async def test_returns_vault_when_keychain_has_key(
        self, orchestrator_with_gate, standard_context, tmp_vault_path
    ):
        """When keychain has the vault key, vault is returned without prompting."""
        # Build a real key and encode it as the keychain would store it
        salt = generate_salt()
        real_key = derive_key("test_passphrase", salt)
        encoded_key = base64.b64encode(real_key).decode()

        messages_sent = []

        async def callback(msg):
            messages_sent.append(msg)

        with patch(
            "blind_assistant.security.credentials.get_credential",
            return_value=encoded_key,
        ):
            vault = await orchestrator_with_gate._get_vault(
                standard_context, response_callback=callback
            )

        assert vault is not None
        # Keychain path should not send any messages to the user
        assert len(messages_sent) == 0


# ─────────────────────────────────────────────────────────────
# No keychain key: prompt for passphrase
# ─────────────────────────────────────────────────────────────


class TestGetVaultPassphrasePrompt:
    async def test_prompts_when_no_keychain_key(
        self, orchestrator_with_gate, standard_context, tmp_vault_path
    ):
        """When keychain is empty, the user is prompted for a passphrase."""
        messages_sent = []

        async def callback(msg):
            messages_sent.append(msg)
            # Immediately supply the passphrase so the flow can complete
            orchestrator_with_gate.confirmation_gate.submit_response(
                standard_context.session_id, "test_passphrase_123"
            )

        with patch("blind_assistant.security.credentials.get_credential", return_value=None):
            vault = await orchestrator_with_gate._get_vault(
                standard_context, response_callback=callback
            )

        assert vault is not None
        # Must have sent a prompt message to the user
        prompt_messages = [m for m in messages_sent if "passphrase" in m.lower()]
        assert len(prompt_messages) >= 1

    async def test_no_callback_returns_none_silently(
        self, orchestrator_with_gate, standard_context
    ):
        """Without a response_callback, cannot prompt user — returns None but logs."""
        with patch("blind_assistant.security.credentials.get_credential", return_value=None):
            vault = await orchestrator_with_gate._get_vault(
                standard_context, response_callback=None
            )
        assert vault is None

    async def test_returns_none_when_passphrase_times_out(
        self, orchestrator_with_gate, standard_context
    ):
        """If user doesn't respond within timeout, vault returns None with voice message."""
        messages_sent = []

        async def callback(msg):
            messages_sent.append(msg)
            # Do NOT submit a response — simulate timeout

        # Patch _collect_vault_passphrase to simulate immediate timeout
        async def _mock_collect(context):
            return None

        orchestrator_with_gate._collect_vault_passphrase = _mock_collect

        with patch("blind_assistant.security.credentials.get_credential", return_value=None):
            vault = await orchestrator_with_gate._get_vault(
                standard_context, response_callback=callback
            )

        assert vault is None
        # User must have received an explanatory message
        assert len(messages_sent) >= 1
        # The message must mention the vault is still locked or no passphrase received
        explanation = " ".join(messages_sent)
        assert any(
            keyword in explanation.lower()
            for keyword in ["locked", "passphrase", "did not", "no"]
        )

    async def test_returns_none_with_voice_message_on_wrong_passphrase(
        self, orchestrator_with_gate, standard_context, tmp_vault_path
    ):
        """Wrong passphrase: user gets a spoken error, cached passphrase is cleared."""
        messages_sent = []
        first_call = True

        async def callback(msg):
            nonlocal first_call
            messages_sent.append(msg)
            if first_call:
                first_call = False
                # Submit a passphrase
                orchestrator_with_gate.confirmation_gate.submit_response(
                    standard_context.session_id, "wrong_passphrase"
                )

        # Create a vault with a DIFFERENT salt so key derivation succeeds but vault
        # decryption would fail. We can simulate this by having unlock() raise.
        with (
            patch("blind_assistant.security.credentials.get_credential", return_value=None),
            patch.object(
                VaultKey,
                "unlock",
                side_effect=ValueError("Invalid passphrase"),
            ),
        ):
            vault = await orchestrator_with_gate._get_vault(
                standard_context, response_callback=callback
            )

        assert vault is None
        # User must have received an error message
        error_messages = [m for m in messages_sent if "could not" in m.lower() or "unlock" in m.lower()]
        assert len(error_messages) >= 1
        # Cached passphrase must be cleared so next attempt can re-prompt
        assert not hasattr(standard_context, "_vault_passphrase")

    async def test_caches_passphrase_in_session(
        self, orchestrator_with_gate, standard_context, tmp_vault_path
    ):
        """After successful unlock, passphrase is cached to avoid re-prompting."""
        messages_sent = []
        prompt_count = [0]

        async def callback(msg):
            messages_sent.append(msg)
            if "passphrase" in msg.lower() and "passphrase" not in str(
                getattr(standard_context, "_vault_passphrase", "")
            ):
                prompt_count[0] += 1
                orchestrator_with_gate.confirmation_gate.submit_response(
                    standard_context.session_id, "my_good_passphrase"
                )

        with patch("blind_assistant.security.credentials.get_credential", return_value=None):
            vault1 = await orchestrator_with_gate._get_vault(
                standard_context, response_callback=callback
            )

        assert vault1 is not None
        # Passphrase must be cached in context
        assert hasattr(standard_context, "_vault_passphrase")
        assert standard_context._vault_passphrase == "my_good_passphrase"  # type: ignore[attr-defined]


# ─────────────────────────────────────────────────────────────
# _collect_vault_passphrase
# ─────────────────────────────────────────────────────────────


class TestCollectVaultPassphrase:
    async def test_returns_passphrase_from_queue(
        self, orchestrator_with_gate, standard_context
    ):
        """Returns the string submitted to the confirmation gate queue."""
        orchestrator_with_gate.confirmation_gate.register_session(standard_context.session_id)
        orchestrator_with_gate.confirmation_gate.submit_response(
            standard_context.session_id, "  my_secret_phrase  "
        )
        result = await orchestrator_with_gate._collect_vault_passphrase(standard_context)
        assert result == "my_secret_phrase"

    async def test_returns_none_on_timeout(
        self, orchestrator_with_gate, standard_context
    ):
        """Returns None if no response arrives before timeout."""
        # Patch asyncio.wait_for to simulate timeout immediately
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            result = await orchestrator_with_gate._collect_vault_passphrase(standard_context)
        assert result is None

    async def test_strips_whitespace_from_passphrase(
        self, orchestrator_with_gate, standard_context
    ):
        """Passphrase is stripped of leading/trailing whitespace."""
        orchestrator_with_gate.confirmation_gate.register_session(standard_context.session_id)
        orchestrator_with_gate.confirmation_gate.submit_response(
            standard_context.session_id, "   passphrase with spaces   "
        )
        result = await orchestrator_with_gate._collect_vault_passphrase(standard_context)
        assert result == "passphrase with spaces"

    async def test_empty_response_returns_none(
        self, orchestrator_with_gate, standard_context
    ):
        """Empty or whitespace-only response returns None (not an empty string)."""
        orchestrator_with_gate.confirmation_gate.register_session(standard_context.session_id)
        orchestrator_with_gate.confirmation_gate.submit_response(
            standard_context.session_id, "   "
        )
        result = await orchestrator_with_gate._collect_vault_passphrase(standard_context)
        assert result is None
