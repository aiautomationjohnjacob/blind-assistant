# Autonomous Cycle State

> This file is the persistent brain of the autonomous loop.
> Every cycle reads this, does work, then updates it before committing.
> If the AI crashes or restarts, it reads this file first to reorient.

## SCOPE EXPANSION — [REVIEWED: Cycle 4 — findings logged to OPEN_ISSUES.md] (added 2026-03-17 by founder)

Major product scope expansion. The loop MUST be aware of these changes:

**Four client platforms** (not just a Python CLI):
1. Android native app (TalkBack)
2. iPhone/iPad native app (VoiceOver)
3. Desktop app — Windows + macOS (NVDA / VoiceOver)
4. Web app at blind-assistant.org (NVDA+Chrome, VoiceOver+Safari, TalkBack+Chrome)
(Plus the education website: learn.blind-assistant.org)

**Architecture decision is now P1**: tech-lead must decide unified framework
(React Native / Flutter) vs native per platform BEFORE any mobile/web implementation.
**IMPORTANT**: Python stays for the backend (orchestrator, second brain, TTS/STT,
security). Python is NOT used for Android/iOS client apps — that requires a separate
tech stack decision. Client apps will talk to the Python backend via an API layer.

**Per-platform test suites**: each platform needs unit + E2E tests + device simulation.
Claude Code will run Android emulators (AVD+ADB) and iOS simulators (xcrun simctl)
to take real screenshots and interact with running apps. Playwright for web.

**10 new agents added** (see `.claude/agents/` and CLAUDE.md):
`project-inspector`, `e2e-tester`, `ios-accessibility-expert`, `android-accessibility-expert`,
`windows-accessibility-expert`, `macos-accessibility-expert`, `web-accessibility-expert`,
`device-simulator`, `documentation-steward`, `backend-security-expert`

**Telegram de-emphasized** (founder directive 2026-03-17):
- Native standalone apps (Android, iOS, Desktop, Web) are the PRIMARY interfaces
- Telegram setup requires visual configuration that blind users cannot easily complete
- Telegram demoted to secondary/super-user channel; power users can enable it optionally
- All references to "Telegram E2E demo" as a P1 have been updated to "Native voice E2E demo"

New wiring in run-cycle:
- Every 5th cycle: call `project-inspector` in STEP 3
- Every 10th cycle: call `documentation-steward` in STEP 3
- After major features: call `e2e-tester` + `device-simulator`
- For any voice/UI feature: call the relevant platform accessibility agent

**Backend server architecture** (founder directive 2026-03-17):
- All user data (second brain vault, calendar, preferences, user profile) lives on the
  **backend server** — not per-device. All clients connect to this shared backend.
- **For now**: backend runs on localhost for development/testing. The Android emulator,
  iOS simulator, and Playwright tests all connect to http://localhost:[port].
- **Later**: migrate backend to cloud (AWS/GCP/Railway/Fly.io) — the loop should NOT
  configure live cloud accounts yet. Infrastructure-as-code documents the future state.
- **Background processes on the server**: second brain vault, calendar integration, user
  profile, session context, TTS/STT pipelines — all server-side, all shared across devices.
- The server should expose endpoints for: /query, /remember, /describe, /task — one API
  that all clients call with the user's message and get a voice-ready response.

---

## Current Phase

**Phase**: 2 — Core Build Sprint
**Status**: IN PROGRESS
**Started**: 2026-03-17
**Last active**: 2026-03-17
**Cycles completed**: 5

## Phase Definitions

```
Phase 0: Foundation Setup         ✅ COMPLETE (agent network, GitHub, MCPs)
Phase 1: Discovery & Architecture  ✅ COMPLETE (all deliverables done, Cycle 1)
Phase 2: Core Build Sprint         🔄 IN PROGRESS (Cycles 2-N)
Phase 3: Blind User Testing        ⏳ Pending
Phase 4: Accessibility Hardening   ⏳ Pending
Phase 5: Polish & Community Ready  ⏳ Pending
```

## What Happens in Each Phase

### Phase 1: Discovery & Architecture
**Goal**: Define exactly what we're building and how, grounded in existing tools and real gaps.
**Agents**: gap-analyst, nonprofit-ceo, tech-lead, ethics-advisor, security-specialist
**Deliverables**:
- [x] `docs/GAP_ANALYSIS.md` — Landscape of existing AI tools; what to integrate vs build
- [x] `docs/INTEGRATION_MAP.md` — Which tools (Obsidian, Telegram, Open Interpreter, etc.)
      we integrate and how; accessibility gaps in each; our integration strategy
- [x] `docs/ARCHITECTURE.md` — Full tech stack with security architecture
- [x] `docs/USER_STORIES.md` — 10+ user stories from all blind personas
- [x] `docs/FEATURE_PRIORITY.md` — Prioritized feature list with mission justification
- [x] `docs/SECURITY_MODEL.md` — How sensitive data is handled end-to-end (from security-specialist)
- [x] `docs/ETHICS_REQUIREMENTS.md` — Full ethics requirements (bonus: added this cycle)
- [x] `src/` — Initial project scaffold (Python, async, all packages created)
- [x] Phase 1 complete: integration strategy decided, security model defined, scaffold created

### Phase 2: Core Build Sprint
**Goal**: Build the minimum product a blind user can actually try end-to-end.
**Agents**: tech-lead, code-reviewer, accessibility-reviewer, blind-user-tester, security-specialist
**Must include**:
- Screen capture + describe (AI sees and narrates the screen)
- Basic voice I/O (speak to it, it speaks back)
- One complete agentic task end-to-end: user asks for something → AI figures out what
  tools/apps are needed → installs them if missing (with user confirmation) → asks
  follow-up questions conversationally → completes the task
- Risk disclosure flow: whenever banking/payment details are requested, the spoken warning
  must fire before any details are accepted
**Phase 2 complete when**: A blind user can ask the AI to do a real-world task (e.g. order
food or book something) entirely by voice, including the app self-installing what it needs

### Phase 3: Blind User Testing (Multi-Platform)
**Goal**: All 5 blind user personas can complete core life-assistant tasks on at least 3 of 5 client platforms.
**Agents**: All 5 blind user personas, screen-observer, computer-use-tester, impact-researcher,
  ios-accessibility-expert, android-accessibility-expert, windows-accessibility-expert,
  macos-accessibility-expert, web-accessibility-expert, device-simulator
**Test scenarios must include**:
- Ask the AI what's on their screen and navigate an inaccessible app
- Order food or a household item entirely by voice (including risk-disclosure flow)
- Ask the AI to research something and take action on the result (compound task)
- Add and retrieve a note from their Second Brain by voice
- Complete setup/onboarding with zero sighted assistance
- Complete the above on at least: Android (TalkBack), iOS (VoiceOver), and Web (NVDA+Chrome)
- Device simulation: Android emulator + iOS simulator screenshots verify accessibility
**Phase 3 complete when**: No SHOWSTOPPER issues from any persona across all scenarios
  AND device-simulator captures passing screenshots for Android, iOS, and Web

### Phase 4: Accessibility Hardening (All Platforms)
**Goal**: WCAG 2.1 AA on web; native accessibility APIs on iOS/Android; NVDA/JAWS on Desktop.
**Agents**: accessibility-reviewer, privacy-guardian, ethics-advisor, security-specialist, deafblind-user,
  ios-accessibility-expert, android-accessibility-expert, windows-accessibility-expert,
  macos-accessibility-expert, web-accessibility-expert
**Phase 4 complete when**: /audit-a11y returns zero CRITICAL findings on web AND
  each platform accessibility agent signs off on their platform AND
  security-specialist signs off on financial data handling AND
  ethics-advisor approves transaction confirmation flow

### Phase 5: Polish & Community Ready
**Goal**: Onboarding works for non-technical newly blind user; grant pitch ready; community launch.
**Agents**: newly-blind-user, blind-elder-user, grant-writer, community-advocate
**Test**: Dorothy (elder persona) can: set up the app, order food, and add a note to her
Second Brain — all without sighted help and without ever asking "what do I do next?"
**Phase 5 complete when**: Dorothy passes the above test AND grant-writer produces GRANT_NARRATIVE.md

## Current Sprint (Phase 2 — Core Build Sprint)

**Sprint goal**: Build the minimum product a blind user can actually try end-to-end.

**Sprint items** (Phase 2 targets — check off as complete):
- [x] Telegram bot fully functional: receives text + voice, replies with text + voice (Cycle 1)
- [x] Whisper STT: transcribes voice messages from Telegram (Cycle 1)
- [x] TTS: ElevenLabs + pyttsx3 fallback, speed-configurable (Cycle 1)
- [x] Screen observer: "What's on my screen?" → spoken description via Claude Vision (Cycle 1)
- [x] Screen redaction: password fields and financial screens never sent to API (Cycle 1)
- [x] Second Brain MVP: add notes by voice, query notes by voice, encrypted vault (Cycle 2)
- [x] Orchestrator: intent classification → tool selection → execution pipeline (Cycle 2)
- [x] Vault passphrase prompt recovery: user can self-unlock Second Brain by voice (Cycle 3)
- [x] TTS + STT unit tests: 25 new tests covering voice pipeline (Cycle 3)
- [x] Risk disclosure flow: payment confirmation with spoken warning (Cycle 1)
- [x] **P1: Backend API server** — FastAPI HTTP server created in api_server.py; endpoints /query /remember /describe /task /profile /health; Bearer token auth; 28 tests (Cycle 4)
- [x] **P1: ARCH DECISION** — React Native + Expo chosen; documented in ARCHITECTURE.md; clients/ directory to be created in Cycle 5 (Cycle 4)
- [ ] **P1: Native voice E2E demo** — voice in → STT → orchestrator → TTS audio reply out (Desktop CLI first; NOT Telegram — Telegram is secondary/super-user only)
- [ ] Tool registry + installer: self-expanding pattern with user confirmation
- [ ] Voice installer: voice-guided setup from zero to functional
- [ ] End-to-end test: blind user asks to order food → full flow with confirmations
- [x] context.clear_sensitive(): UserContext.clear_sensitive() added (Cycle 4, 4 tests)
- [x] Make passphrase prompt timeout configurable in config.yaml (Cycle 4, 3 tests)

## Blockers

None currently. If blockers exist, they will be listed here with workarounds attempted.

## Last Cycle Summary

Cycle 4 (Phase 2 Core Build Sprint) delivered: full codebase audit (Telegram de-emphasis
corrected in main.py default + telegram_bot.py docstring), ARCH DECISION (React Native +
Expo for all client apps — documented in ARCHITECTURE.md), REST API server (api_server.py:
6 endpoints, Bearer token auth, global safe error handler, 28 tests), ISSUE-005
(context.clear_sensitive() — 4 tests), ISSUE-006 (configurable passphrase timeout — 3
tests). Total: 314 tests (was 279), all passing, no regressions. API_SERVER_TOKEN
credential key added to credentials.py.

## Known Issues / Technical Debt

- `transcribe_microphone` uses fixed duration — needs Voice Activity Detection (VAD)
- Tool implementations (doordash.py, instacart.py, etc.) are empty stubs — Phase 2 work
- `src/blind_assistant/memory/mcp_memory.py` not yet implemented — Phase 2 work
- response_callback params in orchestrator lack Optional[Callable] type annotations
- API server has no rate limiting middleware — acceptable on localhost; required before cloud deploy
- clients/ directory doesn't exist yet — React Native Expo skeleton must be created (Cycle 5)
- Voice E2E demo not yet delivered — #1 Phase 2 gate item (ISSUE-007)

## Decisions Made

| Date | Decision | Made by | Reasoning |
|------|----------|---------|-----------|
| 2026-03-17 | Python 3.11+ as primary language | tech-lead | Best AI ecosystem, async support, keyring library |
| 2026-03-17 | ~~Telegram as primary interface~~ — REVISED 2026-03-17 | Founder directive | Telegram setup is visual and inaccessible for blind users; native standalone apps are the primary interface; Telegram is secondary/super-user only |
| 2026-03-17 | Obsidian vault format (file only, no app) | tech-lead | Accessible storage without inaccessible app |
| 2026-03-17 | AES-256-GCM for vault encryption | security-specialist | Industry standard, authenticated encryption |
| 2026-03-17 | OS keychain for all credentials | security-specialist | No .env files, cross-platform, secure |
| 2026-03-17 | Risk disclosure fires every transaction | ethics-advisor + security-specialist | Never assume prior awareness |
| 2026-03-17 | Per-transaction payment confirmation | ethics-advisor | User cannot visually verify; repetition is safer |
| 2026-03-17 | All user data is server-side | Founder directive | Second brain, calendar, profile shared across all 5 clients; backend is single source of truth |
| 2026-03-17 | Backend runs on localhost during dev | Founder directive | No cloud accounts yet; all emulators connect to localhost; cloud migration is a later phase |
| 2026-03-17 | Python NOT used for mobile clients | Founder + tech analysis | Android/iOS require native or cross-platform (React Native/Flutter); Python stays for backend only |
| 2026-03-17 | React Native + Expo for all client apps | tech-lead (Cycle 4) | Native rendering = native accessibility tree; Flutter custom renderer has screen reader gaps; Expo web shares components with mobile |
| 2026-03-17 | FastAPI for REST API server | tech-lead (Cycle 4) | Async, pydantic validation, OpenAPI docs, uvicorn ASGI server; runs on localhost:8000 for dev |

## Loop Status for Next Run

**Loop was manually stopped after Cycle 4.** Loop is clean and ready for Cycle 5.
No mid-cycle state artifacts. All changes committed and pushed.

The most important work for Cycle 5:
1. **P1 Native voice E2E demo** (ISSUE-007) — wire voice_local.py → Whisper STT →
   orchestrator → TTS → speaker; write integration test; this CLOSES Phase 2.
2. **React Native skeleton** — create clients/ directory; scaffold Expo project;
   configure REST client pointing to localhost:8000; basic Hello World screen with
   ARIA labels and TalkBack-accessible layout.
3. **ISSUE-011 (new)**: Add rate limiting middleware to api_server.py before cloud deployment.
4. **ISSUE-010** (E2E test structure): tests/e2e/platforms/ already has __init__.py stubs —
   next cycle write actual Playwright web smoke test for the web client.
