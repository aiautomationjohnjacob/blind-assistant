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

## Resolved Issues

*(Moved here when fixed)*
