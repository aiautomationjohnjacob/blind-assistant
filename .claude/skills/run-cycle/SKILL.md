---
name: run-cycle
description: >
  Run one full autonomous product cycle iteration. Reads current state, does the work
  for the current phase, updates state, and commits progress. This is the main autonomous
  loop driver — it can be run repeatedly and will always pick up where it left off.
  Safe to run at any time; always reads state first before acting.
user-invocable: true
context: fork
agent: general-purpose
---

# Autonomous Product Cycle — One Iteration

You are the orchestrator. Your job is to advance the Blind Assistant project by exactly
one meaningful cycle. You are autonomous — make decisions, do work, and commit progress.
You do NOT wait for human input. If you hit a blocker, document it and work around it.

## Step 1: Orient (always do this first)

Read these files in order:
1. `docs/CYCLE_STATE.md` — What phase are we in? What's done? What's next?
2. `docs/LESSONS.md` — What have previous cycles learned? Don't repeat mistakes.
3. `docs/PRODUCT_BRIEF.md` — What are we building and why?
4. `CLAUDE.md` — Project rules and agent roster

Based on what you read, state clearly:
- Current phase
- What was last completed
- What this cycle should accomplish
- Which agents you'll use

## Step 2: Run the Work for Current Phase

### If Phase 1 (Discovery & Architecture) — NOT STARTED

Spawn these agents in parallel:

**Task A** — Use the `gap-analyst` agent:
"Analyze the current blind assistive technology landscape. Identify the 5 most important
gaps our app can fill. Focus on computer navigation tasks blind users cannot complete
today without sighted assistance. Output: `docs/GAP_ANALYSIS.md`"

**Task B** — Use the `ethics-advisor` agent:
"Review our product concept in docs/PRODUCT_BRIEF.md. Identify ethical risks in an AI
that controls a blind user's computer. What safeguards must be built-in from day one?
Output: `docs/ETHICS_REQUIREMENTS.md`"

After both complete, use the `tech-lead` agent:
"You have: docs/PRODUCT_BRIEF.md, docs/GAP_ANALYSIS.md, docs/ETHICS_REQUIREMENTS.md.
Choose the technology stack for Blind Assistant. Consider: Python vs Node vs Electron,
speech I/O library, screen capture approach, LLM integration (Claude API), packaging for
blind users (must be installable without visual setup). Document your decision with full
reasoning. Output: `docs/ARCHITECTURE.md`"

Then use the `nonprofit-ceo` agent:
"Review docs/GAP_ANALYSIS.md and docs/ARCHITECTURE.md. Validate or challenge the
direction. Are we solving the right problems first? Output: your assessment appended to
`docs/PRODUCT_BRIEF.md` under a 'CEO Review' section."

Finally: generate `docs/USER_STORIES.md` by asking EACH of these 5 agents for their
top 3 user stories (use them in parallel):
- blind-user-tester
- newly-blind-user
- blind-elder-user
- blind-power-user
- deafblind-user

Aggregate all stories into `docs/USER_STORIES.md` with persona labels.

When Phase 1 deliverables are all complete, use tech-lead to scaffold the project:
"Create the initial project scaffold based on docs/ARCHITECTURE.md. Create the directory
structure, package.json/requirements.txt, and a README.md that a blind user could follow
using a screen reader. Keep it minimal — just enough to run 'hello world'."

Mark Phase 1 complete.

### If Phase 2 (Core Build Sprint)

Read `docs/ARCHITECTURE.md` and `docs/USER_STORIES.md`.
Pick the single highest-priority user story that is NOT yet implemented.
Use `tech-lead` to break it into 3-5 implementation tasks.
Implement those tasks, using `code-reviewer` after each significant change.
Use `accessibility-reviewer` when any UI is added.
Commit after each task completion.

### If Phase 3 (Blind User Testing)

For each blind user persona, run them through the core flows:
- Use screen-observer to capture screenshots of current state
- Use computer-use-tester to run an end-to-end task
- Use each blind persona agent to review what they experience
- Document all issues found in `docs/TEST_RESULTS_[date].md`
- For each SHOWSTOPPER: immediately add a task to fix it in the next cycle

### If Phase 4 (Accessibility Hardening)

Run `/audit-a11y src/` — fix all BLOCKER and CRITICAL issues.
Run `privacy-guardian` on any screen-capture code.
Run `ethics-advisor` on any autonomous action features.

### If Phase 5 (Polish & Community Ready)

Run `newly-blind-user` and `blind-elder-user` on the onboarding flow.
Run `grant-writer` to create `docs/GRANT_NARRATIVE.md`.
Run `community-advocate` to prepare `docs/COMMUNITY_OUTREACH.md`.

## Step 3: Self-Assessment (do this every cycle)

After the work, honestly assess:
1. What did I accomplish this cycle? (be specific)
2. What did I attempt but fail or skip? Why?
3. Did I get confused or loop anywhere? What happened?
4. What would make the next cycle go better?
5. Any patterns in what the agents struggled with?

Write this as a dated entry in `docs/LESSONS.md`.

## Step 4: Update State

Update `docs/CYCLE_STATE.md`:
- Mark completed deliverables
- Update current phase if all deliverables are done
- Update sprint items
- Record any new blockers
- Update "Last Cycle Summary" with 2-3 sentences
- Increment cycle count

## Step 5: Commit Everything

```bash
git add -A
git status
git commit -m "cycle: [phase name] — [1 sentence summary of what was accomplished]

Cycle #N | Phase X
Completed: [list of deliverables]
Next: [what the next cycle will do]
Blockers: [any, or 'none']"
git push
```

## Guardrails

- If you've been working on the same task for more than 10 tool calls without progress,
  stop, document the blocker in CYCLE_STATE.md, and move to the next task.
- If an agent returns an error or empty result, try once with a more specific prompt.
  If it fails again, document and skip.
- Never delete code without understanding why it exists.
- Never commit credentials, API keys, or .env files.
- If you're unsure whether to proceed with a major decision, document the options in
  `docs/DECISIONS_PENDING.md` and take the more conservative path.
