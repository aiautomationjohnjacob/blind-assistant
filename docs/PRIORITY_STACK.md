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

## Current Stack (Phase 2 — Core Build Sprint)

| Priority | Item | Source | Added |
|----------|------|---------|-------|
| P2 | Implement Telegram bot: receive text + voice, reply with text + voice | ARCHITECTURE.md Task 1 | 2026-03-17 |
| P2 | Implement Whisper STT pipeline (voice messages → transcribed text) | ARCHITECTURE.md Task 1 | 2026-03-17 |
| P2 | Implement TTS pipeline (ElevenLabs + pyttsx3 fallback, speed control) | ARCHITECTURE.md Task 1 | 2026-03-17 |
| P2 | Implement screen observer: screenshot + Claude Vision description | ARCHITECTURE.md Task 2 | 2026-03-17 |
| P2 | Implement screen redaction: detect and mask passwords + financial screens | ARCHITECTURE.md Task 2 | 2026-03-17 |
| P2 | Implement Second Brain vault: add/query notes by voice, encrypted | ARCHITECTURE.md Task 3 | 2026-03-17 |
| P2 | Implement orchestrator + planner: intent → tools → execute | ARCHITECTURE.md Task 4 | 2026-03-17 |
| P2 | End-to-end test: voice → Telegram → transcribe → intent → tool → response | Phase 2 gate | 2026-03-17 |
| P2 | Voice installer: complete voice-guided setup from fresh Python install | ARCHITECTURE.md Task 5 | 2026-03-17 |
| P2 | Risk disclosure flow: payment confirmation with spoken warning (full test) | SECURITY_MODEL.md | 2026-03-17 |
| P3 | Voice local interface stub (microphone + speaker on local device) | ARCHITECTURE.md | 2026-03-17 |
| P3 | MCP memory server integration (cross-session user preferences) | INTEGRATION_MAP.md | 2026-03-17 |
| P3 | Add unit tests for security/credentials.py and second_brain/encryption.py | testing.md | 2026-03-17 |
| P3 | Set up CHANGELOG.md and populate ROADMAP.md | open source | 2026-03-17 |
| P3 | Cloud hosting: document Telegram webhook on Railway/Fly.io | cloud-architect | 2026-03-17 |

## Completed Items

| Item | Completed | Cycle # |
|------|-----------|---------|
| Agent network setup (20 agents) | 2026-03-17 | 0 |
| GitHub repo + MCP integration | 2026-03-17 | 0 |
| Autonomous loop infrastructure | 2026-03-17 | 0 |
| Product brief with synthesis vision | 2026-03-17 | 0 |
| docs/GAP_ANALYSIS.md | 2026-03-17 | 1 |
| docs/INTEGRATION_MAP.md | 2026-03-17 | 1 |
| docs/SECURITY_MODEL.md | 2026-03-17 | 1 |
| docs/ETHICS_REQUIREMENTS.md | 2026-03-17 | 1 |
| docs/ARCHITECTURE.md | 2026-03-17 | 1 |
| docs/USER_STORIES.md (21 stories, 5 personas) | 2026-03-17 | 1 |
| docs/FEATURE_PRIORITY.md | 2026-03-17 | 1 |
| src/ project scaffold (Python, 29 source files) | 2026-03-17 | 1 |
| requirements.txt (pinned dependencies) | 2026-03-17 | 1 |
| config.yaml (non-secret configuration) | 2026-03-17 | 1 |
| README.md (screen-reader-friendly, voice setup guide) | 2026-03-17 | 1 |
| .gitignore (credential and vault exclusions) | 2026-03-17 | 1 |
| tools/registry.yaml (curated tool registry) | 2026-03-17 | 1 |
| installer/install.py (voice-guided installer skeleton) | 2026-03-17 | 1 |
| Phase 1: Discovery & Architecture — COMPLETE | 2026-03-17 | 1 |
