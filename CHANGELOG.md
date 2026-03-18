# Changelog

All notable changes to Blind Assistant are documented here.

Format: [Semantic Versioning](https://semver.org/). Types: `Added`, `Changed`, `Fixed`, `Security`, `Deprecated`, `Removed`.

---

## [Unreleased] — Phase 4: Accessibility Hardening

### Added
- **Skip link in Expo web export** (Cycle 30): Created `clients/mobile/public/index.html`
  — a custom Expo HTML template that adds a skip-to-main-content link as the first focusable
  element. WCAG 2.4.1 Bypass Blocks (Level A). NVDA+Chrome users can Tab from the address
  bar and immediately land on the skip link; activating it jumps to `#main-content`.
  Also wraps the React root in `<div role="main">` for landmark navigation (D key in NVDA).
- **Web structure E2E tests** (Cycle 30): 5 new web E2E tests in `test_main_screen_chromium.py`
  (`TestPageStructure`): skip link is first focusable element, skip link target exists,
  main landmark is present, heading structure present, headings have accessible labels.
  Total web E2E tests: 33 (was 26 runnable + the 7 new tests + structural class additions).
- **SetupWizardScreen token step live region** (Cycle 30): `accessibilityLiveRegion="polite"`
  added to the instructions Text in the token-entry step. Previously this step was the only
  step without a live region — VoiceOver would not auto-announce the instructions when
  the screen transitioned from welcome → token. 1 new JS test; 128 JS total.

### Fixed
- **VoiceOver live region on View (ISSUE-036)** (Cycle 29): `accessibilityLiveRegion` was
  placed on `<View>` containers in MainScreen.tsx. iOS VoiceOver silently ignores live regions
  on View — they must be on `<Text>` nodes. Fixed transcript and response displays. 6 new
  JS tests added.
- **Web E2E tests silently passing despite failures (ISSUE-034)** (Cycle 29): All 26 web E2E
  tests were written as `async def` using the sync pytest-playwright `page` fixture. This
  created a RuntimeError that was swallowed, making all tests appear to pass with 0 assertions.
  Converted all 26 tests to `def` (sync). Fixed CI `pipefail` bug where `| tee` discarded
  pytest exit codes. All 26 tests now run and assert correctly.
- **axe-core CDN dependency (ISSUE-035)** (Cycle 29): axe-core was injected from cdnjs CDN.
  Committed `axe.min.js` (4.9.1, 555KB) locally; `page.add_script_tag(path=...)` eliminates
  the network dependency in CI. CDN failures now cannot cause false test passes.
- **`accessibilityRole="text"` on web (ISSUE-033)** (Cycle 28): react-native-web maps
  `accessibilityRole="text"` to `role="text"` — not a valid WAI-ARIA role, which causes
  axe-core violations and confuses screen readers. Fixed with `Platform.OS === "web" ?
  undefined : "text"` guard across 10 occurrences in MainScreen.tsx and SetupWizardScreen.tsx.
- **WCAG axe-core CI gate** (Cycle 28): New `a11y-audit` job in ci.yml builds Expo web,
  serves it on :19006, and runs `test_wcag_axe_audit.py`. Fails CI on any CRITICAL WCAG
  violation. Audits: full WCAG 2.1 AA, colour-contrast, interactive element naming, ARIA roles.
  axe.min.js bundled locally; no CDN dependency.

---

## [Phase 3 Complete] — Phase 3: Blind User Testing

### Added
- **Android TalkBack E2E tests** (Cycle 19): Full test suite for Android TalkBack accessibility.
  ADBClient wrapper interacts with an Android emulator or real device. Tests verify content
  descriptions, touch target sizes (44dp minimum), TalkBack focus navigation, the risk
  disclosure flow, and confirmation prompts. Runs in CI on release tags via the e2e-android job.
- **iOS VoiceOver E2E tests** (Cycle 19): Full test suite for iOS VoiceOver. SimctlClient
  wrapper interacts with the iOS Simulator via xcrun simctl. Tests guard against "Double-tap to..."
  hint regression (fixed in Cycle 11), verify visual-only language is absent, and check risk
  disclosure and live region announcements. Runs on macOS CI runners via ios-e2e.yml.
- **Web staging deployment** (Cycle 18): netlify.toml and deploy-staging.yml automate web app
  deployment to Netlify on every push to main. Requires NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID
  GitHub secrets (one-time operator setup — see README).
- **Web E2E accessibility tests** (Cycles 15, 18): 22 Playwright tests verify WCAG 2.1 AA
  compliance for the web app: keyboard navigation, ARIA labels, aria-live status announcements,
  focus management, no visual-only instructions, correct language attribute, and page title.
  Tests cover both the main screen and the food ordering flow.
- **Voice installer: native app priority** (Cycle 17): Setup wizard now presents the native app
  (Android/iOS) as Step 1 and Telegram as optional Step 5. Server address is auto-discovered
  via local network socket so mobile devices can connect without manual IP entry.
- **Unit tests for previously uncovered modules** (Cycle 16): 118 new tests covering Telegram
  bot, second brain query, screen redaction, and screen observer.
- **Live Playwright integration tests** (Cycle 12): 11 real browser integration tests verify
  food ordering end-to-end with a real browser. Auto-skip when system dependencies are absent.
- **Mobile app setup wizard** (Cycle 6): SetupWizardScreen walks a new user through server
  configuration entirely by voice using Expo SecureStore.
- **Real voice recording on mobile** (Cycle 7): 2-press voice recording in the mobile app.
  POST /transcribe endpoint transcribes audio via Whisper and returns text.
- **API rate limiting** (Cycle 6): RateLimitMiddleware (configurable window + limit).

### Changed
- **VoiceOver accessibility hints** (Cycle 11): All 7 hints changed from "Double-tap to..."
  to outcome-first language e.g. "Starts recording your message."
- **Haptic feedback on voice recording** (Cycle 11): Medium haptic on start, Light on stop.
- **Web app CSP** (Cycle 18): connect-src restricted to api.blind-assistant.org in production.

### Fixed
- **CI fully green after security updates** (Cycle 14): cryptography, Pillow, starlette, and
  fastapi upgraded to patch 11 CVEs. All 7 CI jobs green.
- **CI: 56 mypy type errors** (Cycle 13): Type annotations corrected across 7 source files.
- **CI: ruff lint errors** (Cycles 10, 16): Accumulated formatting errors resolved.
- **CI: pip-audit failure** (Cycle 10): openai-whisper requires setuptools on Python 3.12+.
- **CI path bug for Android E2E** (Cycle 19): e2e-android was looking in tests/e2e/android/;
  corrected to tests/e2e/platforms/android/.
- **Expo web export** (Cycle 15): App.tsx shim enables `npx expo export --platform web`.

### Security
- Screen content containing passwords or PII is never sent to external APIs.
- All vault data encrypted with AES-256-GCM using a user passphrase-derived key.
- Payment card numbers never stored; Stripe tokenization planned for Phase 4.
- 11 CVEs patched in Cycle 14 (cryptography, Pillow, starlette, fastapi).

---

## [Unreleased — Phase 2 Complete] — Core Build Sprint

### Added
- **Food ordering checkout loop** (Cycle 10): Complete 11-step conversational flow for ordering
  food by voice. Claude navigates DoorDash, reads options aloud, waits for spoken choice,
  reads the menu, adds items, runs mandatory financial risk disclosure, and places the order.
  No site-specific wrappers — Claude reasons about live page content.
- **ConfirmationGate.wait_for_response()**: Collects free-text user responses in multi-step flows.
- **Tool registry + installer** (Cycle 9): Runtime tool installation with user confirmation.
  Curated registry prevents supply-chain attacks.
- **BrowserTool**: Playwright wrapper for autonomous web navigation.
- **Voice recording endpoint** (Cycle 7): POST /transcribe accepts raw audio, returns text.
- **Second Brain vault** (Cycles 5–6): Encrypted Obsidian-compatible markdown notes stored
  locally. Voice-queried. Passphrase prompt recovery added (Cycle 3).
- **Security: financial risk disclosure** (Cycle 3): Mandatory spoken warning before any
  payment-adjacent action. Cannot be skipped.
- **Backend REST API server** (Cycle 4): FastAPI at localhost:8000. Endpoints: /query,
  /remember, /describe, /task, /profile, /health. Bearer token auth. Rate limiting.
- **React Native + Expo mobile skeleton** (Cycle 5): clients/mobile/ with MainScreen.tsx.

### Changed
- **Telegram demoted to secondary interface** (Cycle 4): Native apps are primary.
- **Client framework selected** (Cycle 4): React Native + Expo for Android/iOS/Web.

### Fixed
- Wake-word-only input bug: "assistant" alone now correctly prompts "Yes?" (Cycle 5).
- Vault microsecond filename uniqueness (Cycle 2).

### Security
- OS keychain for all credentials (never .env files in production).
- AES-256-GCM vault encryption; key derived from passphrase + per-vault salt.

---

## Test Coverage (Phase 3 — current)

- **641 Python unit tests** passing (all modules)
- **25 platform E2E tests** (Android TalkBack + iOS VoiceOver — run on release tags)
- **22 web E2E tests** (Playwright, Chromium + Firefox)
- **117 JS tests** (Jest + jest-expo)
- **11 integration tests** (Playwright browser — skip locally, run in CI)
- **Security modules**: 100% line and branch coverage
- **Overall backend**: ≥80% coverage enforced in CI

---

*This project follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) conventions.*
