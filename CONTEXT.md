# Blind Assistant — New Session Quick Start

> Read this first if you're a new Claude session with no prior context.
> This file is the entry point. Everything else is linked from here.

## What This Project Is

An open-source AI life assistant for blind and visually impaired people.
Not another screen reader — an AI that synthesizes existing tools (Obsidian, Telegram,
Open Interpreter, Whisper, ElevenLabs, shopping APIs) into one accessible layer that
a blind person can set up and use entirely by voice, 24/7, from any device.

Full vision: `docs/PRODUCT_BRIEF.md`

## How to Continue Working

1. Read `docs/CYCLE_STATE.md` — tells you exactly where we are
2. Read `docs/PRIORITY_STACK.md` — tells you what to do next
3. Read `docs/OPEN_ISSUES.md` — tells you what's broken or missing
4. Read `docs/LESSONS.md` — tells you what past cycles learned (avoid repeating mistakes)
5. Run `/run-cycle` — executes one full autonomous development iteration

## Agent Roster (21 agents available)

All agent definitions in `.claude/agents/`. Key agents by function:

| Role | Agent |
|------|-------|
| Strategic direction | `nonprofit-ceo` |
| Architecture & standards | `tech-lead` |
| Code quality (read-only) | `code-reviewer` |
| Security audit | `security-specialist` |
| WCAG compliance | `accessibility-reviewer` |
| Screen reader expert | `screen-reader-expert` |
| Voice UX design | `voice-interface-designer` |
| Screen observation | `screen-observer` |
| Computer use testing | `computer-use-tester` |
| Experienced blind user | `blind-user-tester` |
| Newly blind (Alex) | `newly-blind-user` |
| Elder blind (Dorothy) | `blind-elder-user` |
| Power user (Marcus) | `blind-power-user` |
| DeafBlind (Jordan) | `deafblind-user` |
| Gap analysis | `gap-analyst` |
| Impact research | `impact-researcher` |
| Community voice | `community-advocate` |
| Privacy protection | `privacy-guardian` |
| Ethics review | `ethics-advisor` |
| Grant writing | `grant-writer` |
| Voice UX | `voice-interface-designer` |

## Custom Skills

- `/run-cycle` — Main autonomous loop (reads state → detects gaps → does work → pushes)
- `/audit-a11y [path]` — Full WCAG audit via parallel agents
- `/review-pr [#]` — Multi-persona PR review
- `/fix-wcag` — Batch WCAG violation fixes
- `/retrospective` — Deep cycle health check

## Key Rules (Non-Negotiable)

- Every feature must work by voice with zero vision required
- Sensitive data (passwords, banking, health) NEVER in plain text
- Screen content redacted before external API calls
- Every action costing money or sending comms requires user confirmation
- Commit AND push to GitHub after every meaningful change
- Update CYCLE_STATE.md, PRIORITY_STACK.md, OPEN_ISSUES.md before stopping

## GitHub

Repo: https://github.com/aiautomationjohnjacob/blind-assistant
Auto-runs every 4 hours via GitHub Actions (`.github/workflows/autonomous-cycle.yml`)
