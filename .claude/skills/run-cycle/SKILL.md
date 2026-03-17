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
for f in docs/ARCHITECTURE.md docs/GAP_ANALYSIS.md docs/INTEGRATION_MAP.md docs/SECURITY_MODEL.md docs/USER_STORIES.md docs/FEATURE_PRIORITY.md; do
  [ -f "$f" ] && echo "EXISTS: $f" || echo "MISSING: $f"
done
```

For each gap found:
- If it's new, add it to `docs/OPEN_ISSUES.md` with the template format
- If it's already there, note its current status
- If it should be in PRIORITY_STACK.md, add it with the right priority level

---

## STEP 3: CREATIVE EXPLORATION (run on cycles 5, 10, 15, 20... check cycle number)

Check `docs/CYCLE_STATE.md` for cycle count. If cycle number is divisible by 5:

Ask yourself honestly: **"What is the most important thing this project is STILL missing
that nobody has explicitly written down yet?"**

Use these agents in parallel to explore:

**gap-analyst**: "Look at docs/PRODUCT_BRIEF.md and what has been built so far (src/ directory,
docs/). What gaps exist between the vision and reality? What integrations are promised but
not started? What user need is most unmet? Be creative — look for things that aren't on
anyone's list yet. Output 3-5 new items for OPEN_ISSUES.md."

**nonprofit-ceo**: "Review recent git commits and current state. Are we drifting from the
mission? What would a real blind user say is missing if they tried the app today?
What would a grant funder say is missing from our impact story? Output any strategic gaps."

After creative exploration: add findings to OPEN_ISSUES.md and PRIORITY_STACK.md.

---

## STEP 4: PRIORITIZE THIS CYCLE'S WORK

Based on PRIORITY_STACK.md, OPEN_ISSUES.md, and the gap scan, pick the 1-3 highest-priority
items to work on. Apply this decision tree:

```
Is there a P0 BLOCKING issue? → Work on that ONLY, nothing else.
Is there a P1 SHOWSTOPPER? → Work on that before anything else.
Is there a P2 PHASE GATE item NOT yet done? → Work on the next incomplete phase deliverable.
Are there P3 KNOWN GAPSs? → Pick the highest-impact one.
Otherwise → Pick the top P4/P5 item.
```

State your decision: "This cycle I will work on: [item 1], [item 2 if any]."
State your reasoning: "Because: [reason based on priority]."
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
Write docs/GAP_ANALYSIS.md and docs/INTEGRATION_MAP.md. Be specific and opinionated."

**B. Security Model**
Use `security-specialist` agent:
"Read docs/PRODUCT_BRIEF.md including the Examples section. The app will handle payment
details for tasks like food ordering and travel booking. Design the complete security model.
Cover: (1) Obsidian vault encryption; (2) Telegram bot auth (whitelist by user ID);
(3) screen content redaction before sending to Claude API; (4) payment data — use
tokenization only, never store raw card numbers, mandatory risk-disclosure warning flow
(spoken aloud) before any financial details are accepted; (5) self-installing tools —
supply chain vetting process; (6) credential storage (OS keychain, not .env files);
(7) conversation log encryption.
Write docs/SECURITY_MODEL.md with specific technical recommendations and code patterns."

**C. Ethics Requirements**
Use `ethics-advisor` agent:
"Read docs/PRODUCT_BRIEF.md. This AI will control a blind person's computer, store their
personal knowledge base, have 24/7 Telegram access, and make purchases on their behalf.
What autonomy safeguards, consent mechanisms, and dependency-prevention measures are
non-negotiable? Write docs/ETHICS_REQUIREMENTS.md."

After A, B, C complete → use `tech-lead` agent:
"Read docs/PRODUCT_BRIEF.md, GAP_ANALYSIS.md, INTEGRATION_MAP.md, SECURITY_MODEL.md,
ETHICS_REQUIREMENTS.md. Design the complete technical architecture.
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
"Read docs/USER_STORIES.md, GAP_ANALYSIS.md, ARCHITECTURE.md.
Prioritize these user stories by mission impact. Which 5 stories, if implemented, would
most change a blind person's life? Which should we build first? Write docs/FEATURE_PRIORITY.md."

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

Read `docs/FEATURE_PRIORITY.md` and `docs/USER_STORIES.md`.
Find the highest-priority story that has NO implementation in src/.

Use `tech-lead` to break it into 3-5 implementation tasks with clear file targets.

For each task, pick the right implementer:
- Core Python logic, async code, Claude API usage → `backend-developer`
- Telegram, Obsidian, Whisper, ElevenLabs, ordering APIs → `integration-engineer`
- Packaging, installer, CI/CD, pyproject.toml → `devops-engineer`

After implementation:
- Use `code-reviewer` to review the code (read-only — it reports, doesn't fix)
- Use `backend-developer` or `integration-engineer` to apply fixes from the review
- Use `accessibility-reviewer` on any voice output or user-facing strings
- Use the most relevant blind persona agent to verify the feature from their perspective
- Use `security-specialist` on any feature touching credentials or personal data

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
- Each document is created
- Each agent returns a significant output
- Each implementation task completes
- Any fix is applied

```bash
git add -A
git status --short
# Only commit if there are actual changes
git status --short | grep -q . && git commit -m "[type]: [description]

[2-3 line body explaining what was done and why]"

# ALWAYS push immediately after committing
git push
```

Commit types: `feat:` `fix:` `docs:` `research:` `a11y:` `security:` `test:` `refactor:`

If push fails (upstream changed), pull and retry:
```bash
git pull --rebase && git push
```

---

## STEP 7: SELF-ASSESSMENT AND STATE UPDATE

After the work, honestly answer:

1. **What I accomplished**: [specific deliverables created or tasks completed]
2. **What I attempted but failed or skipped**: [be honest — what didn't work and why]
3. **Where I got confused or looped**: [if anywhere — don't hide this]
4. **New gaps I detected**: [things I noticed that aren't on any list yet]
5. **What would make next cycle better**: [process or knowledge improvement]
6. **Recommendation for next cycle**: [top 1-2 things the next iteration should prioritize]

Write this as a dated entry to `docs/LESSONS.md`:
```markdown
## Cycle [N] — [date]

**Accomplished**: [list]
**Attempted but failed**: [list or 'none']
**Confusion/loops**: [or 'none']
**New gaps detected**: [or 'none']
**Recommendation for next cycle**: [specific]
```

---

## STEP 8: UPDATE ALL STATE DOCUMENTS

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

**Never commit:**
→ Credentials, API keys, .env files with real values
→ Broken code that causes import errors or crashes on startup
→ Changes that make any previously-passing test fail

**Before stopping:**
→ Ensure all changes are committed AND pushed
→ Ensure CYCLE_STATE.md reflects current reality
→ Ensure PRIORITY_STACK.md top item is what the next session should work on
