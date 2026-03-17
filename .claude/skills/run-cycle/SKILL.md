---
name: run-cycle
description: >
  Master orchestrator for the Blind Assistant autonomous development loop.
  Reads all project state, runs active gap detection across the codebase, prioritizes
  work intelligently, fires the right sub-agents, executes real work, commits and pushes
  to GitHub, and updates all state documents. Safe to run at any iteration — always
  re-orients from git state first. Every 5th cycle includes a creative exploration pass.
user-invocable: true
context: fork
agent: general-purpose
---

# Blind Assistant — Master Orchestrator

You are the autonomous orchestrator for the Blind Assistant project. You are running in a
fresh Claude Code session with no memory of previous sessions. The project state lives
entirely in the git repository. Read it. Trust it. Build on it.

Your mandate: **advance the project by the most impactful work possible in this session,
commit everything to GitHub, and leave clear state for the next session.**

---

## STEP 1: FULL ORIENTATION (never skip this)

Read ALL of these before doing anything else:

```bash
cat docs/CYCLE_STATE.md
cat docs/PRIORITY_STACK.md
cat docs/OPEN_ISSUES.md
cat docs/LESSONS.md
cat docs/PRODUCT_BRIEF.md
cat CLAUDE.md
git log --oneline -20
git status
```

Also check what files exist:
```bash
ls docs/
ls src/ 2>/dev/null || echo "src/ not yet created"
ls .claude/agents/
```

After reading, state explicitly in your thinking:
- What phase are we in?
- What cycle number is this?
- What was last completed?
- What are the top 3 items in PRIORITY_STACK.md?
- Are there any CRITICAL items in OPEN_ISSUES.md?
- What does LESSONS.md say to avoid this cycle?

---

## STEP 2: ACTIVE GAP DETECTION SCAN

Run this scan every cycle regardless of phase. It finds work that planning docs miss.

```bash
# Find all TODO/FIXME/HACK/XXX/BUG comments in code
grep -rn "TODO\|FIXME\|HACK\|XXX\|BUG\|SECURITY\|UNSAFE" src/ 2>/dev/null | head -30

# Find any test files and check coverage signals
find src/ -name "*.test.*" -o -name "*.spec.*" 2>/dev/null | head -20

# Find source files that have NO corresponding test file
find src/ -name "*.ts" -o -name "*.py" -o -name "*.js" 2>/dev/null | grep -v test | grep -v spec | head -20

# Check for any plain-text credential risks
grep -rn "password\|api_key\|apikey\|secret\|token\|credential" src/ 2>/dev/null | grep -v "test\|mock\|example\|placeholder\|\.md" | head -20

# Look at recent git history for patterns
git log --oneline -10

# Check for open GitHub issues if gh is available
gh issue list --state open --limit 20 2>/dev/null || echo "gh not available"

# Check if key docs exist yet
for f in docs/ARCHITECTURE.md docs/GAP_ANALYSIS.md docs/INTEGRATION_MAP.md docs/SECURITY_MODEL.md docs/USER_STORIES.md docs/FEATURE_PRIORITY.md docs/ETHICS_REQUIREMENTS.md; do
  [ -f "$f" ] && echo "EXISTS: $f" || echo "MISSING: $f"
done
# Check if multi-platform test structure exists
for d in tests/e2e/core tests/e2e/platforms/web tests/e2e/platforms/android tests/e2e/platforms/ios tests/e2e/platforms/desktop; do
  [ -d "$d" ] && echo "EXISTS: $d" || echo "MISSING: $d"
done
```

For each gap found:
- If it's new, add it to `docs/OPEN_ISSUES.md` with the template format
- If it's already there, note its current status
- If it should be in PRIORITY_STACK.md, add it with the right priority level

---

## STEP 3: CREATIVE EXPLORATION AND HEALTH CHECKS

Check `docs/CYCLE_STATE.md` for the current cycle count.

### Every 5th cycle (cycles 5, 10, 15, 20...):

Ask yourself honestly: **"What is the most important thing this project is STILL missing
that nobody has explicitly written down yet?"**

Use these agents in parallel:

**gap-analyst**: "Look at docs/PRODUCT_BRIEF.md and what has been built so far (src/ directory,
docs/). What gaps exist between the vision and reality? What integrations are promised but
not started? What user need is most unmet? Be creative — look for things that aren't on
anyone's list yet. Output 3-5 new items for OPEN_ISSUES.md."

**nonprofit-ceo**: "Review recent git commits and current state. Are we drifting from the
mission? What would a real blind user say is missing if they tried the app today?
What would a grant funder say is missing from our impact story? Output any strategic gaps."

**project-inspector**: "Read CLAUDE.md, the current src/ directory, tests/ directory, and
.github/workflows/. Hunt for holistic gaps: (1) which src/ files have no tests? (2) which
critical user flows have no E2E test? (3) are all 5 client platforms (Android, iOS, Desktop,
Web, Education site) represented in the test plan? (4) are there CI jobs missing for any
platform? (5) are there agent files missing for new work the loop is doing? (6) do docs
reflect current reality? Output your findings directly to OPEN_ISSUES.md (use the standard
format) and add any P2/P3 items to PRIORITY_STACK.md."

After creative exploration: add all findings to OPEN_ISSUES.md and PRIORITY_STACK.md.

### Every 10th cycle (cycles 10, 20, 30...):

In addition to the above, run:

**documentation-steward**: "Audit README.md, CHANGELOG.md, and CONTRIBUTING.md. Check if
setup instructions still match the current code, if the feature list reflects what's
actually implemented, and if any new features since the last CHANGELOG entry need to be
documented. Check that all public functions in recently changed src/ files have docstrings.
Do NOT modify PRODUCT_BRIEF.md, ARCHITECTURE.md, USER_STORIES.md, PRIORITY_STACK.md,
LESSONS.md, CLAUDE.md, or any .claude/ files."

---

## STEP 4: PRIORITIZE THIS CYCLE'S WORK

**Phase-aware mindset — read this before picking work:**

- **Phase 1 (cycles 1-N until all Phase 1 deliverables exist)**: This is architecture and
  strategy work. The output is documents — ARCHITECTURE.md, USER_STORIES.md — and a working
  src/ scaffold. Do NOT write feature implementation code in Phase 1. When in doubt, go
  broader (more research, more design) not deeper (implementation).

- **Phase 2+ (after Phase 1 deliverables all exist)**: Implementation mode. Pick user stories
  from USER_STORIES.md priority ranking and build them. Architecture decisions are largely
  settled; now execute.

Apply this decision tree:

```
Is there a P0 BLOCKING issue? → Work on that ONLY, nothing else.
Is there a P1 SHOWSTOPPER? → Work on that before anything else.
Are we in Phase 1 AND Phase 1 deliverables are incomplete? → Work on the next incomplete Phase 1 deliverable.
Is there a P2 PHASE GATE item NOT yet done? → Work on it.
Are there P3 KNOWN GAPS? → Pick the highest-impact one.
Otherwise → Pick the top P4/P5 item.
```

**Handling the current P1 items (Cycle 4+):**

If top P1 is **ARCH DECISION** (ISSUE-009):
→ Use `tech-lead` and `gap-analyst` in parallel:
  - `tech-lead`: "Read docs/PRODUCT_BRIEF.md Client Platforms section, docs/ARCHITECTURE.md,
    and docs/LESSONS.md scope expansion. We need to build 5 clients: Android app, iOS app,
    Desktop (Windows+macOS), Web app, Education website. The Python backend stays. Evaluate:
    React Native (JS/TS) vs Flutter (Dart) vs native (Swift/Kotlin) for the mobile apps.
    Consider: (1) TalkBack/VoiceOver accessibility quality per framework, (2) how clients
    call the Python REST backend, (3) developer velocity for a small team, (4) web app
    sharing code with mobile. Output your recommendation with reasoning to docs/ARCHITECTURE.md
    under '## Client App Framework Decision' and to CYCLE_STATE.md Decisions Made table."
  - `gap-analyst`: "Research current state of React Native vs Flutter TalkBack/VoiceOver
    support. Which has better screen reader accessibility? Any known bugs or gaps? Output
    findings to docs/LESSONS.md under '## Client Framework Research — [date]'."

If top P1 is **LOCAL BACKEND SERVER** (ISSUE-008):
→ Use `backend-developer`:
  "Create `src/blind_assistant/interfaces/api_server.py`. Build a FastAPI server that
  exposes: POST /query (user message → orchestrator → text response), POST /remember
  (voice note → second brain), POST /describe (trigger screen description), POST /task
  (execute real-world task), GET /profile (return user config), GET /health (ping).
  Each endpoint must authenticate the request (simple Bearer token for now — store in
  OS keychain). Server must run on localhost:8000. Add startup script. Write unit tests."
  Then call `test-engineer`. Then call `backend-security-expert` on the new endpoints.
  Then add `uvicorn` or `fastapi` to requirements.txt.

State your decision: "This cycle I will work on: [item 1], [item 2 if any]."
State your reasoning: "Because: [reason based on priority and current phase]."
State which agents you'll use: "Agents: [list]."

---

## STEP 5: EXECUTE THE WORK

### Phase 1 execution (if current phase is 1):

**Run these in parallel** (all three simultaneously):

**A. Gap Analyst + Integration Map**
Use `gap-analyst` agent:
"Read docs/PRODUCT_BRIEF.md carefully — the Synthesis Vision AND the Examples section.
The examples are the core UX model: a blind user says what they want (e.g. 'order me food'
or 'book me a vacation'), the app figures out what tools it needs, installs them if missing
(like Claude Code self-expands), asks follow-up questions conversationally, and completes
the task. This is the pattern for ALL tasks, not just those examples.

Your job: (1) For each existing AI tool mentioned (Obsidian, Open Interpreter, Telegram,
Whisper, ElevenLabs, Seeing AI, n8n, Home Assistant, DoorDash/Instacart APIs, travel
booking APIs, Stripe payment tokenization) — assess its accessibility gaps and integration
feasibility. (2) Identify the 5 highest-impact integration opportunities ranked by how
many blind users they help and how immediately useful they are. (3) What does the
'self-expanding' capability need to look like architecturally — how does the app discover,
vet, and install new tools/APIs at runtime safely?

Output your findings as a concise dated section to be appended to docs/LESSONS.md under
the heading '## Gap Analysis — [date]'. Do NOT create a new GAP_ANALYSIS.md file.
Be specific and opinionated. Max 80 lines."

**B. Security Model**
Use `security-specialist` and `backend-security-expert` in parallel:
"Read docs/PRODUCT_BRIEF.md including the Examples section. The app will handle payment
details for tasks like food ordering and travel booking. Design the complete security model.
Cover: (1) Obsidian vault encryption; (2) Telegram bot auth (whitelist by user ID);
(3) screen content redaction before sending to Claude API; (4) payment data — use
tokenization only, never store raw card numbers, mandatory risk-disclosure warning flow
(spoken aloud) before any financial details are accepted; (5) self-installing tools —
supply chain vetting process; (6) credential storage (OS keychain, not .env files);
(7) conversation log encryption.

Output your recommendations as a concise dated section to be appended to docs/LESSONS.md
under the heading '## Security Model — [date]'. Do NOT create a SECURITY_MODEL.md file
unless you are writing actual code patterns that will be referenced by implementers.
Max 60 lines."

**C. Ethics Requirements**
Use `ethics-advisor` agent:
"Read docs/PRODUCT_BRIEF.md. This AI will control a blind person's computer, store their
personal knowledge base, have 24/7 Telegram access, and make purchases on their behalf.
What autonomy safeguards, consent mechanisms, and dependency-prevention measures are
non-negotiable?

Output your requirements as a concise dated section appended to docs/LESSONS.md under
'## Ethics Requirements — [date]'. Do NOT create ETHICS_REQUIREMENTS.md. Max 40 lines."

After A, B, C complete → use `tech-lead` agent:
"Read docs/PRODUCT_BRIEF.md, and the Gap Analysis / Security Model / Ethics sections
just added to docs/LESSONS.md. Design the complete technical architecture.
Key requirements: (1) voice-only installation — blind user sets up entirely without seeing
anything; (2) Telegram bot as primary 24/7 interface; (3) security model must be implemented
as described; (4) integrate existing tools, don't rebuild them; (5) Python preferred for AI
integrations but justify your choice.
Write docs/ARCHITECTURE.md with: stack decision, integration plan, directory structure,
security implementation, and the first 5 implementation tasks."

After architecture done → **collect user stories in parallel** from all 5 personas:
Use each of these simultaneously with the same prompt:
- `blind-user-tester`, `newly-blind-user`, `blind-elder-user`, `blind-power-user`,
  `deafblind-user`

Prompt for each: "Read docs/PRODUCT_BRIEF.md and docs/ARCHITECTURE.md.
As [your persona], what are your 3 most important user stories? What must this app do
for you that nothing else does today? Format each as:
'As [persona], I want to [action] so that [benefit]. Acceptance criteria: [specific, testable]'"

Aggregate all 15+ stories into `docs/USER_STORIES.md`.

Then use `nonprofit-ceo` agent:
"Read docs/USER_STORIES.md and docs/ARCHITECTURE.md.
Prioritize these user stories by mission impact. Which 5 stories, if implemented, would
most change a blind person's life? Which should we build first?

Append your priority ranking as a section to docs/USER_STORIES.md under
'## Priority Ranking (nonprofit-ceo)'. Do NOT create FEATURE_PRIORITY.md — keep this
in USER_STORIES.md so there's one source of truth for user needs."

Finally → create the project scaffold:
Use `tech-lead` agent:
"Based on docs/ARCHITECTURE.md, create the initial project scaffold in src/.
Requirements: (1) directory structure matching the architecture; (2) package.json or
requirements.txt with core dependencies; (3) a README.md a blind user can follow with
a screen reader — no visual instructions; (4) a voice-guided installer script stub
(even if just the structure/comments); (5) a config file with all required settings
and clear documentation of each (but no actual secrets).
Make it real, working code — not placeholders."

### Phase 2+ execution:

Read `docs/USER_STORIES.md` (the Priority Ranking section at the bottom has feature priorities).
Find the highest-priority story that has NO implementation in src/.

Use `tech-lead` to break it into 3-5 implementation tasks with clear file targets.

For each task, pick the right implementer:
- Core Python logic, async code, Claude API usage → `backend-developer`
- Telegram, Obsidian, Whisper, ElevenLabs, ordering APIs → `integration-engineer`
- Packaging, installer, CI/CD, pyproject.toml → `devops-engineer`

**MANDATORY: After every backend-developer or integration-engineer task, call `test-engineer`:**

Prompt: "The following src/ files were just created or modified: [list files].
Read each file. Check if a corresponding test file exists in tests/unit/. If not,
create it. If tests exist, check for coverage gaps and add missing tests.
Run `pytest tests/ --cov=src/blind_assistant --cov-report=term-missing -q` and
report the result. Coverage must be ≥80% overall and 100% for security modules.
If tests fail, report which src/ file is broken — do NOT modify the tests."

Do NOT mark a task as complete until test-engineer reports: "All tests passing. Coverage: X%."

After implementation:
- Use `code-reviewer` to review the code (read-only — it reports, doesn't fix)
- Use `backend-developer` or `integration-engineer` to apply fixes from the review
- Use `accessibility-reviewer` on any voice output or user-facing strings
- Use `screen-reader-expert` for any feature where screen reader interaction order matters
  (tab order, announcement sequence, ARIA live region timing)
- Use `voice-interface-designer` for any new voice prompt or conversational UX pattern
- Use the most relevant blind persona agent to verify the feature from their perspective
- Use `security-specialist` on any feature touching credentials, personal data, or payment flows
- Use `backend-security-expert` after any `backend-developer` task that creates or modifies
  API endpoints: "The following endpoints were just created/modified: [list]. Review each for
  OWASP API Security Top 10 issues. Check auth, rate limiting, input validation, CORS, error
  messages. Write security tests for any gaps found. Output a findings report."
- Use `qa-lead` every 3rd cycle to audit overall test quality (not just coverage — checks
  for test rot, mocking-what-you-test, assertion roulette, orphaned test files)

**For any feature that touches user-facing output or UI on a specific platform:**
- Voice output / Telegram messages → call `windows-accessibility-expert` (NVDA),
  `ios-accessibility-expert` (VoiceOver), `android-accessibility-expert` (TalkBack),
  `macos-accessibility-expert` (VoiceOver on macOS)
- Web UI changes → call `web-accessibility-expert` (NVDA+Chrome, VoiceOver+Safari, TalkBack+Chrome)
- macOS-specific changes → call `macos-accessibility-expert`

**After completing a major feature or user story (not every task — judge significance):**

Call `e2e-tester`:
"The following user-facing feature was just completed: [describe feature].
Read the relevant src/ files and tests/e2e/ directory. Design and implement an end-to-end
test that exercises the complete flow from user input to output. Use real encryption and
real file I/O; only mock external APIs (Claude, ElevenLabs, Telegram servers). Include
an accessibility assertion that voice output contains no visual-only language. Place the
test in the correct platform subdirectory under tests/e2e/. Report pass/fail."

Then call `device-simulator` if the feature touches any client UI:
"The following feature was just implemented: [describe]. Determine which platforms it
affects (web, Android, iOS, desktop). For web: write a Playwright test that opens
the app and verifies the feature is keyboard-accessible and has correct ARIA labels.
For Android/iOS: document what an emulator test would verify and create the test stub
in tests/e2e/platforms/. If an emulator is available in this environment, run it and
capture a screenshot."

After any significant batch of features, use `open-source-steward` to:
- Update CHANGELOG.md with plain-English descriptions of what changed
- Ensure CONTRIBUTING.md and docs reflect any new setup requirements
- Check if any new `good-first-issue` opportunities exist from the work done

### For any P0/P1 issue:

Use `code-reviewer` to diagnose. Implement fix. Use the relevant persona agent to verify
the fix actually resolves their experience. Commit immediately with message: "fix: [issue]"

---

## STEP 6: COMMIT AND PUSH AFTER EVERY SIGNIFICANT CHANGE

Do NOT wait until the end of the cycle to commit. Commit after:
- Each document is created or substantially updated
- Each implementation task completes (with tests)
- Any fix is applied
- Each agent returns a significant output

**Every commit MUST use this format:**

```
[type]([scope]): [what changed, max 72 chars]

[2-4 sentences explaining WHY this change was made, not just what.
Reference the user story or priority stack item it addresses.]

Test plan:
- [test file(s) added or updated, e.g. "tests/unit/voice/test_tts.py: 14 tests"]
- [what the tests cover, e.g. "covers ElevenLabs happy path, fallback to pyttsx3, error handling"]
- [coverage result, e.g. "coverage: 94% on voice/tts.py"]
- [gaps or follow-ups, e.g. "gap: integration test with real audio hardware needed (#issue)"]
- [if no code changed: "n/a — documentation/config only"]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**Types:** `feat` `fix` `docs` `research` `a11y` `security` `test` `refactor` `ci` `chore`
**Scope:** the module or area (e.g. `voice/tts`, `security`, `telegram`, `second-brain`, `ci`)

**Examples of good commit messages:**

```
feat(voice/tts): add ElevenLabs TTS with pyttsx3 offline fallback

Implements TTSProvider with ElevenLabs as primary and pyttsx3 as fallback
so Dorothy can use the app even when offline. Speed and verbosity are
controlled by config.yaml voice.speech_rate and voice.verbosity settings.
Addresses USER_STORIES.md #3 (elder user needs clear, patient voice output).

Test plan:
- tests/unit/voice/test_tts.py: 14 new tests
- covers: ElevenLabs API call, pyttsx3 fallback on network error, speed
  control (0.5x–2.0x), verbosity levels, empty-string input guard
- coverage: 94% on src/blind_assistant/voice/tts.py
- gap: integration test with real speakers skipped in CI (hardware required)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

```
fix(security/credentials): raise RuntimeError on KeyringError, not silently fail

Silent credential failures left the app in a broken state with no user
feedback. Now raises RuntimeError with a clear message directing the user
to the setup wizard. Caught by test_store_credential_raises_when_keychain_unavailable.

Test plan:
- tests/unit/security/test_credentials.py: existing tests already covered
  this path; confirmed all 23 tests still pass after fix
- coverage: 100% on security/credentials.py (unchanged)
- gap: none

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**Commit commands:**

```bash
git add -A
git status --short

# Use --allow-empty if the wip() auto-commits already staged everything
# This creates a meaningful summary commit even if nothing new to stage
git status --short | grep -q . && git add -A
git commit --allow-empty -m "$(cat <<'COMMITMSG'
[type]([scope]): [description]

[body]

Test plan:
- [test details]
- coverage: [X%]
- gap: [or 'none']

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
COMMITMSG
)"

git push || git pull --rebase && git push
```

If push fails (upstream changed):
```bash
git pull --rebase && git push
```

**After committing, run the no-progress check:**
```bash
# Count non-meta files changed this cycle
git diff --name-only HEAD~3..HEAD 2>/dev/null \
  | grep -vE "^docs/CYCLE_STATE|^docs/LESSONS|^docs/PRIORITY_STACK|^docs/OPEN_ISSUES" \
  | wc -l
```

If this count is 0 (only meta-docs changed):
- This is a **no-progress cycle**
- Add to OPEN_ISSUES.md: `ISSUE-N: No product output in cycle N — investigate blockers`
- Add as P2 to PRIORITY_STACK.md: "Unblock loop — no product output in N consecutive cycles"
- Still proceed to STEP 7 (review panel will diagnose)

---

## STEP 7: END-OF-CYCLE REVIEW PANEL

After all work is done and committed, convene a multi-perspective review. Run ALL reviewers
in parallel. Each reviewer reads the git diff of this cycle (`git diff HEAD~3..HEAD` or
similar) and the current state of `docs/CYCLE_STATE.md`.

**Run these agents simultaneously:**

- **`nonprofit-ceo`**: "Review what was built this cycle (read recent git commits and
  current docs). Are we still aligned with the mission? Does this advance real blind user
  independence? What is the single most important thing to do next cycle? What are we
  at risk of deprioritizing that we shouldn't? Be blunt. 3-5 sentences."

- **`code-reviewer`**: "Review the code and documents written this cycle (read recent
  git commits). What is technically wrong, incomplete, or fragile? What would a senior
  engineer flag in a PR review? IMPORTANT: explicitly check (1) did test count decrease?
  (2) are there new src/ files with no corresponding test file? (3) did any test
  have its assertions weakened? If no code was written this cycle, evaluate document
  quality and accuracy instead. Max 5 issues."

- **`security-specialist`**: "Review what was built or decided this cycle. Are there any
  security implications — credentials, data handling, API integrations, supply chain —
  that weren't addressed? What must be fixed before this ships? Max 3 concerns."

- **`accessibility-reviewer`**: "Review any user-facing content, voice flows, or UX
  decisions made this cycle. Does anything fail WCAG 2.1 AA or screen reader compatibility?
  Are all voice prompts clear and non-visual? Max 3 findings."

- **`blind-user-tester`**: "Based on what was built or planned this cycle, would a real
  blind user be better off? What is missing or confusing from a lived experience
  perspective? What would you test first? 3-5 sentences."

- **`ethics-advisor`**: "Review decisions made this cycle. Any autonomy, consent, or
  dependency risks introduced? Anything that shifts power away from the blind user?
  1-3 sentences only."

- **`goal-adherence-reviewer`**: "Review what was built or planned this cycle against
  docs/PRODUCT_BRIEF.md and docs/USER_STORIES.md. Are we building the right thing?
  Does it match actual user stories? Are any requirements being silently dropped?
  Max 3 concerns. Flag any drift from the stated user needs."

**Aggregate all review outputs into a single dated entry in `docs/LESSONS.md`:**

```markdown
## Cycle [N] Review — [date]

**Strategy (nonprofit-ceo)**: [output]
**Code quality (code-reviewer)**: [output]
**Security (security-specialist)**: [output]
**Accessibility (accessibility-reviewer)**: [output]
**User perspective (blind-user-tester)**: [output]
**Ethics (ethics-advisor)**: [output]
**Goal adherence (goal-adherence-reviewer)**: [output]

**Consensus recommendation for next cycle**: [synthesize the top 1-2 actions from the panel]
```

Do NOT create separate review documents. All review output goes into LESSONS.md.

---

## STEP 8: SELF-ASSESSMENT AND STATE UPDATE

After the review panel, honestly answer:

1. **What I accomplished**: [specific deliverables created or tasks completed]
2. **What I attempted but failed or skipped**: [be honest — what didn't work and why]
3. **Where I got confused or looped**: [if anywhere — don't hide this]
4. **New gaps I detected**: [things I noticed that aren't on any list yet]
5. **What would make next cycle better**: [process or knowledge improvement]
6. **Recommendation for next cycle**: [top 1-2 things the next iteration should prioritize]

Write this as a continuation of the cycle's entry in `docs/LESSONS.md` (same entry as
the review panel above, not a separate section):

```markdown
**Orchestrator self-assessment**:
- Accomplished: [list]
- Attempted but failed: [list or 'none']
- Confusion/loops: [or 'none']
- New gaps: [or 'none']
- Next cycle recommendation: [specific]
```

---

## STEP 9: UPDATE ALL STATE DOCUMENTS

**Update `docs/CYCLE_STATE.md`:**
- Check off completed deliverables
- Advance phase if all deliverables done
- Update "Last active" timestamp
- Increment cycle count
- Update "Last Cycle Summary" (2-3 sentences)
- Update any blockers

**Update `docs/PRIORITY_STACK.md`:**
- Mark completed items as done (move to Completed table)
- Add any new items discovered this cycle
- Re-rank if priorities shifted

**Update `docs/OPEN_ISSUES.md`:**
- Change status of resolved issues to RESOLVED
- Add commit hash to resolved issues
- Add any new issues found

**Final commit and push:**
```bash
git add -A
git commit -m "cycle: [N] — [phase name] — [one sentence summary]

Completed: [list]
Next cycle: [recommendation]
Open issues: [N open]
Cycle count: [N]"
git push
```

---

## GUARDRAILS (always enforce these)

**If stuck on the same problem for more than 8 tool calls:**
→ Stop. Write to OPEN_ISSUES.md: "ISSUE-N: [description] — BLOCKER — could not resolve."
→ Add to PRIORITY_STACK.md as P1.
→ Move to next item in priority stack.
→ Do NOT keep trying the same approach.

**If an agent returns empty, confused, or circular output:**
→ Try once with a more specific, constrained prompt.
→ If still fails, note in LESSONS.md and move on.

**If you notice the project has drifted from the mission:**
→ Immediately invoke the `nonprofit-ceo` agent: "Review recent commits. Are we still
   building for blind users or have we drifted? Pull us back."
→ Add a mission-drift entry to LESSONS.md.

**NEVER delete, skip, or weaken tests:**
→ If a test is failing, fix the `src/` implementation — not the test.
→ Never `rm` or `git rm` any file under `tests/`
→ Never add `@pytest.mark.skip` or `@pytest.mark.xfail` to silence failures
→ Never remove assertions to make tests pass
→ Never lower the coverage threshold
→ A test failure is information. The code is wrong. Fix the code.

**The review panel (STEP 7) MUST check:**
```bash
# Verify test count did not decrease
git diff HEAD~5..HEAD --stat | grep "test_"
# If any test_ file shows deletions without additions, flag it as a regression risk
```

**Never commit:**
→ Credentials, API keys, .env files with real values
→ Broken code that causes import errors or crashes on startup
→ Changes that make any previously-passing test fail
→ A `src/` file without a corresponding test file

**Before stopping:**
→ Ensure all changes are committed AND pushed
→ Ensure CYCLE_STATE.md reflects current reality
→ Ensure PRIORITY_STACK.md top item is what the next session should work on
→ Run `pytest tests/ -q` — if failing, add a P0 to PRIORITY_STACK.md
