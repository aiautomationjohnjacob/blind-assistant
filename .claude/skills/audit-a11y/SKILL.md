---
name: audit-a11y
description: >
  Run a comprehensive WCAG 2.1 AA accessibility audit. Spawns parallel sub-agents for
  automated and experiential review. Pass a path argument to audit a specific directory,
  or omit to audit all of src/.
user-invocable: true
context: fork
agent: general-purpose
argument-hint: [path/to/audit]
---

# Accessibility Audit

Conduct a full accessibility audit of: $ARGUMENTS (default: `src/` if no argument given)

## Step 1: Automated Checks
Run axe-core on the build if available:
```bash
npx @axe-core/cli http://localhost:3000 --exit 2>/dev/null || echo "axe CLI not available — proceeding with code review"
```

## Step 2: Code Analysis (Parallel Sub-Agents)
Invoke ALL THREE agents simultaneously for parallel review:

1. Use the **accessibility-reviewer** agent to check WCAG 2.1 AA compliance on all changed/specified files
2. Use the **blind-user-tester** agent to do experiential review of each UI component found
3. Use the **screen-reader-expert** agent to validate all ARIA patterns used

## Step 3: Aggregate Findings
Consolidate results by severity:
- **BLOCKER** — Feature unusable by blind users (from blind-user-tester) or violates WCAG A
- **CRITICAL** — Violates WCAG 2.1 AA or serious screen reader incompatibility
- **WARNING** — Best-practice deviation or screen reader inconsistency risk
- **INFO** — Enhancement opportunity

## Step 4: Report
Create a markdown audit report at `docs/accessibility-audit-$(date +%Y%m%d).md` with:
- Executive summary (N blockers, N critical, N warnings)
- Full findings by severity
- Files audited
- Recommended fix order

If GitHub MCP is available: Create a GitHub issue titled "A11y Audit [YYYY-MM-DD]" with the
full report, and individual issues for each BLOCKER tagged `a11y` `blocker`.

## Step 5: Summary
Report to the main conversation: total findings by severity, top 3 most critical issues,
and link to the audit report file.
