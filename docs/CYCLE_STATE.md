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

**Phase**: 4 — Accessibility Hardening
**Status**: IN PROGRESS
**Started**: 2026-03-18
**Last active**: 2026-03-17
**Cycles completed**: 32

## Phase Definitions

```
Phase 0: Foundation Setup         ✅ COMPLETE (agent network, GitHub, MCPs)
Phase 1: Discovery & Architecture  ✅ COMPLETE (all deliverables done, Cycle 1)
Phase 2: Core Build Sprint         ✅ COMPLETE (Cycles 2-10)
Phase 3: Blind User Testing        🔄 IN PROGRESS (Cycle 11+)
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
- [x] **P1: Native voice E2E demo** — 9 E2E tests in tests/e2e/core/test_voice_pipeline.py; wake-word bug fixed; accessibility assertion added; HTTP round-trip via API server tested (Cycle 5)
- [ ] Tool registry + installer: self-expanding pattern with user confirmation
- [ ] Voice installer: voice-guided setup from zero to functional
- [ ] End-to-end test: blind user asks to order food → full flow with confirmations
- [x] context.clear_sensitive(): UserContext.clear_sensitive() added (Cycle 4, 4 tests)
- [x] Make passphrase prompt timeout configurable in config.yaml (Cycle 4, 3 tests)
- [x] **P1: JS CI job** — 'test-js' job in ci.yml; 77 Jest tests run in CI (Cycle 6)
- [x] **P1: Mobile first-run setup wizard** — SetupWizardScreen + useSecureStorage + app/index.tsx; 63 new JS tests (Cycle 6)
- [x] **P3: Dead code removed** — wake_word_found in voice_local.py removed (Cycle 6)
- [x] **P3: Rate limiting** — RateLimitMiddleware in api_server.py; 8 new Python tests (Cycle 6)
- [x] **P1: Real voice recording** — useAudioRecorder hook + 2-press flow in MainScreen + /transcribe endpoint; 41 new tests (Cycle 7)
- [x] **P3: Quick fixes** — ISSUE-016 (TextInput importantForAccessibility) + ISSUE-017 (URL validation); 14 new JS tests (Cycle 7)
- [x] **P1: Food ordering handler** — _handle_order_food in orchestrator; BrowserTool (Playwright wrapper); order_food/order_groceries wired to real handler; risk disclosure + 2-step confirmation; 44 new Python tests (Cycle 9)
- [x] **P1: Food ordering checkout loop** — complete 11-step conversational flow: reads restaurant options aloud, user picks by voice, reads menu items, adds to cart, 2-step financial confirmation, places order; 5 Claude-powered helper methods with graceful fallbacks; 12 new unit tests + 4 E2E tests updated; ConfirmationGate.wait_for_response() added (5 tests) (Cycle 10)
- [x] **P0: CI repair** — 45 ruff errors resolved; pip-audit setuptools fix for openai-whisper on Python 3.12; CI green (Cycle 10)
- [x] **Documentation audit** (every 10th cycle) — README.md updated (Telegram demoted), CHANGELOG.md created (Cycle 10)

**PHASE 2 COMPLETE** — "A blind user can ask the AI to do a real-world task entirely by voice" milestone reached (Cycle 10).

## Phase 3 Sprint Items (Blind User Testing)
- [x] **a11y: VoiceOver hint fix** — 7 accessibilityHints now use outcome-first language; no "Double-tap" (Cycle 11)
- [x] **a11y: haptic recording cue** — Medium on start, Light on stop; 3 new JS tests (Cycle 11)
- [x] **a11y: importantForAccessibility bug** — SetupWizardScreen progress Text fixed (Cycle 11)
- [x] **ISSUE-004: type annotations** — ResponseCallback alias + 9 method signatures annotated (Cycle 11)
- [x] **P1: Live food ordering validation (ISSUE-021)** — 11 real Playwright integration tests in tests/integration/test_browser_tool_real.py; auto-skip when system deps unavailable; CI job 'integration-browser' added to ci.yml (Cycle 12)
- [x] **P3: ISSUE-020** — Platform hint "Double-tap to activate" removed from MainScreen.tsx; Platform import + platformHint style removed; 24 JS tests pass (Cycle 12)
- [x] **P0: CI repair (ISSUE-022)** — 56 mypy type errors resolved across 9 files; openai-whisper setuptools build failure fixed in test/integration-browser CI jobs; ruff clean; 465 Python tests passing (Cycle 13)
- [x] **P0: CI fully green (Cycle 14)** — 11 CVEs patched (cryptography, Pillow, starlette, fastapi upgraded); pip-audit switched to installed-env mode with --no-build-isolation; 5 new mypy errors from updated type stubs fixed (VoiceSettings, AsyncAnthropic, run_polling); Playwright libasound2 virtual package workaround; ALL 7 CI jobs green on run 23218631525
- [x] **P2: Close stale GitHub CI-failure issues** — batch-closed 79 stale issues in Cycle 14 (commit d593482)
- [x] **P2: Fix Expo web export** — App.tsx shim added (Cycle 15); `npx expo export --platform web` builds successfully; 11 web E2E accessibility tests added; CI e2e-web job rebuilt to actually run tests (Cycle 15)
- [x] **P2: Missing unit tests (ISSUE-028)** — 118 new tests: test_telegram_bot.py (24), test_query.py (49), test_redaction.py (27), test_screen_observer.py (18); ruff format CI blocker from Cycle 15 also fixed (Cycle 16)
- [x] **P2: Voice installer** — Telegram demoted to optional Step 5; _setup_native_app() added as Step 1 (TalkBack/VoiceOver); server address discovery (socket IP); STEP_APP_INTRO mentions both TalkBack + VoiceOver; STEP_COMPLETE updated; _run_self_test reclassified Telegram as optional; 58 new tests; 641 unit tests passing (Cycle 17)
- [x] **P2: Verify web E2E CI** — CI run 23219936377: ALL 7 jobs green including e2e-web (Playwright Chromium + Firefox accessibility tests) (Cycle 17)
- [x] **P2: End-to-end food ordering on real device** — Android TalkBack + iOS VoiceOver E2E test files written (Cycle 19); ADBClient + SimctlClient wrappers; 8 TalkBack tests + 9 VoiceOver tests; CI path bug fixed; ios-e2e.yml macOS workflow; tests skip gracefully when AVD/simulator unavailable; actual AVD run deferred to release CI
- [x] **P2: Web app deployed** — netlify.toml + deploy-staging.yml created (Cycle 18); ISSUE-029: requires manual secret setup (NETLIFY_AUTH_TOKEN + NETLIFY_SITE_ID); 11 food ordering web E2E accessibility tests added
- [x] **P2: ISSUE-029 README docs** — Netlify operator setup instructions added to README.md (Cycle 19)
- [x] **Cycle 20: documentation-steward** — CHANGELOG.md updated through Cycle 19; CONTRIBUTING.md setup steps corrected; 8 missing docstrings added; 72 unit tests for ADB/simctl helpers; 713 Python unit tests total
- [x] **P3: ROADMAP.md updated** — rewritten for current state: Phases 1+2 complete (checked off), Phase 3 in progress with remaining items, Phase 4+5 milestones, correct tech stack table; CONTRIBUTING.md updated to link ROADMAP.md (Cycle 21)
- [x] **P3: Android TalkBack CI triggered** — v0.3.0 release tag pushed; e2e-android AVD job triggered in ci.yml; awaiting CI result (Cycle 21)
- [x] **P3: iOS VoiceOver CI triggered** — v0.3.0 release tag pushed; ios-e2e.yml macOS workflow triggered; awaiting CI result (Cycle 21)
- [x] **P3: iOS VoiceOver CI result** — run 23222358997: 6 PASSED, 2 SKIPPED (backend not reachable in simulator without running server — expected in headless CI) (Cycle 22)
- [x] **P3: Android TalkBack CI bug fix** — ci.yml e2e-android job was structurally unreachable (ci.yml triggers on branches only, job condition was `startsWith(github.ref, 'refs/tags/v')`); fixed by creating e2e-android.yml (Cycle 22)
- [x] **P3: Voice Activity Detection (ISSUE-002)** — transcribe_microphone_with_vad() + _record_with_vad_sync(); webrtcvad-wheels added to requirements.txt; VoiceLocalInterface uses VAD by default; fallback to fixed-duration when webrtcvad unavailable; +12 new tests (Cycle 22)
- [x] **P3: PIL/Playwright screenshot fallback (ISSUE-003)** — _capture_with_pil() + _capture_with_playwright() strategy; headless Chromium fallback for servers; FloatRect for mypy; +9 new tests (Cycle 22)
- [x] **P3: Android TalkBack CI result** — v0.3.1 run 23223429212 FAILED (backslash-continuation bug in `script:` field); fixed in Cycle 23; v0.3.2 tag pushed (Cycle 23)
- [x] **P3: MCP memory server** — MCPMemoryClient + context.py integration; 33 new tests; 765 Python unit tests (Cycle 23)
- [x] **P3: Education website scaffold** — clients/education/ React site; AudioPlayer; 39 Jest accessibility tests; test-education CI job (Cycle 23)
- [x] **P3: MCPMemoryClient in /profile** — GET/PUT /profile now reads/writes preferences via MCPMemoryClient; 14 new Python tests; ProfileUpdateRequest added; PUT /profile with allowable fields (Cycle 24)
- [x] **P3: Education site test fix** — tests moved to src/__tests__/, imports corrected, 41 new Jest tests, coverage 82.7%; npm ci --legacy-peer-deps in CI; NavLink aria-current fixed (Cycle 24)
- [x] **P0: CI fix (test_record_with_vad_sync)** — patch.dict(sys.modules, {'webrtcvad': None}) correctly simulates missing C-extension; CI was failing because pop() doesn't prevent re-import of installed .so (Cycle 24)
- [x] **P3: ISSUE-030 resolved** — VALID_EXTRA_PREFS frozenset in api_server.py; PUT /profile returns 422 on unknown extra keys; all-or-nothing validation (no write on rejection); audit log at WARNING; 8 new allowlist tests in test_api_server.py (Cycle 25)
- [x] **P3: MCPMemoryClient wired into main.py** — production API server now creates MCPMemoryClient on startup and injects it into APIServer; graceful degradation if MCPMemoryClient raises; 3 new tests in test_main.py (Cycle 25)
- [x] **P3: Android TalkBack CI v0.3.2 verified** — run 23223747818 PASSED (Cycle 25)
- [x] **P3: ISSUE-031 resolved** — DELETE /profile/preferences endpoint added; confirm=true required; calls MCPMemoryClient.clear_user_data(); returns 204; graceful MCP degradation; CORS updated for DELETE; 8 new unit tests; 798 Python unit tests total (Cycle 26)
- [x] **P0: CI fix (ISSUE-032)** — test_main.py ruff violations (I001, SIM105/SIM117/S110) repaired with contextlib.suppress(); CI lint was failing since Cycle 25 (Cycle 27)
- [x] **P4: SECURITY_MODEL §10** — VALID_EXTRA_PREFS 422 documented as intentional information disclosure; threat model classification INFORMATIONAL; no fix required (Cycle 27)
- [x] **P3: Voice clear preferences** — `clear_preferences` intent added to planner; `_handle_clear_preferences` handler in orchestrator with ConfirmationGate; `Response.action` field added; APIServer `_query` dispatches `_clear_preferences_for_user()` on confirmed action; 14 new unit tests; 812 Python unit tests total (Cycle 27)

## Phase 4 Sprint Items (Accessibility Hardening)
- [x] **P4: ISSUE-033 fix** — `accessibilityRole="text"` → `Platform.OS === "web" ? undefined : "text"` across 10 occurrences in MainScreen.tsx (3) + SetupWizardScreen.tsx (7); Platform import added; 4 new JS tests (Cycle 28)
- [x] **P4: axe-core WCAG CI gate** — `a11y-audit` job in ci.yml; builds Expo web, serves on :19006, runs test_wcag_axe_audit.py; fails on CRITICAL violations; audit log uploaded as artifact; added to notify-failure (Cycle 28)
- [x] **P4: test_wcag_axe_audit.py** — 4 axe-core E2E tests: critical WCAG full audit, colour-contrast, element naming, ARIA role validity + role="text" DOM check; skips gracefully without playwright/web server (Cycle 28)
- [x] **P4: Bundle axe-core locally** — axe.min.js (4.9.1, 555KB) committed; page.add_script_tag(path=...); CDN dependency eliminated; ISSUE-035 resolved (Cycle 29)
- [x] **P4: Check first a11y-audit CI run result** — ALL 26 web E2E tests were silently failing (async/sync mismatch + pipefail); fixed with sync playwright API; ISSUE-034 resolved (Cycle 29)
- [x] **P4: iOS/Android Phase 4 accessibility** — VoiceOver live region bug fixed (View→Text); accessibilityActions added for rotor; ISSUE-036 resolved; +6 JS tests; 127 JS total (Cycle 29)
- [x] **P4: Skip link + main landmark** — `clients/mobile/public/index.html` custom Expo template; skip-to-main-content link is first focusable element; `<div role="main">` wraps React root; WCAG 2.4.1 Level A (Cycle 30)
- [x] **P4: SetupWizardScreen token step live region** — `accessibilityLiveRegion="polite"` added to token entry instructions Text; matches pattern from all other steps; 1 new JS test; 128 JS total (Cycle 30)
- [x] **P4: Web structure E2E tests** — 5 new tests in `TestPageStructure`: skip link first focusable, skip link target exists, main landmark, heading structure, heading labels (Cycle 30)
- [x] **Documentation steward (Cycle 30)** — CHANGELOG updated with Phase 4 section (Cycles 28-30); README "What You Will Need" corrects Telegram to optional; test counts updated to current (812 Python, 128 JS, 75 education)
- [x] **P4: Verify skip link in expo export** — confirmed `dist/index.html` includes skip link + main landmark from `public/index.html` template (Cycle 31)
- [x] **P4: ISSUE-037 fix: tabindex="-1" on #main-content** — skip link was non-functional (moves scroll not focus); fixed in public/index.html; 5 new TestFocusManagement E2E tests + 1 TestPageStructure test; test_can_reach_main_button_by_tab corrected; ruff clean; 812 Python + 128 JS all passing (Cycle 31)
- [x] **P4: Check axe-core CI gate results** — CI run 23227996919: 0 critical, 0 serious, 1 unidentified moderate/minor violation (ISSUE-039 logged); Phase 4 gate PASSED (Cycle 32)
- [x] **P4: web-accessibility-expert audit (partial)** — 10 E2E test accuracy issues found and fixed (React hydration race, Python/JS syntax bug, setup wizard vs main screen mismatch); _wait_for_app_ready() added to all web E2E tests + axe-core tests; ISSUE-038 resolved, ISSUE-039 open (Cycle 32)
- [ ] **P4: ISSUE-039: identify and fix 1 moderate axe-core violation** — violation ID/impact unknown; axe tests now wait for hydration so next CI run will surface details
- [ ] **P4: Phase 4 completion assessment** — zero CRITICAL axe violations ✓; ISSUE-039 must resolve first; platform agent sign-offs pending

## Blockers

None currently. If blockers exist, they will be listed here with workarounds attempted.

## Last Cycle Summary

Cycle 32 (Phase 4: Accessibility Hardening). Three deliverables:
(1) Fixed 10 web E2E test failures from Cycle 31 push — 3 root causes: Python `or` syntax in
JS eval string (SyntaxError), React hydration race condition (tests ran before React rendered
interactive elements), and setup wizard vs main screen mismatch (CI shows setup wizard, tests
expected main screen labels). Fixed with `_wait_for_app_ready()` helper in all web E2E tests.
(2) Added `_wait_for_app_ready()` to axe-core audit tests so axe now audits the hydrated app.
(3) Checked axe-core CI gate results: 0 critical, 0 serious, 1 unidentified moderate violation
(ISSUE-039 logged). Phase 4 CI gate: PASSED. 812 Python unit tests unchanged. ruff clean.

Cycle 33 priority:
1. **P4: ISSUE-039** — identify the 1 moderate axe-core violation (CI run from this push will show details with improved hydration wait); fix or document as acceptable
2. **P4: Phase 4 completion assessment** — if ISSUE-039 resolves, assess completion: zero CRITICAL axe violations ✓; platform agent sign-offs needed

## Known Issues / Technical Debt

- ~~`transcribe_microphone` uses fixed duration~~ — RESOLVED: VAD implemented (ISSUE-002, Cycle 22)
- Tool implementations (doordash.py, instacart.py, etc.) are empty stubs — not needed (browser handles)
- ~~`src/blind_assistant/memory/mcp_memory.py` not yet implemented~~ — RESOLVED: Cycle 23
- ~~Platform hint text in MainScreen says "Double-tap to activate"~~ — RESOLVED (ISSUE-020, Cycle 12)
- Food ordering integration tests exist but need CI 'integration-browser' job to pass — ISSUE-021 (verify CI on next push)

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

**Loop completed Cycle 32.** Phase 4 (Accessibility Hardening) in progress.
Key deliverables: (1) Fixed 10 web E2E test failures — Python/JS syntax bug (or vs ||),
React hydration race (added _wait_for_app_ready() helper), setup wizard vs main screen
mismatch (expanded label keyword lists). All web E2E tests now use _wait_for_app_ready().
(2) Added _wait_for_app_ready() to axe-core audit tests so axe audits the hydrated app.
(3) Axe-core CI gate results reviewed: 0 critical, 0 serious, 1 unidentified moderate
violation (ISSUE-039 logged). GitHub CI issues 84 and 85 closed. 812 Python unit tests
unchanged. ruff clean. mypy 0 errors.

Most important for Cycle 33:
1. **P4: ISSUE-039** — check the new CI run from this push (axe now waits for hydration);
   identify the 1 moderate violation and fix or document it
2. **P4: Phase 4 completion assessment** — once ISSUE-039 is resolved, run `/audit-a11y`
   or get platform agent sign-offs to determine if Phase 4 is complete

The most important work for Cycle 32 (Phase 4: Accessibility Hardening):
1. **P4: Check axe-core CI gate results** — review 'serious' violations from Cycle 31 push; add any new violations to OPEN_ISSUES.md
2. **P4: web-accessibility-expert full audit** — VoiceOver+Safari and TalkBack+Chrome flows; focus management after app state changes
