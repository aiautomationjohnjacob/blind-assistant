# Priority Stack — Ranked Backlog

> Maintained by the orchestrator. Updated every cycle.
> The orchestrator ALWAYS works from the top of this stack.
> Items are added by gap detection, persona feedback, security audits, and user stories.
> Items are removed when completed and committed.

## How Priority is Determined

1. **P0 — BLOCKING**: Security vulnerabilities, broken builds, data loss risk
2. **P1 — SHOWSTOPPER**: A blind user persona cannot complete a core task
3. **P2 — PHASE GATE**: Required deliverable for current phase to complete
4. **P3 — KNOWN GAP**: Detected gap not yet addressed (see OPEN_ISSUES.md)
5. **P4 — IMPROVEMENT**: Enhancement that improves the product meaningfully
6. **P5 — CREATIVE**: New idea or integration opportunity worth exploring

## Current Stack

| Priority | Item | Source | Added |
|----------|------|---------|-------|
| P2 | Run Phase 1: gap analysis + integration map + security model | CYCLE_STATE.md | 2026-03-17 |
| P2 | Tech-lead architecture decision | CYCLE_STATE.md | 2026-03-17 |
| P2 | Initial project scaffold (voice-only setup) | CYCLE_STATE.md | 2026-03-17 |
| P2 | User stories from all 5 blind personas | CYCLE_STATE.md | 2026-03-17 |
| P2 | Design self-expanding capability (how app installs tools at runtime safely) | PRODUCT_BRIEF examples | 2026-03-17 |
| P2 | Design risk-disclosure flow for payment/banking details (spoken warning + confirmation) | PRODUCT_BRIEF examples | 2026-03-17 |
| P2 | Payment tokenization architecture (Stripe tokens — never store raw card numbers) | security model | 2026-03-17 |

## Completed Items

| Item | Completed | Cycle # |
|------|-----------|---------|
| Agent network setup (20 agents) | 2026-03-17 | 0 |
| GitHub repo + MCP integration | 2026-03-17 | 0 |
| Autonomous loop infrastructure | 2026-03-17 | 0 |
| Product brief with synthesis vision | 2026-03-17 | 0 |
