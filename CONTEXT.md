# Blind Assistant — New Session Quick Start

> Read this first if you're a new Claude session with no prior context.
> This file is the entry point. Everything else is linked from here.

## What This Project Is

An open-source **AI life companion** for blind and visually impaired people — not a screen
reader, but a persistent assistant that helps someone live a fully independent life through
conversation. Think of it as the Claude Code model applied to a blind person's entire life:
if it can't do something, it figures out how and installs what it needs (with user permission).

**Concrete examples of what it does:**
- "Order me food" → installs DoorDash if needed, collects payment securely (with risk warning), takes order by voice, submits
- "Book me a vacation, I'm not sure where" → researches blind-accessible destinations and booking tools, asks follow-up questions, books the trip
- "What's on my screen?" → takes screenshot, describes it intelligently, navigates inaccessible apps
- "Add this to my Second Brain" → stores voice notes in an encrypted personal knowledge base, queryable by conversation
- Available 24/7 via Telegram on any device — phone, laptop, anywhere

**The synthesis principle**: most tools blind people need already exist. The setup, interfaces,
and documentation just assume vision. We wrap existing tools (Obsidian, Open Interpreter,
Telegram, Whisper, ElevenLabs, DoorDash API, etc.) in an accessible layer a blind person
can set up entirely by voice, from day one, with zero sighted assistance.

Full vision: `docs/PRODUCT_BRIEF.md`

## How to Continue Working

1. Read `docs/CYCLE_STATE.md` — tells you exactly where we are
2. Read `docs/PRIORITY_STACK.md` — tells you what to do next
3. Read `docs/OPEN_ISSUES.md` — tells you what's broken or missing
4. Read `docs/LESSONS.md` — tells you what past cycles learned (avoid repeating mistakes)
5. Run `/run-cycle` — executes one full autonomous development iteration

## Agent Roster (38 agents available)

All agent definitions in `.claude/agents/`. Key agents by function:

| Role | Agent |
|------|-------|
| Strategic direction | `nonprofit-ceo` |
| Architecture & standards | `tech-lead` |
| **Writes Python code** | `backend-developer` |
| **Builds integrations** | `integration-engineer` |
| **Packaging & CI/CD** | `devops-engineer` |
| Code quality (read-only) | `code-reviewer` |
| Goal/mission alignment | `goal-adherence-reviewer` |
| Security audit | `security-specialist` |
| Open source & community | `open-source-steward` |
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
| Cloud infrastructure | `cloud-architect` |
| Education website | `education-website-designer` |
| Unit + integration tests | `test-engineer` |
| Test strategy & quality | `qa-lead` |
| End-to-end tests | `e2e-tester` |
| Holistic gap detection | `project-inspector` |
| iOS app accessibility | `ios-accessibility-expert` |
| Android app accessibility | `android-accessibility-expert` |
| Windows app + NVDA/JAWS | `windows-accessibility-expert` |
| macOS app + VoiceOver | `macos-accessibility-expert` |
| Web + browser accessibility | `web-accessibility-expert` |
| Device emulator + screenshot | `device-simulator` |
| Documentation accuracy | `documentation-steward` |

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
- Every action costing money or sending comms requires explicit user confirmation
- **Risk disclosure**: spoken warning required before user provides any banking/payment info
- **Self-expanding**: app may install tools it needs, but must tell the user and get confirmation
- **Conversational completion**: ask follow-up questions rather than failing silently
- Commit AND push to GitHub after every meaningful change
- Update CYCLE_STATE.md, PRIORITY_STACK.md, OPEN_ISSUES.md before stopping

## GitHub

Repo: https://github.com/aiautomationjohnjacob/blind-assistant
Auto-runs every 4 hours via GitHub Actions (`.github/workflows/autonomous-cycle.yml`)
