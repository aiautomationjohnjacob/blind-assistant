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

### Nonprofit Operations Agents
- **grant-writer** — Frames impact in grant language; identifies fundable milestones

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

## Git Workflow
- Feature branches: `feature/description`
- Commit messages: conventional commits (feat:, fix:, a11y:, docs:, test:, research:)
- PRs require: code-reviewer + accessibility-reviewer approval

## Detailed Rules
@.claude/rules/accessibility.md
@.claude/rules/testing.md
