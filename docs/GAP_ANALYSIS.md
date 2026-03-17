# Gap Analysis — Blind Assistant

> Written by: gap-analyst agent
> Cycle: 1 — Phase 1 Discovery
> Date: 2026-03-17

---

## Purpose

This document maps the current landscape of assistive technology and AI tools available
to blind users, identifies where each falls short, and defines where Blind Assistant can
create the most meaningful and differentiated impact.

---

## Gap Analysis: Screen Readers

### Existing solutions:
NVDA (free, Windows), JAWS (expensive, Windows), VoiceOver (Apple), Narrator (Windows),
TalkBack (Android). These are the established tools that virtually all blind computer
users depend on today.

### Identified gap:
All screen readers share the same fundamental limitation: **they require the UI to be
accessible.** They read what's labeled. When an app is poorly labeled, uses non-semantic
markup, or presents information purely visually (charts, graphs, image-heavy layouts),
screen readers fail completely. They have zero reasoning capability — they cannot infer
what an unlabeled button probably does, cannot describe a photo, cannot fill in a form
by understanding context.

Additionally, screen readers require **substantial expertise** to use effectively.
NVDA has hundreds of keyboard commands. JAWS requires expensive training. VoiceOver
behaves differently across apps. Newly blind users and elderly blind users face a steep
learning cliff that many never fully overcome.

### Blind Assistant's differentiated opportunity:
Replace the screen reader's "label-reading" limitation with AI vision reasoning. When a
button has no label, Claude can describe what it looks like and what it probably does.
When a form has an image CAPTCHA, Claude can solve it. This is **not a screen reader
replacement** — it is the reasoning layer that fills gaps where screen readers break.

### Impact estimate:
All 7.6 million blind people in the US who use computers. The 30%+ of apps that
consistently break screen readers represent a daily showstopper for this population.
Particularly high impact for newly blind users who haven't mastered screen reader
expertise yet.

### Recommendation: INTEGRATE + BUILD
Integrate alongside existing screen readers — do not replace them. Build the "see and
reason about the screen" capability on top of Claude vision.

---

## Gap Analysis: AI Vision Apps (Be My Eyes, Seeing AI, OrCam)

### Existing solutions:
- **Be My Eyes**: Human volunteers describe photos on demand. ~6 min avg wait time.
- **Be My AI** (ChatGPT Vision in Be My Eyes): AI describes photos. Manual one-shot.
- **Seeing AI** (Microsoft): Text reading, scene description, product recognition.
- **OrCam**: Hardware wearable reads text, recognizes faces. $3,000+ cost.

### Identified gap:
All these tools are **reactive and manual** — the user must initiate a description request
for a specific moment. They cannot:
- Describe what's on the user's computer screen in real time
- Help navigate an application
- Take action based on what they see
- Monitor ongoing situations (e.g., "tell me when my package delivery notification arrives")
- Connect vision to the rest of the user's life context (calendar, notes, preferences)

Be My AI is limited to one image at a time with no persistent context.
Seeing AI only works on the phone camera, not the computer screen.

### Blind Assistant's differentiated opportunity:
Persistent, proactive, **integrated** vision. The assistant can see the screen at any
time, describe what's happening, act on it, and connect what it sees to everything it
knows about the user. This is a fundamentally different capability class.

### Impact estimate:
High for all blind users who use computers. Transformative for users who regularly
encounter inaccessible apps, PDFs, or image-heavy content.

### Recommendation: BUILD (on Claude Vision API)
Not worth integrating Seeing AI or Be My Eyes — Claude Vision is superior for the
desktop use case. OrCam is hardware-only and expensive; out of scope.

---

## Gap Analysis: General-Purpose AI Assistants (Siri, Alexa, ChatGPT, Claude.ai)

### Existing solutions:
Siri, Google Assistant, Alexa — voice assistants with narrow task domains.
ChatGPT and Claude.ai — powerful AI but web-only, cannot control the computer.
Open Interpreter — AI that controls a computer but requires developer-level setup.

### Identified gap:
**None of these are designed around the experience of blindness.** Every single one:
- Requires visual setup and configuration
- Has a visual web interface as the primary use case
- Cannot navigate desktop applications
- Does not understand the user's specific life context (calendar, contacts, preferences)
- Cannot self-install tools to complete tasks it doesn't know how to do yet
- Does not handle the unique security needs (spoken risk disclosures, etc.)

Open Interpreter is the closest existing tool — it controls the computer through natural
language. But it's a developer tool. Setup requires a terminal, Python knowledge, and
sighted configuration. Zero blind users can set it up independently today.

### Blind Assistant's differentiated opportunity:
Be the accessible wrapper for everything Open Interpreter can do, plus:
- Voice-only setup (no terminal)
- Context about the user's life (Second Brain)
- Telegram as the 24/7 interface
- Security model designed for vulnerable users
- Self-expanding capability (install what's needed, with confirmation)

### Impact estimate:
The entire blind user population who wants to use a computer for real work. This is the
core product gap — it's large, deep, and unaddressed by any current tool.

### Recommendation: BUILD ON TOP OF Open Interpreter + Claude
Don't rebuild computer control. Build the accessible layer on top of existing AI
computer control infrastructure.

---

## Gap Analysis: Personal Knowledge Management (Second Brain)

### Existing solutions:
- **Obsidian**: Powerful personal knowledge base. Visual graph interface. Mouse-dependent.
- **Notion**: Collaborative knowledge base. Partially accessible but complex navigation.
- **Mem.ai**: AI-powered memory. Web app requiring visual navigation.
- **Rewind AI**: Records everything you see/hear. Deeply privacy-problematic.
- **Apple Notes, Google Keep**: Simple notes. Accessible but not queryable by AI.

### Identified gap:
**No personal knowledge management tool is accessible to blind users.** Obsidian's graph
view and visual linking are completely unusable. Notion's complex nested structure is
difficult to navigate by screen reader. AI-powered tools like Mem.ai don't have
accessible interfaces.

A blind person currently has:
- Voice memos (unstructured, unsearchable)
- Email (fragmented)
- Memory (lossy, no backup)
- Screen reader-hostile note apps

A sighted person with a Second Brain can query their notes conversationally: "What were
the key points from my doctor's appointment last month?" A blind person cannot do this
with any current tool.

The impact of a queryable personal knowledge base for a blind person is enormous:
medications, appointments, important conversations, contacts, finances — all stored,
all queryable, all voice-accessible.

### Blind Assistant's differentiated opportunity:
Voice-first Second Brain backed by an Obsidian-compatible markdown vault (local files,
no lock-in) with AI-powered conversational query. The user never sees the file structure
— they just talk to their notes.

Key differentiator: **local-first, encrypted, not cloud-dependent**. Blind users often
have health and financial information in their notes. This must be stored locally and
encrypted, not in some startup's database.

### Impact estimate:
Every blind person who wants to manage their life independently. Particularly high impact
for elderly blind users who take medications, have medical appointments, and need to
remember important information. Life-changing rather than merely useful.

### Recommendation: BUILD (Obsidian vault as backend, voice query layer)
Use Obsidian's markdown format (plain files, portable) as the storage format.
Build the voice interface and AI query layer on top. Don't integrate Obsidian directly
(too visual) — use the file format only.

---

## Gap Analysis: Agentic Task Completion / Self-Expanding Capability

### Existing solutions:
- **Claude Code**: Self-expanding, installs tools, browses web, edits files. Developer-only.
- **Open Interpreter**: Similar capability. Developer-only.
- **AutoGPT / AgentGPT**: Autonomous AI agents. Require API keys, visual setup, technical knowledge.
- **Zapier / n8n**: Workflow automation. Visual setup required. Not conversational.

### Identified gap:
**The agentic capability gap is the most critical unmet need.** No tool today allows a
blind person to say "order me food" and have the AI:
1. Ask what service they want (or suggest one)
2. Offer to install/set up the service if not already configured
3. Ask conversational questions to gather what's needed
4. Complete the task with explicit confirmation before spending money
5. Adapt if the service changes or breaks

This is not a narrow gap — it's the entire premise of what an AI life companion should be.
Claude Code does this for code tasks. Nobody does this for life tasks, accessibly.

### Blind Assistant's differentiated opportunity:
The Claude Code pattern, applied to life tasks, with voice-only setup, security
protections, and the blind user's personal context built in.

Self-expanding capability specifically:
- AI detects it needs a tool (e.g., DoorDash integration) it doesn't have
- AI tells the user what it needs and why, asks permission to install
- AI installs and configures it (with user confirmation at each step)
- Task completes

This pattern must work for grocery ordering, travel booking, appointment scheduling,
smart home control, and any future task the user needs.

### Impact estimate:
Transformative for all blind users. The inability to independently order food, book
services, or shop online is a major independence limitation today.

### Recommendation: BUILD (this is the core product differentiator)
This is what makes Blind Assistant different from everything else. It is the primary
development focus after the voice I/O and screen observation foundations are in place.

---

## Gap Analysis: Multi-Device 24/7 Access (Telegram Bot Interface)

### Existing solutions:
- Voice assistants (phone): Siri/Google Assistant — narrow capability, phone-only
- Web apps: require visual browser navigation
- Desktop apps: require installation, visual setup, one device
- SMS bots: exist but typically narrow-task

### Identified gap:
**Blind users need their assistant everywhere.** A screen is not always available.
A laptop is not always accessible. The assistant must be reachable from any device
the user carries — primarily their phone via a messaging app that doesn't require vision.

Telegram is particularly well-suited:
- Works on any phone, tablet, or computer
- Text-based interaction (screen reader compatible)
- Has a bot API that supports rich interactions
- End-to-end encryption available (Secret Chats)
- Works in areas with slow internet
- No visual UI required for basic conversation

### Blind Assistant's differentiated opportunity:
Native standalone apps that work entirely by voice — the user always has their assistant
accessible, on any device, without needing to set up external accounts. This also means
the assistant is available for "ambient" tasks: "remind me to take my medication at 7pm",
"check if my package has arrived", "what's the weather".

### Impact estimate:
High for all users. Native apps remove the Telegram account requirement entirely.

### Recommendation: BUILD (native apps as primary; Telegram as optional super-user channel)
**Update (2026-03-17 founder directive)**: The original recommendation was Telegram as
primary. This has been revised. Telegram requires visual setup that blind users cannot
complete independently. Native apps (Android, iOS, Desktop, Web) are the primary interfaces.
Telegram is available optionally for power users who can set it up. The system must be
fully usable WITHOUT Telegram ever being configured.

---

## Gap Analysis: Accessible Installation and Setup

### Existing solutions:
Every existing tool requires sighted setup. Even tools labeled "accessible" require:
- Reading documentation (often PDF)
- Navigating installer wizards with visual progress indicators
- Configuration through visual menus
- Error messages that reference visual UI elements

### Identified gap:
**There is no AI life assistant tool that a newly blind person can install themselves,
from scratch, without sighted assistance.**

This is not a minor gap — it is the gatekeeping mechanism that keeps nearly every
powerful AI tool inaccessible. If a blind person cannot independently set up the tool,
the tool might as well not exist for them.

### Blind Assistant's differentiated opportunity:
A voice-guided installer that works from first boot:
- Reads its own installation instructions aloud
- Prompts the user for each required step verbally
- Handles errors verbally ("That didn't work. Let me try another way...")
- Confirms each step before proceeding
- Tests itself after setup ("I can hear you. I can see your screen. Setup complete.")

### Impact estimate:
This is a prerequisite for all other features. Without accessible setup, the product
fails for its primary users before they ever use it.

### Recommendation: P1 PRIORITY (prerequisite for everything else)
Before Phase 2 ships, the installer must be voice-guided end-to-end.

---

## Top 5 Highest-Impact Integration Opportunities

**Ranked by: (blind users affected) × (severity of current gap) × (feasibility)**

### 1. Telegram Bot as 24/7 Interface
**Impact**: Every blind user. Immediate, 24/7, any device.
**Feasibility**: HIGH — Telegram Bot API is well-documented, accessible.
**Build complexity**: Medium — requires bot setup, message routing, context management.

### 2. Claude Vision + Screen Observation
**Impact**: Every blind user who encounters inaccessible apps (30%+ of apps they use).
**Feasibility**: HIGH — Claude Vision API is available and capable.
**Build complexity**: Medium — Playwright screenshots + Claude Vision analysis pipeline.

### 3. Voice I/O (Whisper STT + ElevenLabs/Kokoro TTS)
**Impact**: All users — this is the primary interaction modality.
**Feasibility**: HIGH — both are open-source or API-accessible.
**Build complexity**: Medium — latency is the main engineering challenge.

### 4. Voice-First Second Brain (Obsidian Vault + AI Query)
**Impact**: High for all users; transformative for elderly/health-focused users.
**Feasibility**: HIGH — Obsidian markdown is just files; query layer is Claude.
**Build complexity**: Medium — file management + conversational query interface.

### 5. Agentic Task Completion (Self-Expanding Pattern)
**Impact**: Transformative for independence. Differentiates from all current tools.
**Feasibility**: MEDIUM — requires tool integration framework, confirmation flows.
**Build complexity**: High — but this is the product's core value proposition.

---

## Self-Expanding Capability: Architectural Requirements

The "Claude Code for life tasks" pattern requires:

### Discovery
- AI detects a needed capability it lacks
- AI searches a curated registry of vetted integrations (Phase 2+)
- AI presents options to user with plain-language explanation

### Vetting (Supply Chain Security)
- Only install from curated list (no arbitrary packages from user requests)
- Check package against PyPI/npm safety databases before install
- Log: what, why, when, version installed
- Minimal permission scopes — never grant more than needed

### Confirmation
- Spoken announcement: "To order food, I'd like to set up DoorDash integration.
  This will install a small helper. Is that okay?"
- Wait for explicit yes before any installation
- Confirm installation success: "DoorDash is now ready."

### Audit Trail
- All installed tools listed in user-accessible log
- User can review and uninstall any tool at any time by voice
- Uninstall also removes all stored credentials for that tool

### Failure Handling
- If a tool fails to install, try alternative
- If no alternative exists, explain limitation clearly: "I can't set up DoorDash right
  now because [reason]. Would you like to try Instacart instead?"

---

## Summary Table

| Gap | Severity | Existing Tools | Our Approach | Priority |
|-----|----------|----------------|--------------|----------|
| Inaccessible apps | Critical | None | Claude Vision + screen control | P1 |
| No accessible installer | Critical | None | Voice-guided setup script | P1 |
| No AI life companion | Critical | None | Core product | P1 |
| No 24/7 multi-device access | High | Narrow voice assistants | Telegram bot | P1 |
| No Second Brain for blind | High | None | Voice-first Obsidian vault | P2 |
| No agentic task completion | High | Dev tools only | Self-expanding agent | P2 |
| Payment/ordering inaccessible | High | None | Agentic + security model | P2 |
| Travel research + booking | High | None | Compound research+action | P2 |
| Poor screen reader voice quality | Medium | NVDA/JAWS synthetic voices | ElevenLabs/Kokoro TTS | P2 |
| Smart home inaccessibility | Medium | Voice assistants (narrow) | Home Assistant integration | P3 |
