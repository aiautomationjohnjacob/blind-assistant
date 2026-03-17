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
| P1 | Fix `_get_vault` silent failure: prompt for passphrase via voice when keychain has no key | Cycle 2 review | 2026-03-17 |
| P2 | End-to-end Telegram demo: send text/voice → get real spoken response back | Phase 2 gate | 2026-03-17 |
| P2 | Voice installer: complete voice-guided setup from fresh Python install | ARCHITECTURE.md Task 5 | 2026-03-17 |
| P2 | Integration test: Telegram message → Whisper STT → orchestrator → TTS → reply | Phase 2 gate | 2026-03-17 |
| P3 | Voice Activity Detection (VAD) for voice_local.py (replaces fixed recording duration) | Cycle 2 review | 2026-03-17 |
| P3 | PIL ImageGrab Playwright fallback for headless/server environments | Cycle 2 review | 2026-03-17 |
| P3 | MCP memory server integration (cross-session user preferences) | INTEGRATION_MAP.md | 2026-03-17 |
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
| voice_local.py (local voice interface) | 2026-03-17 | 2 |
| second_brain/query.py (voice query layer over vault) | 2026-03-17 | 2 |
| Orchestrator real intent routing (screen/note/query/general) | 2026-03-17 | 2 |
| Vault microsecond filename uniqueness fix | 2026-03-17 | 2 |
| 244 unit tests (encryption, vault, orchestrator, security) | 2026-03-17 | 2 |
| conftest.py suppress_audio ImportError fix | 2026-03-17 | 2 |
| Voice local interface stub (microphone + speaker) | 2026-03-17 | 2 |
| Unit tests: security/credentials, disclosure, encryption, vault | 2026-03-17 | 2 |
