---
name: fix-wcag
description: >
  Batch-fix WCAG violations across the codebase. Reads the latest accessibility audit report,
  groups violations by file, and implements fixes. Run after /audit-a11y to action its findings.
user-invocable: true
disable-model-invocation: false
context: fork
agent: general-purpose
---

# Batch WCAG Fix Workflow

Fix all outstanding WCAG violations from the latest accessibility audit.

## Step 1: Load Latest Audit
Find the most recent audit report:
```bash
ls -t docs/accessibility-audit-*.md | head -1
```
Read the report and extract all BLOCKER and CRITICAL findings.

## Step 2: Triage and Group
Group violations by file/component. Prioritize:
1. BLOCKER items first (features completely unusable by blind users)
2. CRITICAL items (WCAG AA violations)
3. WARNING items if time permits

## Step 3: Consult Tech Lead
Before implementing, use the **tech-lead** agent to:
- Confirm the fix approach for each violation type
- Identify any shared patterns that should be fixed globally (e.g., a reusable component)
- Approve the implementation strategy

## Step 4: Implement Fixes
For each violation:
1. Read the affected file
2. Apply the specific fix described in the audit finding
3. Verify the fix addresses the root cause, not just the symptom

## Step 5: Verify
After all fixes are implemented:
1. Re-run any available automated tests: `npm test -- --testNamePattern="a11y"` or equivalent
2. Use the **accessibility-reviewer** agent to verify the specific fixed files
3. Use the **blind-user-tester** agent to verify fixed components pass experiential review

## Step 6: Commit
```bash
git add -A
git commit -m "a11y: fix WCAG violations from audit [date]

$(cat docs/accessibility-audit-*.md | grep -E 'BLOCKER|CRITICAL' | wc -l) violations fixed.
Details in docs/accessibility-audit-*.md"
```

Report: N violations fixed across N files, any remaining unresolved items and why.
