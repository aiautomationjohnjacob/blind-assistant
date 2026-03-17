# Changelog

All notable changes to Blind Assistant are documented here.

Format: [Semantic Versioning](https://semver.org/). Types: `Added`, `Changed`, `Fixed`, `Security`, `Deprecated`, `Removed`.

---

## [Unreleased] — Phase 2: Core Build Sprint

### Added
- **Food ordering checkout loop** (Cycle 10): Complete conversational flow for ordering food.
  The assistant navigates to DoorDash, reads restaurant options aloud, waits for the user's
  spoken choice, navigates to the restaurant, presents menu items, adds the selected item
  to the cart, runs mandatory financial risk disclosure, and places the order. All steps use
  Claude to reason about live page content — no site-specific wrappers.
- **ConfirmationGate.wait_for_response()**: New method for collecting free-text user responses
  in multi-step conversational flows (not just yes/no).
- **Tool registry + installer** (Cycle 9): Agents can install new tools (Playwright, etc.) at
  runtime with user confirmation. Includes voice-guided tool installation.
- **BrowserTool**: Playwright wrapper for autonomous web navigation. Claude reasons about any
  web page as a human would — no site-specific code.
- **Voice recording endpoint** (Cycle 7): `/api/transcribe` accepts raw audio, transcribes via
  Whisper, returns text. Powers voice-first input on all clients.
- **Second Brain vault** (Cycles 5–6): Encrypted Obsidian-compatible markdown notes stored
  locally. Voice-queried via the orchestrator.
- **Security: financial risk disclosure** (Cycle 3): Mandatory spoken warning fires before any
  payment-adjacent action. Cannot be skipped.

### Changed
- **Telegram demoted to secondary interface** (Cycle 4 architecture decision): Native apps
  (Android, iOS, Desktop, Web) are the primary clients. Telegram remains available for power
  users who want remote command access.
- **Client framework selected** (Cycle 4): React Native + Expo for Android/iOS/Web;
  Electron/Tauri for Desktop. Python stays backend-only.

### Fixed
- **CI: ruff lint errors** (Cycle 10): 45 accumulated formatting/lint errors resolved. `ruff
  format` now runs before every CI check.
- **CI: pip-audit failure** (Cycle 10): `openai-whisper` setup.py uses `pkg_resources`
  (removed from Python 3.12+ stdlib). Fixed by installing `setuptools` in the audit step.

### Security
- Screen content containing passwords or PII is never sent to external APIs (redaction layer).
- All vault data encrypted with AES-256-GCM using a user passphrase-derived key.
- Payment card numbers never stored; Stripe tokenization planned for Phase 3.

---

## Test Coverage (Phase 2 — current)

- **482 tests** passing (465 unit, 17 E2E backend)
- **Security modules**: 100% line and branch coverage
- **Overall backend**: ≥80% coverage enforced in CI

---

*This project follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) conventions.*
