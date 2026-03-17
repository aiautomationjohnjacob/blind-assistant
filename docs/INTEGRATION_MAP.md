# Integration Map — Blind Assistant

> Written by: gap-analyst agent
> Cycle: 1 — Phase 1 Discovery
> Date: 2026-03-17

---

## Purpose

For every tool in the product vision, this document answers:
1. What does the tool do well?
2. Where does it fail blind users?
3. How do we integrate it (vs rebuild it)?
4. What accessibility wrappers are needed?
5. What is the integration priority?

---

## Integration Strategy Overview

Our core principle: **synthesize, don't rebuild.**

The existing tools landscape is rich. The problem is always the same: accessible wrapper
missing, sighted setup required, no conversational interface, no connection to the rest of
the user's life. We build the connective tissue, not the underlying capabilities.

**Integration tiers:**
- **Tier 1 (Core)**: Must be integrated in Phase 2. Product fails without these.
- **Tier 2 (High Value)**: Integrate in Phase 2-3. Dramatically expands capability.
- **Tier 3 (Enhanced)**: Phase 3-4. Improves experience significantly.
- **Tier 4 (Future)**: Phase 4+. Nice to have once core is solid.

---

## Tier 1: Core Integrations

### 1.1 Claude Vision API (Anthropic)
**Purpose**: See the user's screen; describe images, documents, and interfaces.
**Accessibility gap in original**: Claude.ai web interface requires sighted navigation.
**Our integration**: Programmatic API calls — no web interface needed.

**Integration approach**:
- Playwright takes screenshots of the desktop or specific apps
- Screenshot sent to Claude Vision API with context prompt
- Response returned as text/speech to user
- For sensitive screens (password fields, financial data): detect and mask before sending

**Accessibility wrappers needed**:
- Auto-detect password fields and exclude from screenshots (never send to API)
- Redact financial account numbers before API call
- Allow user to say "describe my screen" or trigger automatically on navigation

**Accessibility gaps in Claude Vision**: None for our use case — we control the interface.

**Priority**: TIER 1 — Core capability

---

### 1.2 Telegram Bot API
**Purpose**: 24/7 multi-device interface. The user's primary access channel.
**Accessibility gap in original**: Telegram app is accessible via screen readers.
                                   Bot API is text-based — inherently accessible.
**Our integration**: Python `python-telegram-bot` library.

**Integration approach**:
- Bot responds to text and voice messages
- User can send voice messages; Whisper transcribes them
- Bot responds with text (available to screen reader / braille display)
- Optional: bot responds with voice message (ElevenLabs TTS)
- Security: whitelist by Telegram user ID; reject all other users

**Accessibility wrappers needed**:
- Voice message → Whisper transcription → intent processing
- Text response structured for braille displays (40-char chunks, no emoji)
- "Reply with voice" option for users who prefer audio

**Accessibility gaps in Telegram itself**: Telegram app is generally screen reader
accessible. No significant gaps for bot interaction.

**Priority**: TIER 1 — Primary interface

---

### 1.3 Whisper (OpenAI Speech-to-Text)
**Purpose**: Transcribe user's speech to text. Voice-first interaction requires this.
**Accessibility gap in original**: N/A — Whisper is an API/library, not a user interface.
**Our integration**: `openai-whisper` library (open-source, runs locally).

**Integration approach**:
- Microphone capture (system default or user-configured)
- Audio streamed or sent in chunks to Whisper
- Transcription returned as text for intent processing
- Support for voice memos sent via Telegram

**Accessibility considerations**:
- Run locally where possible (privacy — speech never leaves device)
- Whisper large-v3 is highly accurate across accents and speech patterns
- Support word-by-word transcription for real-time feedback

**Priority**: TIER 1 — Voice input without this is impossible

---

### 1.4 Text-to-Speech: ElevenLabs / Kokoro
**Purpose**: High-quality voice output. Dramatically better than screen reader voices.
**Accessibility gap in original**: ElevenLabs web UI is not relevant — API only.
**Our integration**: ElevenLabs API (cloud) or Kokoro TTS (local, open-source).

**Integration approach**:
- All AI responses can be spoken aloud
- User-configurable: voice, speed, pitch
- Kokoro as offline fallback (lower quality but functional without internet)
- DeafBlind mode: text only, no audio

**Accessibility considerations**:
- Speed control is critical — Dorothy (elderly user) needs slower speech
- Verbosity control is critical — Marcus (power user) needs concise responses
- DeafBlind users must have text-only mode as a first-class option
- All spoken output must also be available as text (for braille displays)

**Priority**: TIER 1 — Voice output is core to the product

---

### 1.5 Playwright (Browser Computer Control)
**Purpose**: Control web browsers to complete tasks on the user's behalf.
**Accessibility gap in original**: Playwright is a developer tool; no user-facing UI.
**Our integration**: Playwright MCP or direct Python API.

**Integration approach**:
- Navigate to websites, fill forms, click buttons
- Extract text content from web pages
- Take screenshots for Claude Vision analysis
- Handle login flows, checkout processes, etc.

**Accessibility considerations**:
- Never fill password fields without user confirmation per-session
- Log all browser actions (what was clicked, what was filled)
- User can request "show me what you're doing" for any browser action

**Priority**: TIER 1 — Required for web task completion

---

### 1.6 Desktop Commander MCP (Native App Control)
**Purpose**: Control native desktop applications (not just browsers).
**Accessibility gap in original**: Developer tool; no user-facing UI.
**Our integration**: Desktop Commander MCP already available in this environment.

**Integration approach**:
- Keyboard simulation for native app navigation
- Screenshot + describe for any native app
- File system operations (open, read, save documents)
- Process management (launch apps, close apps)

**Priority**: TIER 1 — Required for full computer control

---

## Tier 2: High-Value Integrations

### 2.1 Obsidian Vault (Second Brain Storage)
**Purpose**: Personal knowledge base backend. The "memory" for the user's life.
**Accessibility gap in original**: Obsidian's visual graph interface is completely
inaccessible. Mouse-dependent navigation. Complex visual plugin ecosystem.
**Our integration**: Use Obsidian's markdown file format ONLY — don't use Obsidian app.

**Integration approach**:
- Store all notes as plain markdown files in a user-specified directory
- Obsidian vault format = plain directory of `.md` files with YAML frontmatter
- AI reads/writes files directly — user never interacts with Obsidian app
- Voice query: "What did I write about my doctor appointment last month?"
  → AI searches vault files, returns relevant content
- Voice note: "Add a note: I need to refill my blood pressure medication before Friday"
  → AI creates/updates appropriate note file

**Accessibility wrappers needed**:
- Vault directory setup via voice (no file browser)
- Encryption at rest (AES-256 for vault directory)
- Conversational query interface — no visual search required
- Auto-organize notes by date, topic, and entity (person, place, medication)

**Accessibility gaps in Obsidian itself**: Significant — entire app is inaccessible.
**Resolution**: Don't use the app at all. Use the file format only.

**Priority**: TIER 2 — Major independence feature; Phase 2 target

---

### 2.2 MCP Memory Server (Cross-Session Context)
**Purpose**: Remember the user across sessions. The assistant's persistent memory.
**Accessibility gap in original**: N/A — this is a background service.
**Our integration**: Already available in this environment.

**Integration approach**:
- Store user preferences (voice speed, verbosity level, preferred apps)
- Store important context (user's name, location, common tasks)
- Store installed tool registry
- Retrieve context at session start to personalize responses immediately

**Priority**: TIER 2 — Required for personalization

---

### 2.3 Home Assistant Integration
**Purpose**: Smart home control by voice through the assistant.
**Accessibility gap in original**: Home Assistant UI is partially accessible but complex.
**Our integration**: Home Assistant REST API or WebSocket API.

**Integration approach**:
- User says "turn off the living room lights"
- Assistant translates to Home Assistant API call
- Confirmation: "Living room lights are now off"

**Accessibility wrappers needed**:
- Device discovery via voice: "What smart home devices do I have?"
- Grouping by room, type for easier voice reference
- Status queries: "Is the front door locked?"

**Priority**: TIER 2 — High independence impact for home management

---

### 2.4 DoorDash / Instacart APIs (Food and Grocery Ordering)
**Purpose**: Order food and groceries by voice.
**Accessibility gap in original**: DoorDash/Instacart apps have partial accessibility but
require extensive navigation through complex menus and carts.
**Our integration**: Official partner APIs where available; Playwright automation otherwise.

**Integration approach**:
- User: "Order me a pizza"
- Assistant: "Which service do you want to use — DoorDash, Instacart, or something else?"
- Assistant guides through selection conversationally
- Before any payment details: mandatory spoken risk disclosure
- Confirm order details before submitting: "I'm about to order a large pepperoni pizza
  from Domino's for $18.99. Shall I place the order?"
- After order: confirmation with estimated delivery time

**Security requirements** (from SECURITY_MODEL.md):
- Payment card tokens only — never store raw card numbers
- Risk disclosure spoken aloud before any payment details accepted
- Order confirmation required before submission

**Priority**: TIER 2 — Core independence use case from product brief

---

### 2.5 Travel Booking (Expedia/Booking.com APIs or Playwright)
**Purpose**: Research and book travel entirely by conversation.
**Accessibility gap in original**: Travel booking sites have poor screen reader support,
complex date pickers, multi-step checkout flows.
**Our integration**: Travel booking APIs where available; Playwright for complex flows.

**Integration approach**:
- Compound task: research + recommendation + booking in one conversation
- "I want to take a vacation but I don't know where"
  → Research accessible destinations, travel options for blind users
  → Present options conversationally with spoken summaries
  → User chooses → gather required details through conversation
  → Book with explicit confirmation before payment
- Same security requirements as food ordering

**Priority**: TIER 2 — Core independence use case from product brief

---

## Tier 3: Enhanced Integrations

### 3.1 n8n / Zapier (Background Workflow Automation)
**Purpose**: Automate recurring tasks without user intervention.
**Accessibility gap in original**: n8n has a visual node-based interface; inaccessible.
**Our integration**: n8n REST API for programmatic workflow creation.

**Integration approach**:
- User describes recurring task: "Remind me every day at 7pm to take my medication"
- Assistant creates n8n workflow via API — user never sees the visual interface
- Workflows run in background; assistant notifies user of results

**Priority**: TIER 3 — Enhances automation but not core Phase 2 requirement

---

### 3.2 Calendar Integration (Google Calendar / iCal)
**Purpose**: Manage appointments and reminders by voice.
**Accessibility gap in original**: Google Calendar has partial accessibility; complex UI.
**Our integration**: Google Calendar API or CalDAV.

**Integration approach**:
- "Add a doctor's appointment for March 20th at 2pm"
- "What do I have on Wednesday?"
- Integration with Second Brain: "After my cardiology appointment, remind me to ask about..."

**Priority**: TIER 3 — High value for scheduling; Phase 3 feature

---

### 3.3 Email Integration (Gmail / IMAP)
**Purpose**: Read, compose, and send email by voice.
**Accessibility gap in original**: Gmail has decent accessibility but complex interface.
**Our integration**: Gmail API or IMAP.

**Integration approach**:
- "Read me my latest emails"
- "Reply to Sarah saying I'll be there at 3"
- "Search my email for the confirmation from the doctor's office"

**Priority**: TIER 3 — Important productivity feature; Phase 3

---

### 3.4 Seeing AI / Azure Computer Vision (Object/Text Recognition)
**Purpose**: Recognize text in images, photos, and physical environment.
**Accessibility gap in original**: Seeing AI phone app is reasonably accessible.
**Our integration**: Microsoft Azure Computer Vision API.

**Integration approach**:
- "What does this image say?" (user sends photo via Telegram)
- "Read the text in this PDF scan"
- Integration with screen observation for OCR of non-text UI elements

**Priority**: TIER 3 — Claude Vision covers most of this; Azure CV for edge cases

---

## Tier 4: Future Integrations

### 4.1 WhatsApp / SMS Bot (Alternative Interface)
**Purpose**: Reach users who don't use Telegram.
**Priority**: TIER 4 — native apps cover all primary use cases; Telegram is optional super-user only

### 4.2 Amazon / eBay APIs (Shopping)
**Purpose**: Order physical goods by voice.
**Priority**: TIER 4 — Instacart covers grocery; general shopping Phase 4+

### 4.3 Healthcare APIs (Appointment Booking, Prescription Refills)
**Purpose**: Book medical appointments and manage prescriptions.
**Priority**: TIER 4 — High value but complex compliance requirements (HIPAA)

### 4.4 Banking/Financial Integration (Read-Only)
**Purpose**: Check balances, review transactions by voice.
**Priority**: TIER 4 — Read-only first; very high security requirements; Phase 4+

---

## Integration Architecture: Key Technical Decisions

### Tool Registry Design
All integrations are implemented as "tools" in a registry:
```python
# Each tool follows this interface
class Tool:
    name: str                    # "doordash", "obsidian", "home_assistant"
    description: str             # Plain-language description for AI planner
    requires_credentials: bool   # If True, credential flow required before use
    install_command: str | None  # If set, can be self-installed

    def can_execute(self, task: str) -> bool  # Can this tool handle this task?
    def execute(self, task: str, context: dict) -> ToolResult
```

### Self-Expanding Pattern
```
1. User request arrives
2. Planner agent: "What tools are needed?"
3. For each needed tool:
   a. Check tool registry — installed and configured?
   b. If not: find in available_tools catalog
   c. Announce to user: "I need to set up [tool] to do this. OK?"
   d. Wait for confirmation
   e. Install and configure with user guidance
4. Execute task with confirmed tools
5. Confirm completion or explain failure
```

### Credential Management
- Never stored in plain text files or environment variables
- Stored in OS keychain (Linux: libsecret/keyring; macOS: Keychain; Windows: Credential Store)
- Token rotation tracked and handled automatically
- User can list and revoke all stored credentials by voice

### Communication Security
- All external API calls over TLS
- Telegram: standard API (not E2E) — user warned that Telegram is not E2E by default
- Screenshot content: sensitive regions redacted before any API call
- Conversation logs: encrypted at rest if stored, with user-controlled key

---

## Integration Map Summary

| Tool | Tier | Phase | Integration Method | Accessibility Wrapper |
|------|------|-------|-------------------|----------------------|
| Claude Vision API | 1 | 2 | Direct API | Screenshot pipeline + redaction |
| Telegram Bot API | 1 | 2 | python-telegram-bot | Voice input + braille-safe output |
| Whisper STT | 1 | 2 | Local library | Microphone pipeline |
| ElevenLabs/Kokoro TTS | 1 | 2 | API + local fallback | Speed/verbosity control |
| Playwright (browser) | 1 | 2 | MCP or Python API | Action logging + confirmation |
| Desktop Commander | 1 | 2 | MCP | Voice-triggered actions |
| Obsidian Vault | 2 | 2 | File system (no app) | Voice query + encrypted storage |
| MCP Memory Server | 2 | 2 | MCP (existing) | Session context management |
| Home Assistant | 2 | 3 | REST API | Voice device control |
| DoorDash/Instacart | 2 | 2 | API or Playwright | Risk disclosure + confirmation |
| Travel booking | 2 | 3 | API or Playwright | Compound research+book flow |
| n8n Automation | 3 | 3 | REST API | Voice workflow creation |
| Google Calendar | 3 | 3 | Calendar API | Voice appointment management |
| Email (Gmail/IMAP) | 3 | 3 | Gmail API | Voice email management |
| Azure Computer Vision | 3 | 3 | API | OCR + image description |
| WhatsApp/SMS | 4 | 4 | Twilio/WhatsApp API | Alternative interface |
| Amazon/eBay | 4 | 4 | Product APIs | Voice shopping |
| Healthcare APIs | 4 | 4 | Various | HIPAA-compliant wrapper |
| Banking (read-only) | 4 | 4 | Plaid API | Security-hardened, read-only |
