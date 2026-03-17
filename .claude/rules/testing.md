---
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "tests/**"
  - "src/**/*.py"
---

# Testing Rules — Auto-loaded for all Python and test files

## The Non-Negotiables

**Every `src/` file must have a corresponding `tests/unit/` file — same commit.**
No exceptions. No "we'll add tests later." There is no later.

**NEVER delete, truncate, skip, or weaken tests.** If a test is failing, fix the
`src/` implementation. The test is doing its job. This rule is enforced by:
- `PreToolUse` hook: blocks `rm` of test files
- CI: a decrease in test count or coverage creates a P0 GitHub issue
- STEP 7 review panel: `code-reviewer` explicitly checks test count did not decrease

**Tests run automatically** — you do not need to remember:
- Every `git push` triggers `.github/workflows/ci.yml` (lint + typecheck + test + security)
- Every autonomous cycle triggers `.github/workflows/autonomous-cycle.yml` post-cycle tests
- Every `src/` file edit triggers pytest in the PostToolUse hook (immediate feedback)

## Coverage Thresholds (CI-enforced)
- **80%** overall across all modules (hard fail)
- **100%** for `src/blind_assistant/security/` (every line, every branch)
- **100%** for `src/blind_assistant/second_brain/encryption.py`

---

## Python Test Standards

### File structure (mirror src/ under tests/unit/)
```
tests/
  conftest.py           ← shared fixtures; mocks ALL external I/O
  unit/                 ← fast (<100ms each), no real I/O
    security/
      test_credentials.py
      test_disclosure.py
    second_brain/
      test_encryption.py
      test_vault.py
    voice/
      test_stt.py / test_tts.py
    core/
      test_orchestrator.py / test_planner.py / test_confirmation.py
    interfaces/
      test_telegram_bot.py
    vision/
      test_redaction.py / test_screen_observer.py
    tools/
      test_registry.py
  integration/          ← real file I/O; no real external APIs
  accessibility/        ← voice output correctness
  e2e/                  ← full user flow tests (backend pipeline; only external APIs mocked)
    core/               ← backend flows: voice round-trip, Telegram, Second Brain, payment
    platforms/
      web/              ← Playwright tests (Chromium/Firefox/WebKit — NVDA+Chrome, VoiceOver+Safari)
      android/          ← Android emulator tests via ADB (TalkBack accessibility)
      ios/              ← iOS Simulator tests via xcrun simctl (VoiceOver accessibility)
      desktop/          ← Desktop app smoke tests (NVDA on Windows, VoiceOver on macOS)
```

### E2E test naming convention
```
tests/e2e/core/test_[flow_name].py           (e.g., test_voice_conversation.py)
tests/e2e/platforms/web/test_[feature]_[browser].py  (e.g., test_login_chromium.py)
tests/e2e/platforms/android/test_[feature]_talkback.py
tests/e2e/platforms/ios/test_[feature]_voiceover.py
tests/e2e/platforms/desktop/test_[feature]_nvda.py
```

### Coverage thresholds for multi-platform
Python backend thresholds (80% overall, 100% security) apply to `src/` only.
Client app coverage (Android/iOS/Web/Desktop) will have platform-specific requirements
defined by the relevant accessibility expert agent when implementation begins.

### Naming: test_[what]_[condition]_[result]
```python
def test_store_credential_raises_when_keychain_unavailable(): ...
def test_encrypt_decrypt_roundtrip_preserves_plaintext(): ...
def test_is_confirmation_returns_true_for_all_keywords(): ...
```

### Always mock external I/O in unit tests
Use conftest.py fixtures:
- `mock_keyring` — OS keychain
- `mock_claude_client` — Anthropic API
- `mock_telegram_update` / `mock_telegram_context` — Telegram bot
- `mock_elevenlabs` / `mock_pyttsx3` — TTS
- `mock_whisper` — STT
- `temp_vault_dir` — temp files (auto-cleaned)
- `suppress_audio` — applied to ALL tests automatically

### Parametrize to test all values
```python
@pytest.mark.parametrize("keyword", list(CONFIRMATION_KEYWORDS))
def test_is_confirmation(keyword):
    assert is_confirmation(keyword) is True
```

### Test error paths as thoroughly as happy paths
Every `raise` in src/ must have a corresponding `pytest.raises` test.
Every `return None` must have a test that verifies None is returned.

### Security-critical test patterns (required for security/ modules)
```python
# 1. Ciphertext must not contain plaintext
assert plaintext not in ciphertext

# 2. Wrong key must raise
with pytest.raises(InvalidTag):
    decrypt(encrypt(b"data", key1), key2)

# 3. Tampered data must raise
ct = bytearray(encrypt(b"data", key))
ct[15] ^= 0xFF
with pytest.raises(InvalidTag):
    decrypt(bytes(ct), key)

# 4. Constants must have stable names
assert "token" in STRIPE_PAYMENT_METHOD.lower()  # not raw card number
```

### Async tests
```python
# asyncio_mode = "auto" in pyproject.toml — just write async def
async def test_telegram_handler(mock_telegram_update, mock_telegram_context):
    await handle_message(mock_telegram_update, mock_telegram_context)
    mock_telegram_update.message.reply_text.assert_called_once()
```

## Running Tests Locally
```bash
# Fast: unit tests only
pytest tests/unit/ -q

# Full suite with coverage report
pytest tests/ --cov=src/blind_assistant --cov-report=term-missing

# Security modules (must hit 100%)
pytest tests/unit/security/ tests/unit/test_encryption.py \
  --cov=src/blind_assistant/security \
  --cov-fail-under=100
```

## What the Loop Must Do (for agents)

After EVERY `backend-developer` or `integration-engineer` task:
1. Call `test-engineer` with the list of new/modified `src/` files
2. `test-engineer` writes missing tests, runs coverage, reports pass/fail
3. Only mark the task as complete when `pytest` exits 0 and coverage ≥ 80%
4. If tests fail: fix `src/` — do NOT modify the test assertions
