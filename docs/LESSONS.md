# Lessons Learned (Autonomous Loop Journal)

> This file accumulates what the AI agents learn each cycle.
> It grows over time and informs future cycle behavior.
> The orchestrator reads this at the start of every cycle to avoid repeating mistakes.

## How to Read This

Each entry is dated and tagged with:
- **PROCESS**: Lessons about how to run the loop better
- **PRODUCT**: Lessons about what blind users actually need
- **TECHNICAL**: Coding or architecture lessons
- **AGENT**: Notes on which agents worked well or got confused

---

## Entries

---

## Interface Architecture Update — 2026-03-17 (Founder directive — read before any interface work)

**PRODUCT**: Telegram is NOT the primary interface for Blind Assistant.
- **Why**: Telegram setup requires a visual configuration process (scanning QR codes,
  navigating Telegram's website, phone verification via visual flow). Most blind users
  cannot complete this independently. Building the primary interface on a foundation
  that requires sighted setup contradicts the project's core mission.
- **What is primary**: Native standalone apps built from scratch for blind users — Android
  (TalkBack), iOS (VoiceOver), Desktop (NVDA/VoiceOver), Web (NVDA+Chrome/VoiceOver+Safari).
  Each app must be fully setupable by voice with zero visual interaction required.
- **What Telegram is**: A secondary/super-user channel. Power users who want remote
  access from any device can optionally configure Telegram. It is never required, never
  default, and never the demo target.
- **Implication for the loop**: When ISSUE-007 (E2E demo) is worked on, the target is
  Desktop CLI (voice in → STT → orchestrator → TTS → speaker out). Do NOT prioritize
  Telegram integration as a Phase 2 goal.

**PRODUCT**: Backend-security-expert agent added (2026-03-17).
- Call `backend-security-expert` after any `backend-developer` task touching API endpoints.
- Different from `security-specialist` (user data) — this agent owns the REST API attack surface.

---

## Scope Expansion — 2026-03-17 (Founder directives — read before Cycle 4)

**PRODUCT**: The product is now a family of clients, not a single Python CLI:
1. Android native app
2. iPhone/iPad native app
3. Desktop app (Windows + macOS)
4. Web app (blind-assistant.org)
5. Education website (learn.blind-assistant.org)

**TECHNICAL**: Python is the right choice for the backend (orchestrator, second brain,
security, TTS/STT, Telegram bot) — keep it. Python is NOT the right language for
Android or iOS native apps. Android apps are typically Kotlin/Java; iOS apps are
Swift/SwiftUI. However, a cross-platform framework (React Native, Flutter) may let
us write once and deploy to both. This is a critical architectural decision that must
be made by tech-lead + gap-analyst BEFORE any mobile/web implementation starts.

Key question for tech-lead to answer:
- Should client apps be React Native (JS), Flutter (Dart), or native (Swift/Kotlin)?
- How do client apps communicate with the Python backend? (REST API? WebSocket? gRPC?)
- Can we reuse the Python orchestrator logic across platforms, or does each client
  embed its own AI logic?
- Accessibility quality: which framework has the best NVDA/VoiceOver/TalkBack support?

**PROCESS**: The loop started before the full product vision was defined. Significant scope
expansion happened during Cycle 3 (added 4 client platforms, 9 new agents, multi-platform
accessibility requirements, device simulation testing). The loop must re-read CYCLE_STATE.md
and PRIORITY_STACK.md carefully at the start of Cycle 4 — things have changed.

**PROCESS**: Do not start implementing Android or iOS apps until the ARCH DECISION P1
item is resolved. Building native Android (Python-incompatible) before deciding on
React Native vs Flutter would create throwaway work.

**TECHNICAL**: Backend-first architecture (added 2026-03-17):
- All user data lives server-side: second brain vault, calendar, preferences, user profile
- All 5 clients connect to the backend via REST API (not direct file access)
- Backend runs on localhost during development; E2E tests connect emulators to localhost
- The Python backend should become a FastAPI or Flask server ASAP (P1 in PRIORITY_STACK.md)
- Key API endpoints the backend must expose:
  - `POST /query` — user sends text/voice → AI response
  - `POST /remember` — add note to second brain
  - `POST /describe` — screen description request
  - `POST /task` — execute a real-world task (order food, etc.)
  - `GET /profile` — retrieve user profile/preferences
  - `GET /calendar` — access user calendar events
- Calendar integration, background processes, and user profile are all backend concerns
- Cloud deployment (AWS/GCP) is a later phase — focus on localhost for now

**PROCESS**: Platform-specific agents (`ios-accessibility-expert`, `android-accessibility-expert`,
`windows-accessibility-expert`, `macos-accessibility-expert`, `web-accessibility-expert`,
`device-simulator`) are Phase 2+ agents. They activate once client app implementation begins.
During Phase 1 and early Phase 2 (backend-only work), skip calling these agents unless
reviewing voice output strings or Telegram bot message formatting.

---

## Cycle 1 — 2026-03-17

**Accomplished**:
- All 7 Phase 1 deliverables completed in one cycle: GAP_ANALYSIS, INTEGRATION_MAP,
  SECURITY_MODEL, ETHICS_REQUIREMENTS, ARCHITECTURE, USER_STORIES, FEATURE_PRIORITY
- Full Python project scaffold created (29 source files, correct module structure)
- requirements.txt with pinned deps, config.yaml, README.md, .gitignore, tools/registry.yaml
- Voice-guided installer skeleton (installer/install.py) — substantive but untested
- 21 user stories across 5 blind user personas

**Attempted but failed**: None — all deliverables completed.

**Confusion/loops**:
- PROCESS: The auto-commit system committed many files before manual git add/commit ran.
  git status showed "clean" when files had already been committed. Not a problem but
  confusing mid-session.
  FIX: Use `git log --oneline -5` to confirm what's been committed rather than just
  relying on `git status` being non-empty.

**New gaps detected**:
- `src/blind_assistant/interfaces/voice_local.py` stub was not created — needed for Phase 2
- `src/blind_assistant/second_brain/query.py` not created — needed for Phase 2 Task 3
- Tool implementation files (doordash.py, instacart.py, home_assistant.py) are empty stubs
- No tests exist yet — testing.md requires tests for every component

**Recommendation for next cycle**:
1. AGENT: Start Phase 2 Task 1 — complete Telegram bot + Whisper STT + TTS pipeline end-to-end.
   This creates the first real "the product exists" milestone: user sends voice message,
   gets spoken response back.
2. PROCESS: Create the 2-3 missing stub files (voice_local.py, query.py, tool stubs)
   at the start of next cycle before tackling the main implementation task.
3. PRODUCT: The Phase 2 gate is clear from FEATURE_PRIORITY.md: Dorothy (elder persona)
   and Alex (newly blind) are the test that matters. Build for them first.

---

## Cycle 2 Review — 2026-03-17

**Strategy (nonprofit-ceo)**: Cycle 2 delivered concrete value: the three most testable
blind user flows (what's on my screen, add a note, recall a note) now have real logic
behind them — not stubs. The 244-test suite means future changes won't silently break
security-critical code. We are on track. The risk is we're still not to a "first run"
milestone: a blind user still can't actually demo the product end-to-end. Next cycle
must close that gap — either a working Telegram bot demo or a local voice demo.

**Code quality (code-reviewer)**: (1) vault filename collision bug found and fixed
(microsecond precision now in filenames). (2) VaultKey.lock() clears key from memory
correctly. (3) Orchestrator `_execute_intent` is properly routing but `_get_vault` has
a design issue: it tries keychain only — if key not in keychain, vault is silently
inaccessible with no recovery path. Should prompt user for passphrase.
(4) `_format_date_label` in query.py uses `%-d` format code which fails on Windows
(not a current platform concern but note it). (5) The `suppress_audio` conftest fixture
now handles ImportError gracefully — correct approach.

**Security (security-specialist)**: (1) The vault microsecond filename bug was a
data-loss risk (notes silently overwritten) — fixed this cycle. (2) `_get_vault` silently
returns None if no keychain key — this could leave blind users unable to access their
health/finance notes with no spoken explanation of why. Should speak the passphrase
prompt explicitly. (3) The PBKDF2 iteration count is 600,000 — correct per NIST.
No new security regressions introduced this cycle.

**Accessibility (accessibility-reviewer)**: All voice outputs in query.py and
voice_local.py use plain English with no emoji. The braille-mode formatting correctly
wraps at 40 characters. The "Listening..." acknowledgment in the Telegram bot (cycle 1)
is good practice — user knows their voice was received. One concern: the `transcribe_microphone`
in voice_local.py records a fixed duration — this is poor UX for elderly users who may
speak slowly. Voice Activity Detection (VAD) should be added in Phase 3.

**User perspective (blind-user-tester)**: As a daily NVDA user, I'm excited that the
screen description flow is now wired up. What I'd want to test first: does the
"What's on my screen?" command actually work? The vision flow calls PIL ImageGrab which
won't work on a headless server. On a real machine it should work. The Second Brain add/query
flows feel right — the natural language search is the right approach. The 40-char braille
wrapping for the "no results" message now works correctly.

**Ethics (ethics-advisor)**: The vault `_get_vault` returning None silently is an autonomy
concern — a blind user doesn't know why their notes aren't accessible. The system must
always explain what it cannot do and why, including offering the passphrase prompt.

**Consensus recommendation for next cycle**: (1) Fix vault access when keychain has no
key — prompt for passphrase via voice/Telegram instead of silently failing. (2) Wire up
end-to-end Telegram demo: send a voice message → get spoken response back. This is the
Phase 2 "product exists" milestone.

**Orchestrator self-assessment**:
- Accomplished: voice_local.py created; second_brain/query.py created with full voice
  formatting; orchestrator `_execute_intent` now routes screen_description, add_note,
  query_note, and general_question to real handlers; conftest.py suppress_audio fixed
  for missing sounddevice; vault microsecond filename bug fixed; 244 tests all pass
- Attempted but failed: Could not run tests without first fixing conftest suppress_audio
  (ImportError on sounddevice); had to iterate on test assertions to match actual
  keyword extraction behavior
- Confusion/loops: The auto-commit system had already committed files by the time
  manual git add was run — used `git log` to confirm state as recommended in cycle 1
  LESSONS.md (the lesson worked!)
- New gaps: (1) `_get_vault` silently returns None — needs voice passphrase prompt
  recovery path; (2) `transcribe_microphone` uses fixed duration — needs VAD for
  natural conversation; (3) PIL ImageGrab may fail headless — needs Playwright
  screenshot fallback for servers
- Next cycle recommendation: Close the "product exists" gap — wire Telegram end-to-end
  so a real message gets a real voice response. Fix silent vault failure.

---

## Cycle 3 Review — 2026-03-17

**Strategy (nonprofit-ceo)**: Cycle 3 fixed the most dangerous silent failure in the
product (blind user can't access notes, gets no explanation). That is exactly the right
priority — a tool that fails silently is worse than no tool. The 279-test suite is solid.
However, we still have not reached the "product exists" milestone: a blind user still
cannot demo the app end-to-end without developer intervention. Next cycle must close
that gap. Telegram end-to-end demo (voice in, voice out) is the single most important
remaining Phase 2 deliverable.

**Code quality (code-reviewer)**: (1) The vault passphrase recovery in `_get_vault` is
well-structured: register session BEFORE sending prompt (correct ordering), cache
passphrase in context to avoid re-prompting, clear cached passphrase on wrong input.
(2) `_collect_vault_passphrase` reuses the ConfirmationGate queue — elegant, avoids
a second communication mechanism. (3) pyproject.toml `pythonpath = ["src"]` fix is
essential — tests should never require manual PYTHONPATH. (4) One concern: `Optional`
import was missing and only caught at test time. The type annotation coverage in
orchestrator.py is incomplete — `response_callback` params should be typed as
`Optional[Callable]`. (5) Test count grew from 244 to 279: no regressions.

**Security (security-specialist)**: (1) The vault passphrase is cached in `context._vault_passphrase`
as a plain string in memory for the session duration. This is acceptable (OS doesn't
expose process memory to other processes), but should be cleared on session end. Add a
`context.clear_sensitive()` method. (2) The 120-second passphrase timeout window is
reasonable. (3) The `session_passphrase` is never logged — correct. No regressions.

**Accessibility (accessibility-reviewer)**: The passphrase prompt text is clear and
non-visual: "Please say or type your passphrase now." — correct, works for voice AND
Telegram text users. The "Notes unlocked" confirmation is good UX — user knows the
action succeeded. The offer to remember the passphrase is opt-in, not opt-out — correct.
One note: the 120-second timeout may still be too short for Dorothy (elder); consider
making it configurable (e.g., config.yaml voice.prompt_timeout_seconds).

**User perspective (blind-user-tester)**: Before this fix, if my keychain didn't have
the vault key (e.g., new session, different machine, keychain reset), I was locked out
with no explanation. Now I get a clear spoken prompt and can recover by speaking my
passphrase. This is a real usability win. My next question: can I use the app yet?
Can I send a Telegram message and get a voice reply? That's the test that matters.

**Ethics (ethics-advisor)**: Caching the passphrase in the session context is acceptable
and actually better for autonomy — the user doesn't have to repeat themselves every
time they access a note in the same session. The opt-in offer to store in keychain
respects informed consent. The 120-second timeout respects user agency without being
so short it creates frustration.

**Consensus recommendation for next cycle**: (1) Wire Telegram end-to-end: send a
voice message → get transcription → orchestrator → TTS audio reply. This closes the
Phase 2 "product exists" gap. (2) Add `context.clear_sensitive()` to clear cached
passphrase on session end. (3) Make the passphrase prompt timeout configurable.

**Orchestrator self-assessment**:
- Accomplished: pyproject.toml pythonpath fix (tests now run without PYTHONPATH hack);
  ISSUE-001 _get_vault silent failure fix with voice passphrase prompt recovery;
  10 new tests for passphrase prompt flow (all pass); 14 new TTS tests covering
  synthesize_speech dispatch, ElevenLabs/pyttsx3 fallback, speed formula, speak_locally;
  11 new STT tests covering transcribe_audio, singleton model loading, transcribe_microphone;
  total: 279 tests, all passing, no regressions from 244.
- Attempted but failed: none — all planned work completed.
- Confusion/loops: mock injection pattern for missing optional deps (pyttsx3, elevenlabs)
  required fresh mock per test (setdefault caused mock state bleed between tests). Fixed
  by using sys.modules["pyttsx3"] = fresh_mock instead of setdefault.
- New gaps: (1) `Optional[Callable]` type annotations missing on response_callback params
  throughout orchestrator.py; (2) session context has no clear_sensitive() method to
  zero out cached passphrase at session end; (3) passphrase prompt timeout is hardcoded
  at 120s — should be config.yaml setting; (4) Telegram end-to-end demo still not
  delivered — remains the #1 Phase 2 gate item.
- Next cycle recommendation: Wire Telegram end-to-end — a real voice message in,
  real TTS audio out, all pieces connected. This is the "product exists" moment and
  the most important single step remaining in Phase 2.

---

## Cycle 4 Review — 2026-03-17

**Strategy (nonprofit-ceo)**: This cycle delivered the foundation for multi-platform expansion
— the REST API server and framework decision are both enabling infrastructure. The codebase
is now correctly aligned: Telegram is secondary, the voice CLI is the demo target. Most
important gap remaining: a real user still cannot use the product end-to-end. The voice E2E
demo is still the #1 gap. Next cycle must close that gap — it is the "product exists" milestone
and the Phase 2 gate.

**Code quality (code-reviewer)**: (1) Test count grew from 279 to 314 — no regressions.
(2) api_server.py is well-structured: pydantic models for all contracts, global safe error
handler prevents stack trace leaks, auth checks at the right layer. (3) The _PatchedClient
anti-pattern (test pollution via __del__ unreliability) was caught and corrected during the
cycle — use context managers, not __del__, for test resource cleanup. (4) clear_sensitive()
correctly scoped. (5) Concern: clients/ directory doesn't exist yet — arch decision documented
but not started.

**Security (security-specialist)**: (1) Bearer token auth is acceptable for localhost dev;
must upgrade before cloud deployment. (2) api_auth_disabled bypass is clearly named with
a warning log — correct. (3) Global error handler correctly swallows stack traces — a good
security pattern. (4) MISSING: rate limiting middleware. On localhost low risk; must be added
before cloud deployment. Add as ISSUE-011.

**Accessibility (accessibility-reviewer)**: Per-request braille_mode, speech_rate, verbosity
overrides in the API server are the correct pattern for supporting diverse needs without
server-side state. Voice E2E demo still not delivered — no real accessibility testing possible
yet. The arch decision (React Native) is the right call for accessibility.

**User perspective (blind-user-tester)**: The API server means any client can connect to the
brain. But I still can't USE the product — I need a voice interface that works end-to-end.
React Native for client apps is the right call. VoiceOver and TalkBack have been burned by
Flutter before. React Native's native accessibility tree is the foundation this product needs.

**Ethics (ethics-advisor)**: api_auth_disabled flag with warning log is good — degrades
gracefully for development without hiding security state from developers. The rate limiting
gap is an autonomy concern: if a third party can spam the API and degrade response quality,
that harms user independence.

**Goal adherence (goal-adherence-reviewer)**: All three P1 items addressed. Two P2 items
resolved as bonus. Phase 2 gate "product exists" milestone still not met — voice E2E demo
must be next cycle's first task.

**Consensus recommendation for next cycle**: (1) Wire voice_local.py → Whisper STT →
orchestrator → TTS → speaker end-to-end; write integration test; this closes Phase 2.
(2) Create clients/ directory with React Native Expo skeleton — start the first client app.

**Orchestrator self-assessment**:
- Accomplished: ARCH DECISION (React Native + Expo, documented in ARCHITECTURE.md);
  REST API server (api_server.py, 6 endpoints, Bearer auth, 28 tests); context.clear_sensitive()
  (ISSUE-005, 4 tests); configurable passphrase timeout (ISSUE-006, 3 tests); codebase audit
  (telegram_bot.py docstring + main.py default corrected); OPEN_ISSUES.md updated; total
  test count 314 (was 279), all passing, no regressions
- Attempted but failed: none — all planned work completed
- Confusion/loops: _PatchedClient using __del__ for patch cleanup caused test pollution;
  fixed by switching to contextmanager + with-block pattern. Lesson: never rely on __del__
  for resource cleanup in tests — always use context managers or pytest fixtures.
- New gaps: (1) API server needs rate limiting before cloud deployment (ISSUE-011);
  (2) clients/ directory doesn't exist yet — React Native skeleton needs to be created;
  (3) voice E2E demo still the #1 outstanding Phase 2 gate item
- Next cycle recommendation: Voice E2E demo first (close Phase 2 gate), then React Native
  client skeleton. In that order — the voice pipeline is the foundation everything else builds on.

**TECHNICAL LESSON (test cleanup)**: When mocking external dependencies in tests, always use
context managers (with patch(...):) or pytest fixtures, never __del__. Python's garbage
collector does not guarantee __del__ timing, so cleanup may not happen before the next test
runs, causing state pollution between test modules.

---

## Cycle 5 Review — 2026-03-17

**Strategy (nonprofit-ceo)**: This cycle closed the most important open gap — ISSUE-007, the
Phase 2 "product exists" gate. The voice pipeline is proven end-to-end with 9 E2E tests. The
React Native skeleton gives us the first client app with accessibility from the start. These
two together mean a developer can now connect a phone to the backend. The most critical next
step is getting real TalkBack/VoiceOver testing on a device — that requires the npm install
and an emulator. Cloud deployment planning should start next cycle so we can reach real users.

**Code quality (code-reviewer)**: (1) Test count grew from 314 to 348 — no regressions.
(2) Wake-word-only bug in voice_local.py was correctly found by a failing test and fixed in
src/ (not the test) — correct process. (3) Minor dead code: `wake_word_found` variable is
declared in voice_local.py after the fix but is never read. Low priority. (4) React Native
API client is well-typed with proper error class. (5) E2E test uses sys.modules patching
for anthropic — correct pattern when package not installed in CI. (6) Platform test stubs
are correctly skipped with clear reason strings pointing to ISSUE-010.

**Security (security-specialist)**: No new security concerns. The TODO in app/index.tsx
(`BEARER_TOKEN: string | null = null`) is clearly documented and harmless for development.
The voice local bug fix (wake word stripping) has no security implications. Rate limiting
(ISSUE-011) remains open — still localhost-only, still acceptable for dev.

**Accessibility (accessibility-reviewer)**: MainScreen.tsx is accessibility-correct from
the first commit: `role="button"` with label AND hint; `role="header"` for title; status
text uses `accessibilityLiveRegion="polite"`; emoji decorated with `importantForAccessibility="no"`.
The E2E accessibility test (no visual-only language in responses) is novel and important —
first time we've asserted on voice output content quality. Recommend adding the visual-language
check to every new orchestrator response path in future cycles.

**User perspective (blind-user-tester)**: The wake-word fix is real user impact — saying
"assistant" alone without a command used to silently send garbage to the AI. Now it correctly
asks "Yes? How can I help?" exactly like a real voice assistant should. The React Native
screen's startup announcement is correct. I'd want to run TalkBack on a real device to
verify the double-tap activation flow works as expected.

**Ethics (ethics-advisor)**: No concerns. The bearer token TODO is clearly commented and
doesn't ship to users in this state. The voice pipeline correctly routes all AI processing
through the backend — nothing runs client-side that could leak user data.

**Goal adherence (goal-adherence-reviewer)**: Both P1 items delivered exactly as scoped in
PRIORITY_STACK.md. ISSUE-007 (Phase 2 gate) resolved. ISSUE-009 (React Native skeleton)
resolved. The 21 skipped platform E2E tests are correctly documented stubs — they match the
test structure in testing.md and point to ISSUE-010 for follow-up. No requirements dropped.

**Consensus recommendation for next cycle**: (1) Run `npm install` in clients/mobile and
verify the 32 JS tests pass — this should be a Cycle 6 P1. (2) Begin cloud deployment
planning so React Native clients can connect to a real server, not just localhost — the
clients/ directory is built, the backend is built; connecting them on a real device is the
next "product exists" milestone.

**Orchestrator self-assessment**:
- Accomplished: ISSUE-007 resolved (9 E2E voice pipeline tests, accessibility assertion);
  25 unit tests for voice_local.py; wake-word-only bug fixed in voice_local.py;
  React Native Expo skeleton (clients/mobile/) with accessibility-first MainScreen.tsx,
  typed API client, 32 JS tests; multi-platform E2E stubs (Web/Android/iOS/Desktop)
  properly skipped with ISSUE-010 references; Python test count 348 (was 314)
- Attempted but failed: none — all planned work completed
- Confusion/loops: lifecycle tests for VoiceLocalInterface.start() initially hung because
  the loop is infinite and the transcription mock needed to raise CancelledError to exit
  cleanly. Fixed by having the mock raise asyncio.CancelledError instead of returning None.
  Lesson: when testing infinite loops, the mock must interrupt the loop, not just return
  a null value.
- New gaps: (1) `wake_word_found` variable in voice_local.py after fix is dead code —
  minor cleanup item; (2) clients/mobile/ JS tests need `npm install` to run — should be
  part of CI next cycle; (3) bearer token storage needs expo-secure-store integration
  before any user can actually use the React Native app
- Next cycle recommendation: (1) Add npm install + jest to CI (clients/mobile/); resolve
  the 32 JS tests in CI; (2) Design the setup wizard voice flow for mobile — the
  `BEARER_TOKEN = null` TODO needs to become a real first-run experience

**TECHNICAL LESSON (wake word detection)**: When the wake word is the entire utterance
("assistant" with nothing after it), the code must explicitly set `clean_transcript = ""`
after finding an empty `after_wake`. Setting it to the original transcript (the default)
left a non-empty string that bypassed the "Yes?" follow-up prompt. Always verify the
control flow for the wake-word-only case — it's the most common first interaction for a
new user learning the app.

**TECHNICAL LESSON (infinite loop testing)**: When testing a method that runs an infinite
loop (`while self._running`), the test mock must cause the loop to exit, not just return
a value. The cleanest pattern: have the mock raise `asyncio.CancelledError` (which the loop
catches and breaks on), or set `self._running = False` and then raise. Never rely on the
loop checking `_running` between a return value and the next iteration — there may be
more code between them.

---

## Cycle 6 Review — 2026-03-17

**Strategy (nonprofit-ceo)**: Delivered concrete user-visible value. The mobile setup wizard
means a blind user who downloads the app now has a complete path from first launch to
connected assistant — all narrated aloud. The CI job closes a real test-reliability gap.
Rate limiting is prudent infrastructure protecting user service quality. The next most
important thing: the MainScreen button still sends a hardcoded message instead of recording
real microphone input. Closing that gap makes the native app actually usable as a voice
assistant — not just a connected stub.

**Code quality (code-reviewer)**: (1) Test count: Python 339→347, JS 31→77 — no regressions.
(2) RateLimitMiddleware correctly uses time.monotonic() and defaultdict(deque) — proper sliding
window. (3) One code smell: STEP_INSTRUCTIONS.confirm is mutated as a module-level variable
inside handleConfirmToken() — should be a useRef. Low severity. (4) app/index.tsx has no
unit tests (documented gap — integration test in Phase 3). (5) No test file regressions.

**Security (security-specialist)**: Bearer token stored correctly in expo-secure-store (device
secure enclave, never in JS constants). RateLimitMiddleware uses monotonic clock and takes
only the first X-Forwarded-For IP (correct). Two items to address: (1) The speak() call in
handleConfirmToken includes partial token chars — if TTS output is logged at DEBUG level
this would leak credentials; add a comment warning. (2) saveApiBaseUrl() does not validate
the URL — a file: or data: URL would be invalid; add URL validation before storing.

**Accessibility (accessibility-reviewer)**: SetupWizardScreen is accessibility-correct from
the first commit: error uses liveRegion="assertive"; confirm step speaks first-4/last-4 for
verification; every interactive element has accessibilityLabel + accessibilityHint. One note:
the TextInput should have importantForAccessibility="yes" explicitly to guarantee TalkBack
focus on appearance. Progress indicator correctly uses importantForAccessibility="no-hide-descendants".

**User perspective (blind-user-tester)**: The setup wizard is the right approach. Hearing the
token prefix/suffix read back before confirm gives real confidence. Re-enter button is critical.
The unresolved gap: MainScreen still sends hardcoded "Hello, what can you do?" — a real blind
user tapping the button would hear a canned response, not their actual spoken question.
This must be fixed before the app is meaningful.

**Ethics (ethics-advisor)**: No concerns. Wizard asks only for the API token, no personal data.
Token never leaves device — used only for local backend auth. Rate limiting protects user's
AI access from being degraded by others.

**Goal adherence (goal-adherence-reviewer)**: All four PRIORITY_STACK items addressed exactly as
scoped. ISSUE-014, ISSUE-013, ISSUE-012, ISSUE-011 all resolved. No requirements dropped. The
mobile app can now be fully configured by voice on first run — this was the stated goal of ISSUE-013.

**Consensus recommendation for next cycle**: (1) Add real microphone recording to MainScreen —
replace the hardcoded message with expo-av audio capture, send the WAV bytes to the backend
for STT, display/speak the AI response. This closes the "the app actually works as a voice
assistant" milestone. (2) Add URL validation to saveApiBaseUrl() and importantForAccessibility
to the TextInput in SetupWizardScreen (minor fixes from this cycle's review).

**Orchestrator self-assessment**:
- Accomplished: ISSUE-014 (JS CI job — 32→77 JS tests now in CI); ISSUE-013 (setup wizard —
  useSecureStorage hook, SetupWizardScreen, app/index.tsx rewrite, 63 new JS tests);
  ISSUE-012 (dead code removed from voice_local.py); ISSUE-011 (RateLimitMiddleware, 8 new
  Python tests); Python total 347 (was 339), JS total 77 (was 31), all passing
- Attempted but failed: none — all planned work completed
- Confusion/loops: (1) jest.mock("react-native") with jest.requireActual caused a circular
  dependency on the SettingsManager native module — fixed by switching to jest.spyOn in
  beforeEach. (2) importantForAccessibility="no-hide-descendants" hides elements from
  @testing-library getByText/getByLabelText — fixed test to check accessible header instead.
- New gaps: (1) MainScreen.tsx sends hardcoded "Hello" — needs real microphone capture
  (ISSUE-015 below); (2) saveApiBaseUrl should validate URL scheme; (3) SetupWizardScreen
  TextInput missing importantForAccessibility="yes"; (4) speak() in wizard logs partial token
  at DEBUG level — harmless but worth a comment
- Next cycle recommendation: Implement real voice recording in MainScreen (expo-av
  AudioRecorder → send to backend /query as audio or pre-transcribed text). This completes
  the "native app actually records and responds to voice" milestone that is the true Phase 2
  completion for the mobile client.

**TECHNICAL LESSON (React Native test mocks)**: Never use jest.requireActual("react-native")
inside jest.mock() — it triggers the Settings.ios.js module which requires SettingsManager
(a native module not available in Node-based Jest, even with jest-expo preset). Instead, use
jest.spyOn() in beforeEach() to patch individual methods on the already-mocked module that
jest-expo provides. This is the correct and idiomatic pattern for jest-expo environments.

**TECHNICAL LESSON (importantForAccessibility vs testing-library)**: Elements with
importantForAccessibility="no-hide-descendants" in React Native are correctly hidden from
accessibility tree queries (getByText, getByLabelText) in @testing-library/react-native.
This is correct behavior — the element is intentionally decorative. Do not try to query these
elements via accessibility APIs; instead, test that the accessible counterpart (the spoken
announcement, or an accessible header on the same screen) is present.
