---
name: retrospective
description: >
  Run a deep retrospective on recent cycles. Analyzes git history, test results, and
  lessons learned to identify patterns, recurring failures, and process improvements.
  Run this when cycles seem to be going in circles, after a phase completes, or weekly
  as a health check. Produces recommendations for improving the autonomous loop itself.
user-invocable: true
context: fork
agent: general-purpose
---

# Product Cycle Retrospective

You are conducting a retrospective on the Blind Assistant autonomous development loop.
Your job is to honestly assess what's working, what isn't, and make concrete improvements.

## Step 1: Gather Evidence

```bash
# Recent commit history
git log --oneline -30

# What changed recently
git diff HEAD~10 --stat

# Any test results
ls docs/TEST_RESULTS_*.md 2>/dev/null

# Lessons learned so far
cat docs/LESSONS.md

# Current blockers
grep -A 20 "## Blockers" docs/CYCLE_STATE.md
```

## Step 2: Analyze Patterns

Look for:
- **Loops**: Same issue appearing in multiple cycle summaries
- **Abandoned tasks**: Things started but never finished
- **Agent failures**: Which agents return unhelpful results?
- **Missing capability**: Things the loop wanted to do but couldn't because a tool was missing
- **Drift**: Is the work drifting away from the mission in PRODUCT_BRIEF.md?
- **Pace**: Is each cycle making meaningful progress or spinning?

## Step 3: Interrogate the Loop Itself

Ask these hard questions:
1. Is the `/run-cycle` skill's instructions clear enough? Where does the AI get confused?
2. Are the right agents being called for each phase?
3. Is the state in `docs/CYCLE_STATE.md` accurate and useful?
4. Is the commit history telling a coherent story of progress?
5. What would a human engineer say is wrong with how the AI is working?

## Step 4: Propose Improvements

For each problem found:
1. Root cause (be specific — not "the AI got confused" but WHY)
2. Concrete fix (edit a skill file, agent prompt, or state file)
3. Actually make the fix now if it's a small change to a `.md` file

## Step 5: Write Retrospective Report

Create or append to `docs/RETROSPECTIVE_[date].md`:
```markdown
# Retrospective — [Date]

## Cycles reviewed: N to M
## Overall health: ON TRACK / SLOWING / STUCK / DRIFTING

## What's working well:
[List]

## Problems identified:
[Problem 1: root cause + fix applied or recommended]
[Problem 2: ...]

## Changes made to the loop:
[List of files changed and why]

## Recommended focus for next 3 cycles:
[Specific, actionable]
```

## Step 6: Commit

```bash
git add -A
git commit -m "retro: [date] retrospective — [one line summary]

Health: [status]
Key issue: [main thing found]
Fix applied: [or 'recommendations only']"
git push
```
