---
name: review-pr
description: >
  Multi-persona PR review using specialist agents. Runs code-reviewer, accessibility-reviewer,
  and goal-adherence-reviewer in parallel, then posts consolidated findings as a PR comment.
  Pass the PR number as argument.
user-invocable: true
disable-model-invocation: false
context: fork
agent: general-purpose
argument-hint: [PR-number]
---

# Multi-Persona PR Review

Review PR #$ARGUMENTS using parallel specialist agents.

## Step 1: Gather PR Context
```bash
gh pr view $ARGUMENTS --json title,body,files,commits
gh pr diff $ARGUMENTS
```

## Step 2: Parallel Agent Reviews
Spawn all three agents simultaneously:

1. **code-reviewer** — Review for code quality, correctness, security, and maintainability
2. **accessibility-reviewer** — Review for WCAG 2.1 AA compliance and ARIA correctness
3. **goal-adherence-reviewer** — Verify implementation matches the PR description and mission

Pass the PR title and description to the goal-adherence-reviewer as context for requirements.

## Step 3: Aggregate Results
Collect findings from all three reviewers and determine overall verdict:
- If any BLOCKER exists → **Request Changes**
- If only CRITICAL/WARNING → **Request Changes** with specific items to address
- If only INFO/SUGGESTION → **Approve with Comments**
- If clean → **Approve**

## Step 4: Post Review
If GitHub MCP is available, post as a PR review comment using:
```
gh pr review $ARGUMENTS --[approve|request-changes] --body "[consolidated review]"
```

If GitHub MCP is not available, output the full review to the conversation.

## Review Comment Format
```markdown
## PR Review — [title]

### Code Quality (code-reviewer)
[findings or ✅ No issues found]

### Accessibility (accessibility-reviewer)
[findings or ✅ WCAG 2.1 AA compliant]

### Goal Adherence (goal-adherence-reviewer)
[findings or ✅ All requirements satisfied]

### Verdict: APPROVE / REQUEST CHANGES
[reason and specific items to address]
```
