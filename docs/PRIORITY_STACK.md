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

## Current Stack (Phase 2 — Core Build Sprint)

| Priority | Item | Source | Added |
|----------|------|---------|-------|
| P1 | **Native app voice E2E demo** *(last remaining P1 — backend server now exists)*: voice input → STT → orchestrator → TTS audio reply; test via Desktop CLI (voice_local.py); wire all pieces end-to-end; ISSUE-007 | ISSUE-007 updated, Phase 2 gate | 2026-03-17 |
| P1 | **React Native skeleton** *(now unblocked by arch decision)*: create `clients/` dir; scaffold Expo project with REST client pointing to localhost:8000; Hello World on Android emulator with TalkBack; ISSUE-009 resolved, next step is implementation | ISSUE-009 follow-up | 2026-03-17 |
| P2 | Integration test: voice input → Whisper STT → orchestrator → TTS → reply (via CLI or API, not Telegram) | Phase 2 gate | 2026-03-17 |
| P2 | Voice installer: complete voice-guided setup from fresh Python install | ARCHITECTURE.md Task 5 | 2026-03-17 |
| P2 | Web app: accessible web interface at blind-assistant.org (WCAG 2.1 AA; NVDA+Chrome, VoiceOver+Safari, TalkBack+Chrome) | Founder scope expansion | 2026-03-17 |
| P2 | Per-platform E2E test suite structure: create tests/e2e/platforms/ with Android/iOS/Web/Desktop dirs | Founder scope expansion | 2026-03-17 |
| P2 | Cross-platform accessibility audit: run all 5 platform agents on current codebase | Founder scope expansion | 2026-03-17 |
| P3 | Android app: native Android app (TalkBack); architecture per ARCH DECISION above | Founder scope expansion | 2026-03-17 |
| P3 | iOS app: native iPhone/iPad app (VoiceOver); architecture per ARCH DECISION above | Founder scope expansion | 2026-03-17 |
| P3 | Device simulation CI: Android emulator (AVD) + Playwright for web E2E in CI | device-simulator agent | 2026-03-17 |
| P3 | Education website (learn.blind-assistant.org): audio-primary; NVDA+Chrome; zero mouse | education-website-designer | 2026-03-17 |
| P3 | Voice Activity Detection (VAD) for voice_local.py (replaces fixed recording duration) | ISSUE-002 | 2026-03-17 |
| P3 | PIL ImageGrab Playwright fallback for headless/server environments | ISSUE-003 | 2026-03-17 |
| P3 | Add Optional[Callable] type annotations to response_callback params in orchestrator | ISSUE-004 | 2026-03-17 |
| P3 | MCP memory server integration (cross-session user preferences) | INTEGRATION_MAP.md | 2026-03-17 |
| P3 | Set up CHANGELOG.md and populate ROADMAP.md | open source | 2026-03-17 |
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
