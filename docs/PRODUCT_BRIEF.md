# Blind Assistant — Product Brief (Living Document)

> This document is maintained by the AI agents. Humans may edit it to redirect priorities.
> Last updated by: human founder, 2026-03-17

---

## The Vision

Blind Assistant is an **AI life companion for blind and visually impaired people** — not
just a screen reader, not just a computer tool, but a persistent intelligent assistant
that helps someone live a full, independent life through conversation.

The best analogy is: imagine taking Claude Code's ability to read screens, browse the web,
read documents, install tools, and execute tasks — and wrapping it in an interface that a
blind person who has never used a computer before can set up and use entirely by voice,
from day one, with zero sighted assistance required.

The key insight driving this project: **most of what blind people need already exists as
AI tools — they just can't use them.** The setup requires vision. The interfaces require
vision. The documentation assumes vision. Our job is to synthesize these existing tools
into a single accessible layer that works for someone who cannot see at all. 


### Examples

Lets say a blind person wants to order food, for instance, they just ask our app how to do that and our app will ask them if they would like to install Doordash, once installed the app will ask if they want to input their payment information, once input the app will ask them what they would like to order and submit the order. Similar to how Claude Code works for developers - if it can't do a skill thats needed to accomplish a task, it figures out on its own how to do that task and does it for the user. Note the user might supply banking details, in which case it is important that the app keeps that information secretive or encrypted or something to ensure that the user doesn't get hacked. Even if we come to a reasonable security proof state, the app should notify the user that providing banking details could be risky to any app.

Let's say a blind person wants to book a trip to a destination but doesn't know where. The AI assistant can do research on All the different tools that are currently available to help blind people book vacations It can also book the vacation itself. If it doesn't know how to do that right now, it can figure it out and then ask the user for questions and follow-ups on what exactly it needs in order to accomplish this task. But just by talking to the user, it's able to figure out how to accomplish this task. Similar warnings and security systems should be in place for this as well, since the user would be providing banking information. 

---

## The Synthesis Vision

### What Already Exists (and needs to be made accessible)

**Personal Knowledge & Memory**
- **Obsidian + Second Brain** — A blind person could keep track of their entire life:
  appointments, medications, relationships, finances, ideas, goals — all in a personal
  knowledge base. But Obsidian's graph view and visual navigation are inaccessible. Our
  role: provide a voice-first interface to a personal Second Brain that stores the user's
  life in structured, queryable notes they can ask questions about conversationally.
- **Mem.ai, Notion AI, Rewind AI** — AI-powered memory and life logging tools, none
  designed for blind users.

**Computer & Task Automation**
- **Open Interpreter** — AI that can control a computer, execute code, browse the web,
  and complete tasks. Not designed for blind users; setup requires vision.
- **Claude Code** — Can read screens, websites, Google Docs, PDFs, install missing tools,
  write and run code, and automate workflows. Extraordinarily powerful — but the interface
  is a terminal, not accessible to most blind users.
- **n8n, Zapier, IFTTT** — Workflow automation. Could automate dozens of daily tasks
  (bill reminders, email organization, calendar management) — but require visual setup.
- **AutoGPT / AgentGPT** — Autonomous AI agents that can browse and act. Not accessible.

**Native App Interfaces (Primary)**
- **Android app** — Built specifically for blind users with TalkBack from day one;
  zero-visual-setup; no Telegram account or external accounts required to get started
- **iOS app** — VoiceOver-native; Siri Shortcuts integration; single-download setup
- **Desktop app** — Windows (NVDA/JAWS) + macOS (VoiceOver); voice-guided installer
- **Web app** — WCAG 2.1 AA; NVDA+Chrome, VoiceOver+Safari; no download required

**Secondary/Super-User Channel**
- **Telegram bot** — Optional for power users who want remote access from any device
  via a chat interface. NOT a primary interface — Telegram setup requires visual
  configuration that most blind users cannot complete independently. Available as an
  optional power-user feature once the native apps exist. WhatsApp / SMS similar.

**Important**: the Telegram bot integration that is partially built is a prototype
demonstration of the backend capabilities — it is NOT the target product interface.
Native apps are what ships to blind users.

**Vision & World Interpretation**
- **Be My Eyes / Be My AI** — Ask a human or AI to describe a photo. Slow. Manual.
  Our approach: proactive, continuous, integrated — not a one-off photo description app.
- **Seeing AI** (Microsoft) — Reads text, describes scenes, recognizes faces and products.
  A component to integrate, not reinvent.
- **GPT-4o / Claude vision** — Read any document, image, chart, webpage and describe it.
  Already exists; needs accessible delivery wrapper.

**Voice & Audio**
- **Whisper (OpenAI)** — State-of-the-art speech recognition. Free and open-source.
  The speech-to-text engine for our voice interface.
- **ElevenLabs / Azure TTS / Kokoro** — High-quality, natural text-to-speech.
  Much better than built-in screen readers' robotic voices.

**Home & Physical World**
- **Home Assistant** — Controls smart home devices by voice. Could integrate so the blind
  user can ask the assistant to turn on lights, lock doors, set alarms.
- **Online ordering APIs** (Amazon, Instacart, grocery delivery) — With user permission,
  the assistant can order items online. A blind person who needs something urgently can
  say "order me more of my blood pressure medication" and have it handled.

### The Synthesis Principle

We are not building most of these tools from scratch. We are:
1. **Connecting them** — building the integration layer that makes them work together
2. **Wrapping them accessibly** — every setup step, every interaction, works by voice
3. **Curating them** — choosing the best tool for each job and abstracting the complexity
4. **Personalizing them** — the assistant learns the user's specific life, preferences,
   and needs, so responses are always contextually relevant

**The user talks. The assistant figures out which tools to use. The user never sees the
complexity underneath.**

---

## The Core Promise

A blind user can:
1. **Set up everything entirely by voice** — install, configure, and start using without
   ever needing to see a screen or ask a sighted person for help
2. **Access their AI assistant 24/7 from any device** — through native apps on Android,
   iOS, Desktop (Windows/macOS), or the Web — wherever they are
3. **Get help with any computer task** — "read me this document," "fill out this form,"
   "find and book a flight," "what's on my screen right now"
4. **Navigate inaccessible apps** — the AI sees the screen and acts as their eyes even
   when the app has zero accessibility support
5. **Manage their personal life** — notes, appointments, finances, shopping, research,
   relationships — all through conversation
6. **Take action in the world** — order things online, send emails, schedule appointments,
   with user permission before any action that spends money or sends communications
7. **Stay safe** — all sensitive data encrypted; no plain-text passwords or financial
   details; security audit built into every release

---

## Target Users (in priority order)

1. **Newly blind users** — Adapting to vision loss, overwhelmed; need maximum support
   and extremely gentle onboarding
2. **Elderly blind users** — Long-time blind, lower tech confidence; need patience and
   plain language; enormous population
3. **Working-age experienced blind users** — Need professional-grade efficiency; often
   already use NVDA/JAWS; will adopt if we're demonstrably better for certain tasks
4. **DeafBlind users** — Braille-display primary; sets our accessibility floor
5. **Low vision users** — Some functional vision; need high contrast, zoom, large text
   alongside AI assistance

---

## What We Are NOT Building

- Another screen reader (NVDA/JAWS already handle this; we integrate with them)
- A product that requires sighted setup at any point
- A paid product (nonprofit; core features free forever)
- A tool that requires technical knowledge to use or maintain
- Something that stores sensitive data in plain text (a hard security non-negotiable)
- An app that makes decisions for users without permission

---

## Research Phase Mandate

**The gap-analyst and tech-lead agents must answer during Phase 1:**

1. Which existing tools (from the synthesis list above) should we integrate vs rebuild?
2. What does the most accessible "installer" look like for a blind user?
3. How does Telegram bot integration work as the primary multi-device interface?
4. What is the minimum viable "life assistant" — the first 5 things a newly blind user
   would want to be able to do that they currently can't?
5. What does a Second Brain look like for a blind person — what structure, what queries,
   what daily interactions would make it genuinely valuable?
6. What security architecture handles sensitive personal data (passwords, banking, medical)
   without ever storing it in plain text?
7. Can we build on top of Open Interpreter, Claude Code, or similar foundations rather
   than starting from scratch?

---

## Client Platforms

Blind Assistant is not a single app — it is a family of clients sharing the same backend:

| Platform | Interface | Primary screen reader |
|----------|-----------|-----------------------|
| **Android app** | Native Android app | TalkBack (Android Accessibility Suite) |
| **iPhone/iPad app** | Native iOS app | VoiceOver |
| **Desktop (Windows)** | Native Windows app or Python CLI | NVDA, JAWS |
| **Desktop (macOS)** | Native macOS app or Python CLI | VoiceOver |
| **Web app** | Accessible website (Chrome/Firefox/Safari) | NVDA+Chrome, VoiceOver+Safari, TalkBack+Chrome |

All five clients must:
1. Work entirely by voice/screen reader — zero mouse, zero vision required
2. Integrate with the platform's native accessibility API (not fight it)
3. Pass the NVDA keyboard-only test (if NVDA fails it, it doesn't ship)
4. Work with the platform's built-in AT: VoiceOver, TalkBack, NVDA, JAWS, Narrator (as backup)

The **education website** (`learn.blind-assistant.org`) is a sixth client — an accessible
course platform that must be fully operable by NVDA+Chrome with zero mouse use.

---

## Multi-Platform Accessibility

Every interaction pattern must be designed for the specific accessibility model of each platform:

- **iOS**: VoiceOver gesture navigation (swipes, taps, rotor); Siri Shortcuts integration;
  Dynamic Type support; Switch Control for motor disabilities
- **Android**: TalkBack swipe-to-navigate; Explore by Touch; BrailleBack for braille displays;
  Voice Access for hands-free; Google Assistant integration
- **Windows desktop**: NVDA + Chrome/Firefox for web; NVDA + native app for desktop;
  JAWS compatibility for professional users; Windows Narrator as minimum baseline
- **macOS desktop**: VoiceOver + Safari for web; VoiceOver + native app for desktop;
  Siri integration; macOS Keychain for credential storage
- **Web**: WCAG 2.1 AA minimum; semantic HTML first; ARIA only when HTML is insufficient;
  keyboard-only navigation; works in NVDA+Chrome, VoiceOver+Safari, TalkBack+Chrome

**The cross-platform test**: every feature must be completable on at least 3 of the 5
platforms before it is considered shipped. Platform experts audit each platform independently.

---

## Technical Principles

- **Voice-first, vision-optional** — every single interaction works by voice
- **Privacy by default** — encryption at rest, zero plain-text sensitive data, local-first
  where possible
- **Offline-capable core** — basic functions work without internet; cloud AI for heavy tasks
- **Modular integrations** — each tool (Obsidian, Telegram, Home Assistant) is a plugin;
  users can enable only what they need
- **Accessible installer** — the install process itself is voice-guided and screen-reader
  compatible from the first second
- **Security-audited releases** — every release includes a security audit agent review
- **API-first backend** — the Python backend exposes a REST/WebSocket API so all client
  apps (Android, iOS, Desktop, Web) can connect to it. Client apps are NOT Python — they
  use platform-appropriate languages (Swift, Kotlin, JavaScript/TypeScript). Backend and
  clients are separate deployment units that communicate over the API.
- **Server-side user data** — the second brain vault, user calendar, preferences, and profile
  all live on the backend server (not per-device). All clients share the same user data.
  During development: backend runs on localhost. Later: migrates to cloud (AWS/GCP/Railway).
- **Background processes on server** — TTS/STT pipelines, calendar integration, vault
  encryption/decryption, session context — all run server-side. Clients send text/audio
  and receive text/audio responses; they do not run AI locally.
- **Multi-platform by default** — every user-facing feature must work across all 5 clients.
  No feature ships to only one platform without a documented plan for the others. Platform
  accessibility agents audit each platform before any release.

---

## Current Build Phase

See `docs/CYCLE_STATE.md` for current status.

## Technical Direction

See `docs/ARCHITECTURE.md` once the tech-lead agent creates it.

## The Education Website

A free, open-access course platform — a second product component alongside the main app —
that teaches blind users how to use AI tools and live more independently. Lives at
`learn.blind-assistant.org` (or `website/` in this repo).

**Why it exists:** Even with a perfect app, newly blind users need to learn how to talk to AI,
how to set up a Second Brain, how to order food by voice. These skills can't be assumed.
The education site removes the barrier of "I don't know how to start."

**Course topics:**
1. How to use Blind Assistant (setup through advanced features)
2. AI literacy for blind users (what AI can and can't do; how to prompt effectively)
3. Second Brain for the blind (build a personal knowledge system by voice)
4. Navigating the digital world (banking, travel booking, shopping — all by voice)
5. Advocating for yourself (your rights; accessible technology at work; WCAG; reporting barriers)

**The accessibility floor:** every course must be completable by someone using NVDA on Windows
with zero mouse use. If it fails that test, it doesn't ship.

**Technical approach:** static site generator (Astro, Next.js, or Eleventy); audio is the
primary format — text is the fallback, not the other way around; semantic HTML first;
courses authored in Markdown with YAML frontmatter; no JavaScript required for core functionality.

---

## Community & Ethics

- Built with the blind community, not for them
- Privacy-first: screen content never logged without explicit opt-in
- Open-source forever: no paywalls for blind users
- Partnerships: NFB, ACB, local lighthouse organizations for user testing
- "Nothing about us without us" — real blind users in every testing cycle
