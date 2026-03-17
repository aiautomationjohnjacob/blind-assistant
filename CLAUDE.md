# Blind Assistant — Project Vision & Operating Manual

## The Product Vision

Blind Assistant is an open-source AI assistant built specifically for blind and visually
impaired users. Think of it as **Open Interpreter / Open Claude for the blind** — a
conversational AI that can actually see, navigate, and control the computer on behalf of
the user, through natural speech or text.

Most screen readers (NVDA, JAWS, VoiceOver) work by reading what's on the screen.
They require the user to already know how to navigate. They break when apps are poorly
labeled. They can't handle novel situations. They have no reasoning ability.

**Blind Assistant is different.** It combines Claude's vision, reasoning, and computer use
capabilities into an assistant that:
- **Sees the screen** — takes screenshots and describes what's actually on it
- **Understands context** — knows what the user is trying to accomplish, not just what's focused
- **Navigates intelligently** — can click, type, scroll, and navigate apps the user couldn't access alone
- **Describes images** — live audio description of photos, charts, documents, and visual interfaces
- **Handles the unexpected** — when a poorly labeled app breaks a screen reader, Blind Assistant
  can reason about what it sees and help anyway
- **Learns the user's patterns** — adapts to individual needs, vocabulary, and workflows over time
- **Speaks and listens** — voice-first interface; no mouse, no visual UI required

This is not just another accessibility tool. It is an AI that genuinely extends what a blind
person can independently accomplish on a computer — making tasks possible that were previously
impossible, or that required sighted assistance.

## The Organization

Blind Assistant is a **nonprofit** initiative. The measure of success is:
> "How many more blind people can independently use their computer today compared to yesterday?"

Not revenue. Not users. Not downloads. Independence.

The project is built, governed, and tested with the blind community — not for them, not at them.
Real blind users are embedded in every phase of design, development, and evaluation.

## The Agent Network

This project runs through an orchestrated network of AI sub-agents, each with a distinct
role, expertise, and perspective. Claude Code's autonomous capabilities allow these agents
to work in parallel, review each other's work, and commit progress continuously.

### Core Team Agents
- **nonprofit-ceo** — Sets strategic direction; anchors all decisions in mission
- **tech-lead** — Architecture, technology selection, code standards
- **code-reviewer** — Technical quality, security, correctness (read-only)
- **goal-adherence-reviewer** — Verifies work matches requirements and mission

### Accessibility & Compliance Agents
- **accessibility-reviewer** — WCAG 2.1 AA / ARIA compliance auditing
- **screen-reader-expert** — NVDA/JAWS/VoiceOver/TalkBack behavioral differences
- **voice-interface-designer** — Conversational UI, audio UX, voice-first design patterns

### Blind User Persona Agents (Diverse Voices)
- **blind-user-tester** — Experienced screen reader user (NVDA primary)
- **newly-blind-user** — Recently lost sight; learning assistive tech; needs simplicity
- **blind-elder-user** — 65+, low technical confidence; dignity and patience required
- **blind-power-user** — Expert; demands efficiency, speed, minimal verbosity
- **deafblind-user** — Uses refreshable braille display; no audio channel available

### Technical Implementation Agents
- **backend-developer** — Writes Python implementation code; async, Claude API, voice pipelines
- **integration-engineer** — Builds service integrations: Telegram, Obsidian, Whisper,
  ElevenLabs, DoorDash, travel APIs, Home Assistant, Stripe tokenization
- **devops-engineer** — Packaging (PyPI), voice-guided installer, CI/CD, release automation

### Computer Interaction Agents (Screen & System)
- **screen-observer** — Takes screenshots, describes screen state using vision AI
- **computer-use-tester** — Drives actual workflows via Playwright/Desktop Commander

### Research & Strategy Agents
- **gap-analyst** — Analyzes existing tools, identifies unmet needs in the blind tech space
- **impact-researcher** — Designs user studies, measures real-world independence outcomes
- **community-advocate** — Voice of the organized blind community; NFB/ACB/APH perspective

### Ethics & Safety Agents
- **privacy-guardian** — Protects sensitive screen content (passwords, banking, health data)
- **ethics-advisor** — Ensures AI enhances autonomy, not dependency; informed consent
- **security-specialist** — Implementation security audit: encryption, credential storage,
  Telegram security, plain-text sensitive data, prompt injection, dependency CVEs

### Open Source & Community Agents
- **open-source-steward** — Community health, CONTRIBUTING.md, issue triage, PR reviews,
  CHANGELOG, release notes; ensures blind contributors feel especially welcome

### Nonprofit Operations Agents
- **grant-writer** — Frames impact in grant language; identifies fundable milestones

### Testing & Quality Agents
- **test-engineer** — Writes exhaustive unit tests for all Python code; 80% coverage floor;
  100% on security modules; called after every backend-developer or integration-engineer task
- **qa-lead** — Owns test strategy and test quality (not just coverage); detects test rot;
  designs regression suites; ensures test pyramid is balanced
- **e2e-tester** — Designs and writes end-to-end tests covering full user flows (voice → STT →
  orchestrator → tool → TTS); only external APIs mocked; one test per blind persona scenario
- **project-inspector** — Proactively hunts for holistic gaps (missing tests, missing CI, missing
  E2E, agent roster gaps, doc gaps, dependency hygiene); called every 5th cycle; writes directly
  to OPEN_ISSUES.md and PRIORITY_STACK.md

### Platform Accessibility Agents
- **ios-accessibility-expert** — Native iOS app + Safari web app; VoiceOver, Switch Control,
  AssistiveTouch; UIAccessibility API; Siri Shortcuts integration; Dynamic Type support
- **android-accessibility-expert** — Native Android app + Chrome web app; TalkBack, BrailleBack,
  Switch Access, Voice Access; Android Accessibility API; gesture-based navigation patterns
- **windows-accessibility-expert** — Native desktop app + Chrome/Firefox web app; NVDA and JAWS;
  the NVDA keyboard-only test is the project's accessibility floor; NVDA Browse/Forms Mode
- **macos-accessibility-expert** — Native macOS app + Safari web app; VoiceOver (shares
  NSAccessibility architecture with iOS); macOS Keychain; Terminal.app VoiceOver compatibility
- **web-accessibility-expert** — Cross-browser web app + education website; covers NVDA+Chrome,
  NVDA+Firefox, VoiceOver+Safari, TalkBack+Chrome, JAWS+Chrome; WCAG 2.1 AA; semantic HTML first

### Infrastructure & Education Agents
- **cloud-architect** — Designs cloud infrastructure in planning mode (no live accounts yet);
  recommends Railway/Fly.io for Telegram webhook, local-first for user vault; infrastructure as code
- **education-website-designer** — Builds accessible course platform at `learn.blind-assistant.org`;
  audio-primary design; must be fully completable by NVDA user with zero mouse use

### Documentation Agent
- **documentation-steward** — Keeps README.md, CHANGELOG.md, CONTRIBUTING.md, and code-level
  docstrings accurate and up to date; called every 10th cycle; NEVER modifies strategic docs
  (PRODUCT_BRIEF.md, ARCHITECTURE.md, USER_STORIES.md, PRIORITY_STACK.md, CLAUDE.md, LESSONS.md)

## Custom Skills (Slash Commands)
- `/audit-a11y [path]` — Full WCAG audit via parallel agents
- `/review-pr [#]` — Multi-persona PR review posted to GitHub
- `/fix-wcag` — Batch-fix WCAG violations from latest audit

## Technology Approach (Synthesis Strategy)
The goal is to integrate existing tools, not reinvent them:
- **Screen observation**: Claude vision + Playwright screenshots
- **Computer control**: Playwright MCP (browser), Desktop Commander MCP (native apps)
- **Voice I/O**: Whisper (STT) + ElevenLabs/Kokoro (TTS) — better than screen reader voices
- **Personal knowledge (Second Brain)**: Obsidian-compatible markdown vault, voice-queried
- **Multi-device access**: Telegram bot as primary 24/7 interface (phone + laptop)
- **Memory**: MCP memory server (cross-session knowledge graph)
- **Automation**: n8n or similar for background task workflows
- **Physical-world tasks**: Shopping/ordering APIs (with explicit user confirmation always)
- **Stack**: TBD by tech-lead agent in Phase 1 — must support voice-only setup

## Non-Negotiable Rules
- Every interactive element MUST have an accessible name
- Every PR MUST pass accessibility audit before merge
- No `outline: none` without a visible focus replacement
- Color must NEVER be the sole conveyor of information
- Sensitive data (passwords, banking, health) NEVER stored in plain text
- Screen content containing PII must NEVER be sent to external APIs without redaction
- All user-facing strings support i18n
- Every feature is tested with at least one blind user persona agent before shipping
- Security specialist must review any feature that handles credentials or personal data
- Every action that costs money or sends a communication requires explicit user confirmation
- **Risk disclosure is mandatory**: whenever the user provides banking or payment details,
  the app MUST warn them clearly — even if our security is good — that providing financial
  information to any app carries inherent risk. No exceptions.
- **Self-expanding is allowed**: the app may install tools, apps, or APIs it needs to
  complete a task (like Claude Code does) — but it must tell the user what it's installing
  and why, and get confirmation before doing so
- **Conversational task completion**: the app resolves tasks through conversation, asking
  follow-up questions as needed rather than failing silently or requiring upfront specification
- **NEVER delete or weaken tests**: if a test is failing, fix the `src/` implementation.
  Never delete test files, remove assertions, add `skip`, or lower coverage thresholds to
  make CI green. A failing test is information — it means the code is wrong.
- **Every `src/` file must have tests in the same commit**: `test-engineer` runs after
  every `backend-developer` or `integration-engineer` task. No code ships untested.

## Git Workflow

Feature branches: `feature/description`
PRs require: code-reviewer + accessibility-reviewer approval

**Every commit must use this format** (enforced by run-cycle STEP 6):

```
[type]([scope]): [what changed, max 72 chars]

[2-4 sentences explaining WHY — not just what — was changed.
Reference the user story or PRIORITY_STACK item it addresses.]

Test plan:
- [test file(s) added/updated and number of tests]
- [what the tests cover]
- coverage: [X% on the changed module]
- gap: [known test gap or 'none']

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

Types: `feat` `fix` `docs` `research` `a11y` `security` `test` `refactor` `ci` `chore`
Scope: the module/area touched (`voice/tts`, `security`, `telegram`, `second-brain`, `ci`)

The `wip(src: filename.py) HH:MM` commits from the auto-hook are intermediate saves.
The meaningful commit with the test plan is the `feat/fix/etc` commit from STEP 6.
Both appear in history; reviewers focus on the typed commits.

## Detailed Rules
@.claude/rules/accessibility.md
@.claude/rules/testing.md
