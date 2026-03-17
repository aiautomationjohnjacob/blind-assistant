# Autonomous Cycle State

> This file is the persistent brain of the autonomous loop.
> Every cycle reads this, does work, then updates it before committing.
> If the AI crashes or restarts, it reads this file first to reorient.

## Current Phase

**Phase**: 2 — Core Build Sprint
**Status**: READY TO START
**Started**: 2026-03-17
**Last active**: 2026-03-17
**Cycles completed**: 1

## Phase Definitions

```
Phase 0: Foundation Setup         ✅ COMPLETE (agent network, GitHub, MCPs)
Phase 1: Discovery & Architecture  → Current
Phase 2: Core Build Sprint         → Pending
Phase 3: Blind User Testing        → Pending
Phase 4: Accessibility Hardening   → Pending
Phase 5: Polish & Community Ready  → Pending
```

## What Happens in Each Phase

### Phase 1: Discovery & Architecture
**Goal**: Define exactly what we're building and how, grounded in existing tools and real gaps.
**Agents**: gap-analyst, nonprofit-ceo, tech-lead, ethics-advisor, security-specialist
**Deliverables**:
- [x] `docs/GAP_ANALYSIS.md` — Landscape of existing AI tools; what to integrate vs build
- [x] `docs/INTEGRATION_MAP.md` — Which tools (Obsidian, Telegram, Open Interpreter, etc.)
      we integrate and how; accessibility gaps in each; our integration strategy
- [x] `docs/ARCHITECTURE.md` — Full tech stack with security architecture
- [x] `docs/USER_STORIES.md` — 10+ user stories from all blind personas
- [x] `docs/FEATURE_PRIORITY.md` — Prioritized feature list with mission justification
- [x] `docs/SECURITY_MODEL.md` — How sensitive data is handled end-to-end (from security-specialist)
- [x] `docs/ETHICS_REQUIREMENTS.md` — Full ethics requirements (bonus: added this cycle)
- [x] `src/` — Initial project scaffold (Python, async, all packages created)
- [x] Phase 1 complete: integration strategy decided, security model defined, scaffold created

### Phase 2: Core Build Sprint
**Goal**: Build the minimum product a blind user can actually try end-to-end.
**Agents**: tech-lead, code-reviewer, accessibility-reviewer, blind-user-tester, security-specialist
**Must include**:
- Screen capture + describe (AI sees and narrates the screen)
- Basic voice I/O (speak to it, it speaks back)
- One complete agentic task end-to-end: user asks for something → AI figures out what
  tools/apps are needed → installs them if missing (with user confirmation) → asks
  follow-up questions conversationally → completes the task
- Risk disclosure flow: whenever banking/payment details are requested, the spoken warning
  must fire before any details are accepted
**Phase 2 complete when**: A blind user can ask the AI to do a real-world task (e.g. order
food or book something) entirely by voice, including the app self-installing what it needs

### Phase 3: Blind User Testing
**Goal**: All 5 blind user personas can complete core life-assistant tasks.
**Agents**: All 5 blind user personas, screen-observer, computer-use-tester, impact-researcher
**Test scenarios must include**:
- Ask the AI what's on their screen and navigate an inaccessible app
- Order food or a household item entirely by voice (including risk-disclosure flow)
- Ask the AI to research something and take action on the result (compound task)
- Add and retrieve a note from their Second Brain by voice
- Complete setup/onboarding with zero sighted assistance
**Phase 3 complete when**: No SHOWSTOPPER issues from any persona across all scenarios

### Phase 4: Accessibility Hardening
**Goal**: WCAG 2.1 AA compliance, security audit, privacy audit, ethics review.
**Agents**: accessibility-reviewer, privacy-guardian, ethics-advisor, security-specialist, deafblind-user
**Phase 4 complete when**: /audit-a11y returns zero CRITICAL findings AND security-specialist
signs off on financial data handling AND ethics-advisor approves transaction confirmation flow

### Phase 5: Polish & Community Ready
**Goal**: Onboarding works for non-technical newly blind user; grant pitch ready; community launch.
**Agents**: newly-blind-user, blind-elder-user, grant-writer, community-advocate
**Test**: Dorothy (elder persona) can: set up the app, order food, and add a note to her
Second Brain — all without sighted help and without ever asking "what do I do next?"
**Phase 5 complete when**: Dorothy passes the above test AND grant-writer produces GRANT_NARRATIVE.md

## Current Sprint (Phase 2 — Core Build Sprint)

**Sprint goal**: Build the minimum product a blind user can actually try end-to-end.

**Sprint items** (Phase 2 targets — check off as complete):
- [ ] Telegram bot fully functional: receives text + voice, replies with text + voice
- [ ] Whisper STT: transcribes voice messages from Telegram
- [ ] TTS: ElevenLabs + pyttsx3 fallback, speed-configurable
- [ ] Screen observer: "What's on my screen?" → spoken description via Claude Vision
- [ ] Screen redaction: password fields and financial screens never sent to API
- [ ] Second Brain MVP: add notes by voice, query notes by voice, encrypted vault
- [ ] Orchestrator: intent classification → tool selection → execution pipeline
- [ ] Tool registry + installer: self-expanding pattern with user confirmation
- [ ] Risk disclosure flow: payment confirmation with spoken warning
- [ ] Voice installer: voice-guided setup from zero to functional
- [ ] End-to-end test: blind user asks to order food → full flow with confirmations

## Blockers

None currently. If blockers exist, they will be listed here with workarounds attempted.

## Last Cycle Summary

Cycle 1 completed Phase 1 entirely in one session. All 7 required Phase 1 deliverables
are committed: GAP_ANALYSIS, INTEGRATION_MAP, SECURITY_MODEL, ETHICS_REQUIREMENTS,
ARCHITECTURE, USER_STORIES, FEATURE_PRIORITY. Full Python project scaffold created
with 29 source files implementing the core module structure. Phase 1 is COMPLETE.
Moving to Phase 2: Core Build Sprint.

## Known Issues / Technical Debt

- `src/blind_assistant/interfaces/voice_local.py` stub not yet created (needed for Phase 2)
- `src/blind_assistant/second_brain/query.py` stub not yet created (needed for Phase 2)
- Tool implementations (doordash.py, instacart.py, etc.) are empty stubs — Phase 2 work
- `src/blind_assistant/memory/mcp_memory.py` not yet implemented — Phase 2 work
- No tests exist yet — Phase 2 must add tests per testing.md requirements

## Decisions Made

| Date | Decision | Made by | Reasoning |
|------|----------|---------|-----------|
| 2026-03-17 | Python 3.11+ as primary language | tech-lead | Best AI ecosystem, async support, keyring library |
| 2026-03-17 | Telegram as primary interface | tech-lead + gap-analyst | 24/7 multi-device, accessible, no visual UI needed |
| 2026-03-17 | Obsidian vault format (file only, no app) | tech-lead | Accessible storage without inaccessible app |
| 2026-03-17 | AES-256-GCM for vault encryption | security-specialist | Industry standard, authenticated encryption |
| 2026-03-17 | OS keychain for all credentials | security-specialist | No .env files, cross-platform, secure |
| 2026-03-17 | Risk disclosure fires every transaction | ethics-advisor + security-specialist | Never assume prior awareness |
| 2026-03-17 | Per-transaction payment confirmation | ethics-advisor | User cannot visually verify; repetition is safer |
