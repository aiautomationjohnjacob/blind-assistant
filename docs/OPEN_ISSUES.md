# Open Issues — Living Gap Tracker

> Every gap detected by the orchestrator, agents, or gap scans goes here.
> Items stay here until fixed and verified. The orchestrator reads this every cycle.
> Format: [ID] [severity] [category] description — detected by — date

## Severity Levels
- **CRITICAL**: Security, data loss, or complete feature failure
- **HIGH**: Blind user showstopper or major usability failure
- **MEDIUM**: Significant gap or degraded experience
- **LOW**: Minor gap, enhancement, or nice-to-have

## Open Issues

### ISSUE-001: Silent vault failure when keychain has no key
**Severity**: HIGH
**Category**: ux, accessibility
**Detected by**: code-reviewer, ethics-advisor (Cycle 2 review)
**Detected**: 2026-03-17
**Description**: `Orchestrator._get_vault()` returns None silently if the vault key is not
in the OS keychain. The user gets a generic message with no path forward. A blind user
who hasn't stored their key in the keychain has no voice-accessible recovery.
**Impact**: Dorothy (elder) and Alex (newly blind) cannot use Second Brain after a fresh
session if they didn't store vault key in keychain during setup.
**Proposed fix**: When `_get_vault` returns None, speak a passphrase prompt, collect
via active interface, derive the key, and continue. Add
`unlock_vault_with_prompt(context, response_callback)` to orchestrator.
**Status**: RESOLVED
**Resolved in**: Cycle 3 — `_get_vault` now prompts for passphrase via response_callback,
registers confirmation gate session before prompt, caches passphrase in context for the
session, derives key from passphrase+salt, and speaks a clear error if the passphrase is
wrong. 10 unit tests added covering all paths.

### ISSUE-002: Fixed-duration microphone recording
**Severity**: MEDIUM
**Category**: accessibility, ux
**Detected by**: accessibility-reviewer (Cycle 2 review)
**Detected**: 2026-03-17
**Description**: `voice_local.py` records for a fixed 8 seconds. Elderly users may be
cut off; fast users waste time waiting.
**Impact**: Dorothy (elder) cut off; Marcus (power user) slowed.
**Proposed fix**: Implement Voice Activity Detection (silero-vad or webrtcvad).
Fall back to fixed duration if VAD unavailable.
**Status**: OPEN

### ISSUE-003: PIL ImageGrab fails on headless servers
**Severity**: MEDIUM
**Category**: architecture, integration
**Detected by**: orchestrator self-assessment (Cycle 2)
**Detected**: 2026-03-17
**Description**: `screen_observer.py` uses `PIL.ImageGrab` which requires a display.
On headless servers or Telegram webhook deployments, this fails silently.
**Impact**: "What's on my screen?" command unavailable in cloud/server mode.
**Proposed fix**: Add Playwright screenshot as primary capture; fall back to PIL for
local mode. Handle ImportError with clear user message.
**Status**: OPEN

---

## Issue Template

```
### ISSUE-[N]: [Short title]
**Severity**: CRITICAL / HIGH / MEDIUM / LOW
**Category**: security | accessibility | ux | architecture | testing | integration
**Detected by**: [agent name or scan type]
**Detected**: [date]
**Description**: [What the gap is]
**Impact**: [Who is affected and how]
**Proposed fix**: [How to address it]
**Status**: OPEN / IN PROGRESS / BLOCKED / RESOLVED
**Resolved in**: [commit hash or cycle #]
```

---

### ISSUE-004: Missing type annotations on response_callback parameters
**Severity**: LOW
**Category**: testing, architecture
**Detected by**: Cycle 3 self-assessment
**Detected**: 2026-03-17
**Description**: Several orchestrator methods have `response_callback=None` parameters
with no type annotation. Should be typed as `Optional[Callable[[str], Awaitable[None]]]`.
**Impact**: Type checker cannot catch missing callbacks; harder for contributors to
understand the interface.
**Proposed fix**: Add proper type annotations to all response_callback parameters.
**Status**: OPEN

### ISSUE-005: Session context has no clear_sensitive() method
**Severity**: MEDIUM
**Category**: security
**Detected by**: security-specialist (Cycle 3 review)
**Detected**: 2026-03-17
**Description**: The vault passphrase is cached in `context._vault_passphrase` as a
plain string for session duration. When the session ends, this is never explicitly
zeroed out. While OS memory isolation prevents other processes reading it, explicit
zeroing is defense-in-depth.
**Impact**: Passphrase remains in heap memory until garbage collected after session ends.
**Proposed fix**: Add `context.clear_sensitive()` method that sets `_vault_passphrase = None`
and call it in session teardown paths.
**Status**: RESOLVED
**Resolved in**: Cycle 4 — `UserContext.clear_sensitive()` added to orchestrator.py;
4 unit tests added in test_orchestrator.py covering clearing, idempotency, no-op when
nothing cached, and non-interference with other fields.

### ISSUE-006: Passphrase prompt timeout is hardcoded at 120 seconds
**Severity**: LOW
**Category**: accessibility, ux
**Detected by**: accessibility-reviewer (Cycle 3 review)
**Detected**: 2026-03-17
**Description**: `_collect_vault_passphrase` times out after 120 seconds, hardcoded.
Dorothy (elder) may need more time; Marcus (power user) might want less.
**Impact**: Poor fit for users on either end of the speed spectrum.
**Proposed fix**: Read from `config.yaml voice.prompt_timeout_seconds` with default 120.
**Status**: RESOLVED
**Resolved in**: Cycle 4 — `_collect_vault_passphrase` now reads
`config.get("voice", {}).get("prompt_timeout_seconds", 120)`. 3 tests added in
test_orchestrator.py covering configured value, default value, and early-timeout path.

### ISSUE-007: Native voice E2E demo not yet delivered
**Severity**: HIGH
**Category**: integration, architecture
**Detected by**: Phase 2 gate review (Cycle 3); updated by founder directive 2026-03-17
**Detected**: 2026-03-17
**Description**: A real user still cannot interact with the assistant end-to-end through
a native interface. All individual pieces exist (STT, TTS, orchestrator) but they have
not been wired together and tested on real hardware.
**Note (2026-03-17 founder update)**: Telegram is NOT the target for this demo. Native
standalone apps are the primary interface. Telegram requires visual setup that blind users
cannot complete independently — it is a secondary/super-user channel only. The E2E demo
should be via the Desktop CLI (voice in → TTS audio out), which is the most accessible
and requires zero external accounts to test.
**Impact**: Phase 2 is not complete. The "product exists" milestone is not met.
**Proposed fix**: Wire Desktop CLI → microphone → Whisper STT → orchestrator → TTS →
speaker output. Test on real hardware. Telegram integration can follow later as an
optional super-user feature.
**Status**: RESOLVED
**Resolved in**: Cycle 5 — 9 E2E tests in tests/e2e/core/test_voice_pipeline.py verify
the full pipeline: voice input → STT → orchestrator → TTS → speaker. Accessibility
assertion added (no visual-only language in responses). API server HTTP round-trip tested.
Bug fix: wake-word-only utterances ("assistant" alone) now correctly prompt "Yes? How can
I help?" instead of routing empty text to the AI (commits 9fa8bf8 + dc9a5d5).

### ISSUE-008: No REST API server — all clients have no connection point
**Severity**: HIGH
**Category**: architecture, integration
**Detected by**: Founder directive (scope expansion 2026-03-17)
**Detected**: 2026-03-17
**Description**: The Python backend runs as a CLI/Telegram bot but has no HTTP server.
All 5 client apps (Android, iOS, Desktop, Web) need to connect to the backend via REST API.
Without this, no client app can function.
**Impact**: All multi-platform work is blocked until this exists.
**Proposed fix**: Add FastAPI or Flask server to `src/blind_assistant/interfaces/api_server.py`.
Expose: `POST /query`, `POST /remember`, `POST /describe`, `POST /task`, `GET /profile`.
Run on localhost:8000 for development; behind auth for production.
**Status**: RESOLVED
**Resolved in**: Cycle 4 — `src/blind_assistant/interfaces/api_server.py` created with
FastAPI. Endpoints: GET /health (no auth), POST /query, POST /remember, POST /describe,
POST /task, GET /profile. Bearer token auth via OS keychain. Global safe error handler.
CORS middleware. Per-request preference overrides. 28 unit tests, all passing.
Added to main.py behind --api flag. Credentials: API_SERVER_TOKEN added to credentials.py.

### ISSUE-009: No architecture decision on client-app framework
**Severity**: HIGH
**Category**: architecture
**Detected by**: Founder directive (scope expansion 2026-03-17)
**Detected**: 2026-03-17
**Description**: Android and iOS apps are required but no decision has been made on whether
to use React Native, Flutter, or native (Swift/Kotlin). Building the wrong stack wastes
significant effort. Python is NOT appropriate for Android/iOS clients.
**Impact**: All Android/iOS implementation is blocked until this is decided.
**Proposed fix**: Use tech-lead + gap-analyst to evaluate React Native vs Flutter vs native
specifically on: (1) TalkBack/VoiceOver accessibility quality, (2) development speed,
(3) ability to call the Python REST backend. Document decision in ARCHITECTURE.md and
CYCLE_STATE.md Decisions Made table.
**Status**: RESOLVED
**Resolved in**: Cycle 4 — Decision: React Native + Expo. Documented in
ARCHITECTURE.md under '## Client App Framework Decision'. Key rationale: React Native
renders to native views (native a11y tree), Flutter uses custom rendering engine with
a parallel semantic tree — unacceptable for blind-user-first product. Client code will
live in `clients/` directory. Android and iOS share one codebase. Expo Web for the
web app. Electron/Tauri for Desktop (deferred to Phase 3).

### ISSUE-010: No multi-platform E2E test infrastructure
**Severity**: MEDIUM
**Category**: testing, architecture
**Detected by**: Founder directive (scope expansion 2026-03-17)
**Detected**: 2026-03-17
**Description**: `tests/e2e/platforms/` directory structure doesn't exist. Web E2E tests
(Playwright), Android emulator tests (ADB), iOS simulator tests (xcrun simctl) have no
home and no scaffolding.
**Impact**: Cannot verify any client app works end-to-end. CI web E2E job skips (no tests).
**Proposed fix**: Create `tests/e2e/platforms/{web,android,ios,desktop}/` directories with
placeholder files. Add Playwright dependency. Wire the first web smoke test.
**Status**: OPEN

### ISSUE-011: API server has no rate limiting
**Severity**: MEDIUM
**Category**: security, architecture
**Detected by**: security-specialist (Cycle 4 review)
**Detected**: 2026-03-17
**Description**: `api_server.py` has no rate limiting middleware.
**Status**: RESOLVED
**Resolved in**: Cycle 6 — RateLimitMiddleware added to api_server.py (sliding window,
defaultdict(deque), no new dependency). 60 req/min auth endpoints, 120 req/min /health,
both configurable via config.yaml api_server.rate_limit_per_minute. 8 unit tests added.

### ISSUE-012: Dead code — wake_word_found variable in voice_local.py
**Severity**: LOW
**Category**: testing, architecture
**Detected by**: Cycle 5 code-reviewer
**Detected**: 2026-03-17
**Description**: The `wake_word_found` boolean was declared but never read.
**Status**: RESOLVED
**Resolved in**: Cycle 6 — two lines removed from voice_local.py. All 25 voice_local
unit tests continue to pass.

### ISSUE-013: Mobile app has no bearer token — first-run flow not implemented
**Severity**: MEDIUM
**Category**: ux, accessibility
**Detected by**: Cycle 5 self-assessment
**Detected**: 2026-03-17
**Description**: `clients/mobile/app/index.tsx` sets `BEARER_TOKEN = null`, meaning
the React Native app cannot authenticate against the API server. A blind user who
launches the app for the first time has no way to complete setup.
**Impact**: The React Native app cannot make authenticated API calls until setup is done.
**Proposed fix**: Implement voice-guided first-run setup wizard that asks the user for
their API token (generated by the backend setup wizard), stores it in
`expo-secure-store`, and loads it at startup. This is the mobile equivalent of the
Python `installer/install.py` setup wizard.
**Status**: OPEN

### ISSUE-014: clients/mobile/ JS tests not running in CI
**Severity**: MEDIUM
**Category**: testing, ci
**Detected by**: Cycle 5 self-assessment
**Detected**: 2026-03-17
**Description**: `clients/mobile/` has 32 Jest tests (19 for api.ts, 13 for MainScreen.tsx)
but no CI job runs them. The `.github/workflows/ci.yml` only runs Python tests. The npm
install and jest run must be added to CI.
**Impact**: JS test regressions will go undetected.
**Proposed fix**: Add `npm ci && npm test` step to CI for `clients/mobile/`.
**Status**: OPEN

---

## Resolved Issues

### ISSUE-001 — RESOLVED (Cycle 3)
Silent vault failure when keychain has no key. Fixed in `src/blind_assistant/core/orchestrator.py`
`_get_vault()`: now prompts user for passphrase via response_callback when keychain is empty,
derives key from passphrase+salt, caches in session context, offers to store in keychain.
10 unit tests added in `tests/unit/test_vault_passphrase_prompt.py`.

*(Previously open issues moved here when fixed)*
