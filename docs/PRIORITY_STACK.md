# Priority Stack — Ranked Backlog

> Maintained by the orchestrator. Updated every cycle.
> The orchestrator ALWAYS works from the top of this stack.
> Items are added by gap detection, persona feedback, security audits, and user stories.
> Items are removed when completed and committed.

## How Priority is Determined

1. **P0 — BLOCKING**: Security vulnerabilities, broken builds, data loss risk
2. **P1 — SHOWSTOPPER**: A blind user persona cannot complete a core task
3. **P2 — PHASE GATE**: Required deliverable for current phase to complete
4. **P3 — KNOWN GAP**: Detected gap not yet addressed (see OPEN_ISSUES.md)
5. **P4 — IMPROVEMENT**: Enhancement that improves the product meaningfully
6. **P5 — CREATIVE**: New idea or integration opportunity worth exploring

## Current Stack (Phase 3 — Blind User Testing)

**Phase 3 goal**: All 5 blind user personas can complete core life-assistant tasks on at least 3 of 5 client platforms.

| Priority | Item | Source | Added |
|----------|------|---------|-------|
| P1 | **Verify CI integration-browser job (ISSUE-021 follow-up)**: The new 'integration-browser' CI job added in Cycle 12 must pass on the next push to confirm BrowserTool real Playwright tests work end-to-end. If CI fails, diagnose and fix before starting new features. | Cycle 12 self-assessment | 2026-03-17 |
| P2 | End-to-end food ordering demo on real device: blind user on Android (TalkBack) + iOS (VoiceOver) can say "order me food" and complete the full flow by voice. | Phase 3 sprint | 2026-03-17 |
| P2 | Voice installer: complete voice-guided setup from fresh Python install | ARCHITECTURE.md Task 5 | 2026-03-17 |
| P2 | Web app: accessible web interface at blind-assistant.org (WCAG 2.1 AA; NVDA+Chrome, VoiceOver+Safari, TalkBack+Chrome) | Founder scope expansion | 2026-03-17 |
| P3 | Android app: run npm install + expo build:android + TalkBack test on AVD | Founder scope expansion | 2026-03-17 |
| P3 | iOS app: run npm install + expo build:ios --simulator + VoiceOver test on xcrun simctl | Founder scope expansion | 2026-03-17 |
| P3 | Device simulation CI: Android emulator (AVD) + Playwright for web E2E in CI | device-simulator agent | 2026-03-17 |
| P3 | Education website (learn.blind-assistant.org): audio-primary; NVDA+Chrome; zero mouse | education-website-designer | 2026-03-17 |
| P3 | Voice Activity Detection (VAD) for voice_local.py (replaces fixed recording duration) | ISSUE-002 | 2026-03-17 |
| P3 | PIL ImageGrab Playwright fallback for headless/server environments | ISSUE-003 | 2026-03-17 |
| P3 | MCP memory server integration (cross-session user preferences) | INTEGRATION_MAP.md | 2026-03-17 |
| P3 | Populate ROADMAP.md with Phase 3-5 milestones | open source | 2026-03-17 |
| P3 | Telegram integration: secondary/super-user channel only; voice-guided Telegram setup for power users who want remote access; NOT required for primary blind user experience | cloud-architect | 2026-03-17 |

## Completed Items

| Item | Completed | Cycle # |
|------|-----------|---------|
| Agent network setup (20 agents) | 2026-03-17 | 0 |
| GitHub repo + MCP integration | 2026-03-17 | 0 |
| Autonomous loop infrastructure | 2026-03-17 | 0 |
| Product brief with synthesis vision | 2026-03-17 | 0 |
| docs/GAP_ANALYSIS.md | 2026-03-17 | 1 |
| docs/INTEGRATION_MAP.md | 2026-03-17 | 1 |
| docs/SECURITY_MODEL.md | 2026-03-17 | 1 |
| docs/ETHICS_REQUIREMENTS.md | 2026-03-17 | 1 |
| docs/ARCHITECTURE.md | 2026-03-17 | 1 |
| docs/USER_STORIES.md (21 stories, 5 personas) | 2026-03-17 | 1 |
| docs/FEATURE_PRIORITY.md | 2026-03-17 | 1 |
| src/ project scaffold (Python, 29 source files) | 2026-03-17 | 1 |
| requirements.txt (pinned dependencies) | 2026-03-17 | 1 |
| config.yaml (non-secret configuration) | 2026-03-17 | 1 |
| README.md (screen-reader-friendly, voice setup guide) | 2026-03-17 | 1 |
| .gitignore (credential and vault exclusions) | 2026-03-17 | 1 |
| tools/registry.yaml (curated tool registry) | 2026-03-17 | 1 |
| installer/install.py (voice-guided installer skeleton) | 2026-03-17 | 1 |
| Phase 1: Discovery & Architecture — COMPLETE | 2026-03-17 | 1 |
| voice_local.py (local voice interface) | 2026-03-17 | 2 |
| second_brain/query.py (voice query layer over vault) | 2026-03-17 | 2 |
| Orchestrator real intent routing (screen/note/query/general) | 2026-03-17 | 2 |
| Vault microsecond filename uniqueness fix | 2026-03-17 | 2 |
| 244 unit tests (encryption, vault, orchestrator, security) | 2026-03-17 | 2 |
| conftest.py suppress_audio ImportError fix | 2026-03-17 | 2 |
| Voice local interface stub (microphone + speaker) | 2026-03-17 | 2 |
| Unit tests: security/credentials, disclosure, encryption, vault | 2026-03-17 | 2 |
| pyproject.toml pythonpath fix (no manual PYTHONPATH needed) | 2026-03-17 | 3 |
| ISSUE-001 fix: _get_vault passphrase prompt recovery (10 tests) | 2026-03-17 | 3 |
| TTS unit tests: synthesize_speech, ElevenLabs, pyttsx3, speak_locally (14 tests) | 2026-03-17 | 3 |
| STT unit tests: transcribe_audio, singleton model, transcribe_microphone (11 tests) | 2026-03-17 | 3 |
| Total test count: 279 (was 244) | 2026-03-17 | 3 |
| ARCH DECISION (ISSUE-009): React Native + Expo for all client apps | 2026-03-17 | 4 |
| REST API server (ISSUE-008): FastAPI /query /remember /describe /task /profile /health | 2026-03-17 | 4 |
| ISSUE-005: UserContext.clear_sensitive() added (4 tests) | 2026-03-17 | 4 |
| ISSUE-006: configurable passphrase timeout from config.yaml (3 tests) | 2026-03-17 | 4 |
| Telegram de-emphasis: main.py default + telegram_bot.py docstring corrected | 2026-03-17 | 4 |
| Total test count: 314 (was 279) | 2026-03-17 | 4 |
| ISSUE-007: Voice E2E demo — 9 E2E tests, pipeline proven end-to-end | 2026-03-17 | 5 |
| Wake-word-only bug fix in voice_local.py ("assistant" alone now prompts "Yes?") | 2026-03-17 | 5 |
| 25 unit tests for VoiceLocalInterface (test_voice_local.py) | 2026-03-17 | 5 |
| React Native Expo skeleton: clients/mobile/ with MainScreen.tsx + API client | 2026-03-17 | 5 |
| 32 JS tests for API client + MainScreen accessibility (jest-expo) | 2026-03-17 | 5 |
| Multi-platform E2E test stubs (Web/Android/iOS/Desktop) per ISSUE-010 | 2026-03-17 | 5 |
| Total test count: 348 Python passed + 21 skipped; 32 JS tests (requires npm install) | 2026-03-17 | 5 |
| ISSUE-014: JS CI job ('test-js') added to ci.yml; 77 JS tests now in CI (was 32) | 2026-03-17 | 6 |
| ISSUE-013: SetupWizardScreen + useSecureStorage + app/index.tsx rewrite; 63 new JS tests | 2026-03-17 | 6 |
| ISSUE-012: Dead code wake_word_found removed from voice_local.py | 2026-03-17 | 6 |
| ISSUE-011: RateLimitMiddleware added to api_server.py; 8 new Python tests; configurable | 2026-03-17 | 6 |
| Total test count: 356 Python (347 unit + 9 E2E, 21 skipped); 77 JS tests in CI | 2026-03-17 | 6 |
| ISSUE-015: Real voice recording in MainScreen — useAudioRecorder hook + 2-press flow | 2026-03-17 | 7 |
| Backend POST /transcribe endpoint (base64 audio → Whisper STT); 7 Python tests | 2026-03-17 | 7 |
| JS API client: transcribe() method + TranscribeRequest/Response types; 7 tests | 2026-03-17 | 7 |
| ISSUE-016: importantForAccessibility="yes" added to SetupWizardScreen TextInput | 2026-03-17 | 7 |
| ISSUE-017: URL scheme validation in saveApiBaseUrl() with error message; 7 tests | 2026-03-17 | 7 |
| Total test count: 363 Python (354 unit + 9 E2E, 21 skipped); 114 JS tests | 2026-03-17 | 7 |
| Tool registry + installer (Cycle 8): 36 registry tests, 23 planner tests, ISSUE-018 /transcribe 413 limit | 2026-03-17 | 8 |
| Total test count Cycle 8: 426 Python (417 unit + 9 E2E, 21 skipped); 114 JS tests | 2026-03-17 | 8 |
| BrowserTool (Playwright wrapper): 24 unit tests; _handle_order_food: 12 unit tests; 8 E2E food ordering tests | 2026-03-17 | 9 |
| order_food/order_groceries wired to real handler (not stub); risk disclosure + 2-step confirmation in place | 2026-03-17 | 9 |
| Total test count Cycle 9: 470 Python (453 unit + 17 E2E, 21 skipped); 114 JS tests | 2026-03-17 | 9 |
| CI: 45 ruff errors resolved; pip-audit openai-whisper setuptools fix; CI green | 2026-03-17 | 10 |
| Food ordering checkout loop: 11-step conversational flow; 5 Claude helpers; 12 new unit tests; 4 E2E updated | 2026-03-17 | 10 |
| ConfirmationGate.wait_for_response() added (5 tests) | 2026-03-17 | 10 |
| Documentation: README.md updated (Telegram demoted), CHANGELOG.md created | 2026-03-17 | 10 |
| **PHASE 2 COMPLETE** — food ordering by voice end-to-end milestone reached | 2026-03-17 | 10 |
| Total test count Cycle 10: 482 Python (465 unit + 17 E2E, 21 skipped); 114 JS tests | 2026-03-17 | 10 |
| a11y: VoiceOver hint fix (7 "Double-tap" → outcome-first accessibilityHints) | 2026-03-17 | 11 |
| a11y: haptic recording cue (Medium on start, Light on stop) + 3 new tests | 2026-03-17 | 11 |
| a11y: importantForAccessibility="no-hide-descendants" → "yes" on SetupWizardScreen progress Text | 2026-03-17 | 11 |
| ISSUE-004: ResponseCallback type alias + 9 annotated method signatures in orchestrator.py | 2026-03-17 | 11 |
| Cross-platform accessibility audit (code-level): VoiceOver/TalkBack issues found + fixed | 2026-03-17 | 11 |
| Total test count Cycle 11: 465 Python (unchanged); 117 JS tests (was 114, +3 haptic tests) | 2026-03-17 | 11 |
| ISSUE-021: 11 real Playwright integration tests in tests/integration/test_browser_tool_real.py; CI job 'integration-browser' added | 2026-03-17 | 12 |
| ISSUE-020: "Double-tap to activate" platform hint removed from MainScreen.tsx; Platform import + platformHint style removed | 2026-03-17 | 12 |
| Total test count Cycle 12: 482 Python (unchanged); 117 JS (unchanged); +11 integration tests (skip locally) | 2026-03-17 | 12 |
