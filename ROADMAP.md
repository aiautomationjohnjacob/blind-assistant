# Roadmap

> This is a living document. Community input shapes priorities.
> See `docs/FEATURE_PRIORITY.md` for the full agent-researched priority list.
> See `docs/CYCLE_STATE.md` for the current sprint status and cycle count.
>
> **Current status**: Phase 5 — Polish & Community Ready (Cycle 37, March 2026)

---

## Phase 1 — Foundation ✅ COMPLETE (Cycle 1)

Architecture, security model, and project scaffold.

- [x] Technology stack decision and architecture document
- [x] Gap analysis of existing accessibility tools (35+ tools evaluated)
- [x] Security model: AES-256-GCM vault, OS keychain, screen redaction, payment tokenization
- [x] Initial project scaffold — Python backend, async, 29 source files
- [x] User stories from 5 blind user personas (21 stories)
- [x] Feature priority ranked by mission impact

---

## Phase 2 — Core Experience ✅ COMPLETE (Cycles 2–10)

The minimum a blind user can actually try end-to-end.

- [x] Voice conversation loop — speak to it, it speaks back (ElevenLabs TTS + pyttsx3 fallback)
- [x] Screen description — "What's on my screen?" → spoken answer via Claude Vision
- [x] Screen redaction — password fields and financial screens never sent to API
- [x] Second Brain — add notes by voice, query your knowledge base, encrypted vault
- [x] Food ordering by voice — complete agentic task via Playwright browser automation
- [x] Risk-disclosure flow — spoken payment warning fires on every financial transaction
- [x] REST API backend — FastAPI server; all 5 clients connect via HTTP
- [x] React Native mobile app — iOS + Android client (Expo SDK)
- [x] First-run setup wizard — voice-guided onboarding, zero visual interaction required
- [x] Real voice recording — 2-press record flow with haptic feedback
- [x] Tool registry + installer — self-expanding capability with user confirmation
- [x] Rate limiting — API server protected against abuse
- [x] Voice E2E demo proven — full pipeline: speech → STT → orchestrator → tool → TTS

**Milestone reached**: A blind user can ask the AI to order food entirely by voice,
including payment risk disclosure and 2-step confirmation, without sighted assistance.

---

## Phase 3 — Blind User Testing 🔄 IN PROGRESS (Cycles 11–, current)

All 5 blind user personas can complete core life-assistant tasks on at least 3 of 5 client platforms.

### Completed in Phase 3

- [x] VoiceOver hint language — outcome-first hints, no "Double-tap" instructions
- [x] Haptic recording cue — Medium haptic on start, Light on stop (accessibility feedback without audio)
- [x] TalkBack/VoiceOver importantForAccessibility fixes
- [x] Live food ordering validation — 11 Playwright integration tests
- [x] CI fully green — 7 jobs, all passing (ruff, mypy, pytest, security-audit, test-js, e2e-web, integration-browser)
- [x] Web app deployed — Netlify staging via deploy-staging.yml
- [x] Expo web export — builds and deploys correctly
- [x] Web E2E accessibility tests — WCAG 2.1 AA keyboard nav, ARIA, lang, title, focus (Chromium + Firefox)
- [x] 118 new unit tests — Telegram bot, query layer, screen redaction, screen observer
- [x] Voice installer refactored — native app setup as Step 1; Telegram demoted to optional Step 5
- [x] Android TalkBack E2E tests — ADBClient wrapper + 8 test scenarios
- [x] iOS VoiceOver E2E tests — SimctlClient wrapper + 9 test scenarios
- [x] Android/iOS CI workflows — triggered on release tags
- [x] Platform helper unit tests — 72 device-free tests for ADB/simctl parsers

### Remaining in Phase 3

- [ ] Android TalkBack device test — AVD emulator run via release tag CI (PRIORITY)
- [ ] iOS VoiceOver device test — iOS Simulator run via macOS runner (PRIORITY)
- [ ] Voice Activity Detection — replace fixed 8s recording with silence detection
- [ ] PIL fallback — Playwright screenshot for headless/server environments
- [ ] MCP memory server — cross-session user preferences and knowledge graph
- [ ] Education website — learn.blind-assistant.org; audio-primary; zero mouse

**Phase 3 complete when**: No SHOWSTOPPER issues from any persona across all scenarios
AND device-simulator captures passing screenshots for Android, iOS, and Web.

---

## Phase 4 — Accessibility Hardening (Planned)

WCAG 2.1 AA on web; native accessibility APIs on iOS/Android; NVDA/JAWS on Desktop.

- [ ] WCAG 2.1 AA audit — zero CRITICAL findings on web (`/audit-a11y` skill)
- [ ] iOS accessibility sign-off — ios-accessibility-expert agent approves VoiceOver flows
- [ ] Android accessibility sign-off — android-accessibility-expert approves TalkBack flows
- [ ] Desktop app — Windows (NVDA/JAWS) + macOS (VoiceOver); Electron or Tauri wrapper
- [ ] NVDA keyboard-only test — entire desktop app navigable without mouse
- [ ] Deafblind support — braille display compatibility (no audio-only feedback)
- [ ] Security specialist sign-off — financial data handling reviewed end-to-end
- [ ] Ethics advisor approval — transaction confirmation flow reviewed
- [ ] Payment tokenization — Stripe integration (never store raw card numbers)
- [ ] Multi-language support foundation — i18n strings prepared

**Phase 4 complete when**: All platform accessibility agents sign off on their platform
AND `/audit-a11y` returns zero CRITICAL findings AND security-specialist approves
financial data handling.

---

## Phase 5 — Polish and Community Ready (Planned)

Onboarding works for non-technical newly-blind users; grant pitch ready; community launch.

- [ ] Dorothy test — elder blind user (65+, low tech confidence) sets up the app,
      orders food, and adds a note to her Second Brain — all without sighted help
- [ ] Zero "What do I do next?" moments — every state has a clear spoken next step
- [ ] CONTRIBUTING.md for blind contributors — accessible development workflow documented
- [ ] Community user testing — partnership with NFB/ACB/APH chapters
- [ ] Grant narrative — fundable impact story with measurable outcomes
- [ ] Public launch announcement — coordinated with blind community organizations
- [ ] Cloud backend option — Railway/Fly.io deployment for users without a local machine

**Phase 5 complete when**: Dorothy passes the above test AND grant-writer produces
`GRANT_NARRATIVE.md` with measurable impact metrics.

---

## Parallel Track — Education Website (`learn.blind-assistant.org`)

*Runs alongside the main app — can be contributed to independently.*

- [ ] Accessible course platform scaffold (React; audio-primary; NVDA+Chrome with zero mouse)
- [ ] Course 1: How to use Blind Assistant (setup → advanced)
- [ ] Course 2: AI literacy for blind users
- [ ] Course 3: Second Brain by voice
- [ ] Course 4: Navigating the digital world (banking, travel, shopping)
- [ ] Course 5: Advocating for yourself (rights, WCAG, reporting)
- [ ] NVDA end-to-end test — any course completable with zero mouse use

---

## What We Will NOT Build

- **Another screen reader** — NVDA and JAWS do this well; we integrate with them
- **A paid tier** — core features are free forever for blind users
- **A desktop GUI that requires vision** — everything is voice-first; visual UI is secondary
- **Anything that requires sighted setup** — this is a hard constraint, always
- **Service-specific API wrappers** (DoorDashTool, TravelBookingTool, etc.) — the browser
  tool handles these via Playwright; Claude reasons about the page like a human would

---

## Tech Stack (Decided)

| Layer | Technology | Reason |
|-------|-----------|--------|
| Python backend | FastAPI + asyncio | AI ecosystem, async, Anthropic SDK |
| Mobile (iOS + Android) | React Native + Expo | Native a11y tree; TalkBack/VoiceOver just work |
| Web client | Expo Web (shared with mobile) | Same components, WCAG 2.1 AA |
| Desktop (Phase 4) | Electron or Tauri wrapping web client | Deferred; architecture decided |
| TTS | ElevenLabs (primary) + pyttsx3 (offline fallback) | Natural voice; resilient offline |
| STT | OpenAI Whisper (local) | Privacy; no audio sent to cloud |
| Vault encryption | AES-256-GCM | Industry standard, authenticated |
| Credentials | OS keychain (keyring library) | No .env files, cross-platform |
| Browser automation | Playwright (wrapped by BrowserTool) | Any website, any task |
| Backend auth | Bearer token (OS keychain stored) | Simple; expandable |

---

## How to Influence the Roadmap

1. Open a [Feature Request](../../issues/new?template=feature_request.md) issue
2. Comment on existing roadmap items with your use case
3. Vote (👍) on issues to signal priority
4. Share your lived experience — "I can't do X today and it costs me Y" is the most
   powerful input we receive
5. If you are blind or visually impaired, your direct feedback is especially valued —
   open an issue using the Accessibility Issue template
