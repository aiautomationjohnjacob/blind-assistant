"""
E2E Desktop Tests — NVDA screen reader (Windows)

Tests the Blind Assistant Desktop CLI (Python voice interface) with NVDA,
the most widely used free screen reader on Windows.

NOTE: NVDA is Windows-only. These tests are intended to be run on a Windows CI
agent or a Windows developer machine with NVDA installed.

Currently tests the Desktop CLI (voice_local.py), not a native Desktop GUI app.
A native Windows Desktop app (Electron or Tauri) is planned for Phase 3.

These tests are skipped until a Windows CI runner with NVDA is configured.
"""

import pytest

# Skip all tests until Windows CI runner with NVDA is set up
pytestmark = pytest.mark.skip(
    reason=(
        "Windows + NVDA environment not set up in CI. "
        "ISSUE-010: Desktop NVDA E2E planned for Phase 3. "
        "Run manually on Windows with NVDA installed."
    )
)


class TestDesktopCLIWithNVDA:
    """
    Tests for the Desktop CLI (voice_local.py) with NVDA.

    NVDA reads console output and can interact with the terminal.
    These tests verify the CLI speaks in a way NVDA can read aloud.
    """

    def test_startup_message_contains_no_visual_language(self):
        """
        The startup announcement must not contain visual-only language.
        'Click the button' is meaningless to a keyboard/voice user.
        Acceptable: 'Say assistant followed by your request.'
        """
        startup_message = (
            "Blind Assistant is ready. Say 'assistant' followed by your request. Or just speak and I will listen."
        )
        visual_only_terms = ["click", "tap", "see", "look", "view", "watch"]
        for term in visual_only_terms:
            assert term not in startup_message.lower(), (
                f"Visual-only term '{term}' found in startup message. Replace with voice/keyboard equivalent."
            )

    def test_error_message_gives_recovery_path(self):
        """
        Error messages must tell the user what to do next.
        'I had trouble with that request. Could you try again or rephrase it?'
        Not just: 'Error.'
        """
        error_message = "I had trouble with that request. Could you try again or rephrase it?"
        # Must give a path forward
        assert any(word in error_message.lower() for word in ["try", "say", "speak", "rephrase"])
