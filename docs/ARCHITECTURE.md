# Technical Architecture — Blind Assistant

> Written by: tech-lead agent
> Input documents: PRODUCT_BRIEF.md, GAP_ANALYSIS.md, INTEGRATION_MAP.md,
>                  SECURITY_MODEL.md, ETHICS_REQUIREMENTS.md
> Cycle: 1 — Phase 1 Discovery
> Date: 2026-03-17

---

## Stack Decision

### Language: Python 3.11+

**Rationale**:
- Best ecosystem for AI integrations (LangChain, OpenAI SDKs, Anthropic SDK, Whisper)
- Telegram bot library (`python-telegram-bot`) is mature and well-maintained
- Playwright has first-class Python support
- `keyring` library provides cross-platform OS keychain access
- `cryptography` library provides industrial-grade encryption primitives
- Lower barrier for contributors from the AI/ML space who will care about this project

**Tradeoffs**:
- Not as fast as Rust/Go for I/O intensive tasks — mitigated by async Python (`asyncio`)
- GIL limits CPU parallelism — not relevant for our I/O-bound workload

### Runtime: Async Python (asyncio)

Voice I/O, Telegram events, API calls, and screen observation all need to happen
concurrently without blocking. The entire application is async from the start.

### Primary Interfaces: Native Apps

**Update (2026-03-17 founder directive)**: The original architecture placed Telegram as
the primary interface. This has been revised. Telegram requires visual setup (QR scanning,
phone verification, account creation on Telegram's website) that blind users cannot complete
independently — making it incompatible with the project's core requirement of zero-visual-setup.

The primary interfaces are **native standalone apps** built specifically for blind users:
- Android app (TalkBack) — setupable entirely by voice from first launch
- iOS app (VoiceOver) — setupable entirely by voice from first launch
- Desktop app, Windows + macOS (NVDA / VoiceOver) — voice-guided installer
- Web app (NVDA+Chrome, VoiceOver+Safari) — no download required

All clients connect to the **Python backend via REST API** (FastAPI, localhost for dev).

Telegram remains available as an **optional super-user channel** for power users who want
remote access and are able to set it up. It is never required, never default, never the
primary demo target. The voice_local.py CLI and the Desktop app are the Phase 2 demo
targets.

---

## Execution Model: Phone Talks to User's Own Machine

This is the core architectural pattern — and it's what makes the tool powerful:

```
[User's phone/tablet]          [User's desktop/home server]
   Android app          ──▶   Python backend (FastAPI)
   iOS app              ──▶     │
   (voice in/out only)          ├── Playwright browser (navigates any website)
                                ├── Desktop Commander (controls native apps)
                                ├── Claude Vision (sees the screen)
                                └── Second Brain vault (user's data, local)
```

The phone is just a voice terminal. All the intelligence — AI reasoning, browser
control, screen observation, data storage — runs on the user's own machine. This means:

- **No cloud dependency for sensitive data**: Second Brain vault never leaves the user's machine
- **No service-specific code**: Playwright navigates DoorDash, Expedia, any bank website the
  same way a human would — Claude reasons about the page, fills in forms, clicks buttons
- **Any task is possible**: If a service has a website, the app can use it. No API deal required.
- **User's computer does the work**: The phone app says "order me pad thai", the desktop
  opens a browser, finds a delivery service, places the order, confirms with the user

Cloud hosting (Railway/Fly.io) is a future option for users who want always-on access
without keeping their computer on, but the default and preferred deployment is local.

**When to build specific integrations instead of using the browser:**
- Payment tokenization (Stripe SDK — never handle raw card numbers in a browser)
- Services requiring OAuth that need background refresh (Google Calendar, Gmail)
- Local hardware protocols that aren't web-accessible (Home Assistant REST API)
- Anything where browser automation would be brittle due to heavy JavaScript rendering

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                CLIENT APPS (voice terminals)                      │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Android app │  │  iOS app   │  │ Desktop  │  │  Web app   │  │
│  │ (TalkBack) │  │(VoiceOver) │  │(NVDA/VO) │  │(NVDA+Chr.) │  │
│  └──────┬─────┘  └──────┬─────┘  └────┬─────┘  └──────┬─────┘  │
└─────────┼───────────────┼─────────────┼────────────────┼────────┘
          └───────────────┴──────REST API┴────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              PYTHON BACKEND (runs on user's own machine)          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │   Local Voice Interface (microphone + speaker; desktop)   │   │
│  └──────────────────────────┬───────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────┘
             │                             │
             ▼                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INPUT PIPELINE                                 │
│  Voice message → Whisper STT → Text                              │
│  Text message → Direct text                                      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR / PLANNER                         │
│                                                                   │
│  - Intent classification (what does the user want?)              │
│  - Tool selection (which tools/integrations are needed?)         │
│  - Gap detection (does a needed tool need to be installed?)      │
│  - Confirmation management (what requires user approval?)        │
│  - Context injection (Second Brain, memory, user preferences)    │
│                                                                   │
│  Model: Claude API (claude-sonnet-4-x for speed,                 │
│          claude-opus for complex planning)                        │
└───┬───────────┬───────────┬───────────┬───────────┬─────────────┘
    │           │           │           │           │
    ▼           ▼           ▼           ▼           ▼
┌──────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌──────────────┐
│Screen│  │Second  │  │Browser │  │Desktop │  │ Task Agents  │
│Obs.  │  │Brain   │  │Control │  │Control │  │ (food, travel│
│      │  │(Vault) │  │(Play-  │  │(Desktop│  │  shopping,   │
│Claude│  │        │  │wright) │  │Cmdr    │  │  calendar)   │
│Vision│  │Local   │  │        │  │MCP)    │  │              │
└──────┘  └────────┘  └────────┘  └────────┘  └──────────────┘
                                                      │
                                          ┌───────────┴───────────┐
                                          │   Tool Registry        │
                                          │   (curated plugins)    │
                                          └───────────────────────┘
    │           │           │           │           │
    ▼           ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SECURITY LAYER                                 │
│  - Screenshot redaction (before any external API call)           │
│  - Credential access (OS keychain only)                          │
│  - Confirmation gate (high-stakes action approval)               │
│  - Audit log (all actions, all installs)                         │
│  - Risk disclosure (financial actions)                           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT PIPELINE                                │
│                                                                   │
│  Text response → ElevenLabs TTS (cloud) or Kokoro (local)       │
│  → Speed/verbosity control → Speaker or Telegram voice message  │
│  → Braille-safe text → Telegram text message                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repository Layout

The repo is split by deployment unit. Never mix code across boundaries.

```
blind-assistant/
│
├── src/                         ← PYTHON BACKEND (the only thing that runs AI)
│   └── blind_assistant/
│       ├── core/                # Orchestrator, planner, context, confirmation
│       ├── interfaces/          # voice_local.py, api_server.py, telegram_bot.py
│       ├── voice/               # stt.py (Whisper), tts.py (ElevenLabs/Kokoro)
│       ├── vision/              # screen_observer.py, redaction.py, ocr.py
│       ├── second_brain/        # vault.py, encryption.py, query.py
│       ├── tools/               # browser/, desktop/ — general capabilities only
│       ├── security/            # credentials.py, disclosure.py, sanitize.py
│       └── memory/              # mcp_memory.py
│
├── android/                     ← ANDROID CLIENT (Kotlin/React Native/Flutter — TBD)
│   └── (created after ARCH DECISION — calls src/ backend via REST API)
│
├── ios/                         ← iOS CLIENT (Swift/React Native/Flutter — TBD)
│   └── (created after ARCH DECISION — calls src/ backend via REST API)
│
├── desktop/                     ← DESKTOP CLIENT (Windows + macOS)
│   └── (Phase 3 — may wrap voice_local.py or be a separate native app)
│
├── web/                         ← WEB CLIENT (TypeScript/React — TBD)
│   └── (Phase 3 — calls src/ backend via REST API)
│
├── shared/                      ← SHARED API TYPES (used by all clients)
│   └── api_types/               # Request/response schemas (JSON Schema or OpenAPI)
│
├── installer/                   # Voice-guided setup script (Python)
├── tools/registry.yaml          # Approved packages for self-expanding capability
├── tests/                       # unit/, integration/, accessibility/, e2e/
├── docs/                        # Architecture, user stories, gap analysis, etc.
├── config.yaml                  # Non-secret configuration
└── requirements.txt             # Python backend dependencies only
```

**Rule**: `src/` is Python only. `android/`, `ios/`, `web/` use their own language and
build tools. They never import from `src/` — they call it over HTTP. The `shared/`
directory holds only language-agnostic schemas (OpenAPI/JSON Schema) so all clients
stay in sync with the backend API contract.

### Tools: Capabilities, Not Pre-Built Wrappers

`src/blind_assistant/tools/` contains **general capabilities** that Claude uses
autonomously — NOT hardcoded wrappers for specific services:

```
tools/
├── browser/          # Playwright-based web browser control
│   └── playwright_tool.py   # Claude navigates ANY website by reasoning about it
│
└── desktop/          # Desktop Commander — controls native apps
    └── desktop_commander.py  # Claude controls ANY app by seeing the screen
```

**There is no `ordering/doordash.py`, no `travel/booking.py`, no `home/home_assistant.py`.**
Claude uses the browser tool and figures out how to order food on DoorDash the same way
a human does — by navigating the website. This means:
- Zero maintenance when DoorDash changes their UI
- Works for ANY ordering/travel/home service, not just pre-approved ones
- Claude can handle novel services the founders never anticipated
- The only pre-built integrations worth building are APIs that require OAuth or special
  auth that can't be done via browser (e.g. Home Assistant local API, Stripe tokenization)

`tools/registry.yaml` lists approved **packages** (Playwright, aiohttp) that the
self-expanding capability can install — not approved services. The services are open-ended.

---

## Core Patterns

### 1. The Orchestration Loop

```python
# src/blind_assistant/core/orchestrator.py (simplified)

async def handle_user_input(text: str, context: UserContext) -> Response:
    # 1. Classify intent
    intent = await planner.classify_intent(text, context)

    # 2. Check what tools are needed
    required_tools = await planner.identify_tools(intent)

    # 3. Self-expanding: install any missing tools
    for tool in required_tools:
        if not tool_registry.is_installed(tool):
            confirmed = await confirmation.ask_install(tool)
            if confirmed:
                await installer.install(tool)

    # 4. Security gate: any high-stakes actions?
    for action in intent.actions:
        if action.is_high_stakes:
            confirmed = await confirmation.ask_action(action)
            if not confirmed:
                return Response("Cancelled. Let me know if you'd like to do something else.")

    # 5. Execute
    result = await executor.run(intent, context)

    # 6. Format response for output channel
    return formatter.format(result, context.output_preferences)
```

### 2. Tool Interface

```python
# src/blind_assistant/tools/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ToolResult:
    success: bool
    message: str          # Plain English result description
    data: dict | None     # Structured data if needed
    actions_taken: list[str]  # Audit trail

class Tool(ABC):
    name: str
    description: str      # Plain English, for AI planner
    requires_credentials: bool
    allowed_endpoints: list[str]  # Security: only these URLs

    @abstractmethod
    async def can_handle(self, task: str) -> bool:
        """Can this tool handle this task description?"""

    @abstractmethod
    async def execute(self, task: str, context: dict) -> ToolResult:
        """Execute the task and return a result."""
```

### 3. Confirmation Gate

```python
# src/blind_assistant/core/confirmation.py

class ConfirmationGate:
    async def ask_action(self, action: Action) -> bool:
        """
        Speak a confirmation request and wait for user response.
        Returns True if confirmed, False if cancelled.
        """
        message = self._build_confirmation_message(action)
        await tts.speak(message)

        response = await self._wait_for_response(timeout=30)
        return response.lower() in {"yes", "confirm", "ok", "do it", "go ahead"}

    async def ask_financial_action(self, action: FinancialAction) -> bool:
        """
        Financial actions require risk disclosure first, then confirmation.
        This is non-negotiable per SECURITY_MODEL.md and ETHICS_REQUIREMENTS.md
        """
        # Step 1: Risk disclosure (always, every time)
        await tts.speak(FINANCIAL_RISK_DISCLOSURE)
        understood = await self._wait_for_response(timeout=60)
        if understood.lower() not in {"yes", "continue", "i understand", "ok"}:
            return False

        # Step 2: Specific action confirmation
        return await self.ask_action(action)

FINANCIAL_RISK_DISCLOSURE = """
Before you share payment details, I need to tell you something important.
Providing financial information to any app — including this one — carries some risk.
We protect your data with encryption and never store card numbers in plain text.
But please only share payment information you're comfortable sharing with a digital assistant.
You can remove your payment information at any time.
Do you want to continue?
"""
```

### 4. Screen Observation Pipeline

```python
# src/blind_assistant/vision/screen_observer.py

async def describe_screen(region: ScreenRegion | None = None) -> str:
    """
    Take screenshot, redact sensitive content, get AI description.
    Never writes screenshot to disk. Never sends sensitive screens to API.
    """
    # 1. Capture (in memory only)
    screenshot_bytes = await capture_screenshot(region)

    # 2. Check for sensitive content
    sensitivity = await redaction.analyze(screenshot_bytes)

    if sensitivity.has_password_fields:
        # Never send password fields to external API
        return "I can see a screen with password fields. I've protected this screen — I won't describe the content of password fields."

    if sensitivity.has_financial_content:
        await tts.speak("I can see a financial page. Protecting this screen.")
        # Use local description only
        return await local_vision.describe(screenshot_bytes)

    # 3. Redact any detected sensitive regions
    redacted_bytes = await redaction.apply(screenshot_bytes, sensitivity)

    # 4. Send to Claude Vision
    description = await claude_vision.describe(redacted_bytes)

    return description
```

### 5. Second Brain Query

```python
# src/blind_assistant/second_brain/query.py

async def query_vault(question: str, vault: EncryptedVault) -> str:
    """
    Answer a question using the user's personal knowledge base.
    All processing happens locally — vault content never sent externally
    except as anonymous search queries.
    """
    # 1. Search vault for relevant notes (local, no API)
    relevant_notes = await vault.search(question)

    if not relevant_notes:
        return "I don't have any notes about that. Would you like me to add a note on this topic?"

    # 2. Ask Claude to synthesize an answer from notes
    # Note: sends note content to Claude API — user was informed at setup
    answer = await claude.synthesize(
        question=question,
        context=relevant_notes,
        instruction="Answer the user's question based only on their personal notes. Be concise."
    )

    return answer
```

---

## Voice-Only Installation Architecture

The installer must work from zero — no sighted assistance required.

### Installer Design

```python
# installer/install.py

"""
Blind Assistant Voice-Guided Installer

To start: python install.py

The installer will:
1. Speak instructions aloud (no reading required)
2. Wait for verbal responses at each step
3. Confirm each step before proceeding
4. Test itself after setup
"""

async def run_installer():
    # Use system TTS (pyttsx3) before ElevenLabs is configured
    # pyttsx3 works out of the box on all platforms, no API key needed
    tts = SystemTTS()

    await tts.speak(
        "Welcome to Blind Assistant setup. I'll guide you through everything by voice. "
        "This will take about 5 minutes. Say 'ready' when you're ready to start."
    )

    await wait_for_ready()

    # Step-by-step voice-guided configuration
    await setup_telegram(tts)         # Get Telegram bot token
    await setup_claude_api(tts)       # Get Claude API key
    await setup_whisper(tts)          # Download Whisper model
    await setup_tts(tts)              # Configure voice output
    await setup_security(tts)         # Configure Telegram user whitelist
    await setup_vault(tts)            # Create Second Brain vault
    await run_tests(tts)              # Self-test all components

    await tts.speak(
        "Setup complete. I can hear you, I can see your screen, and your notes are ready. "
        "You can now talk to me in Telegram or use the voice shortcut we just set up. "
        "What would you like to do first?"
    )
```

---

## Security Implementation Summary

See SECURITY_MODEL.md for full specification. Key implementation points:

| Concern | Implementation |
|---------|----------------|
| API keys | OS keychain via `keyring` library |
| Vault encryption | AES-256-GCM via `cryptography` library |
| Screenshots | Memory-only; redacted before any API call |
| Payment cards | Stripe tokenization only; never stored raw |
| Telegram auth | User ID whitelist in OS keychain |
| Prompt injection | System prefix on all screen content |
| Dependency vetting | `pip-audit` in CI; pinned versions |
| Action audit | All actions logged to encrypted audit file |

---

## First 5 Implementation Tasks

### Task 1: Core Infrastructure (Week 1)
**Goal**: Async Python skeleton with Telegram bot + Whisper STT + basic TTS

Deliverables:
- `src/blind_assistant/main.py` — starts Telegram bot
- `src/blind_assistant/interfaces/telegram_bot.py` — receives text and voice messages
- `src/blind_assistant/voice/stt.py` — Whisper transcription of voice messages
- `src/blind_assistant/voice/tts.py` — ElevenLabs + pyttsx3 fallback
- `src/blind_assistant/security/credentials.py` — OS keychain access
- Basic echo test: send voice message → transcribed → echoed back as voice

**Why first**: Everything else depends on this pipeline working.

---

### Task 2: Screen Observation (Week 1-2)
**Goal**: Take screenshot, redact sensitive content, describe with Claude Vision

Deliverables:
- `src/blind_assistant/vision/screen_observer.py`
- `src/blind_assistant/vision/redaction.py` — password field + financial content detection
- Basic command: "What's on my screen?" → spoken description
- Tests: verify password fields are never sent to API

**Why second**: Core differentiating capability. Proves the vision architecture works.

---

### Task 3: Second Brain MVP (Week 2)
**Goal**: Voice-add and voice-query personal notes, encrypted on disk

Deliverables:
- `src/blind_assistant/second_brain/vault.py`
- `src/blind_assistant/second_brain/encryption.py`
- `src/blind_assistant/second_brain/query.py`
- Commands: "Add a note: [content]" / "What do I know about [topic]?"
- Encryption verified: vault unreadable without passphrase

**Why third**: Second Brain is a core independence feature and the foundation for
personalization throughout the app.

---

### Task 4: Orchestrator + Tool Registry (Week 2-3)
**Goal**: Intent classification → tool selection → execution pipeline

Deliverables:
- `src/blind_assistant/core/orchestrator.py`
- `src/blind_assistant/core/planner.py`
- `src/blind_assistant/tools/registry.py`
- `src/blind_assistant/tools/installer.py`
- `src/blind_assistant/core/confirmation.py`
- End-to-end test: "Order me food" → DoorDash tool identified → install offered → confirmed

**Why fourth**: Once the tool registry pattern is established, adding new integrations
becomes a matter of writing a new Tool subclass.

---

### Task 5: Voice-Guided Installer (Week 3)
**Goal**: Brand new user can set up the entire system without sighted assistance

Deliverables:
- `installer/install.py` — voice-guided setup wizard
- `installer/voice_setup.py` — component-level setup helpers
- End-to-end test: fresh Python install → run installer → fully functional in ~5 minutes
  guided entirely by voice

**Why fifth**: This is the accessibility gate. Without an accessible installer,
we cannot ship to real blind users.

---

## Non-Functional Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Voice response latency | < 2 seconds | Time from speech end to first word of response |
| STT accuracy | > 95% WER | Tested against diverse blind user speech samples |
| Screen description latency | < 5 seconds | Time from "what's on my screen" to spoken description |
| Vault query latency | < 3 seconds | Time from question to spoken answer |
| Installer completion time | < 10 minutes | Fresh install to functional system, voice-only |
| Offline core capability | Basic I/O works | Test with network disabled |

---

## Technology Versions

```
python = "3.11+"
anthropic = ">=0.20.0"           # Claude API
openai-whisper = ">=20231117"    # Speech-to-text (local)
python-telegram-bot = ">=21.0"  # Telegram interface
playwright = ">=1.40.0"          # Browser control
cryptography = ">=42.0"          # Vault encryption
keyring = ">=24.0"               # OS credential storage
elevenlabs = ">=1.0.0"           # Cloud TTS
pyttsx3 = ">=2.90"               # Local TTS fallback
stripe = ">=7.0.0"               # Payment tokenization
pillow = ">=10.0.0"              # Screenshot manipulation
httpx = ">=0.25.0"               # HTTP client (async)
pytest = ">=7.0.0"               # Testing
pytest-asyncio = ">=0.23.0"      # Async test support
pip-audit = ">=2.7.0"            # Dependency security audit
```
