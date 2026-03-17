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
