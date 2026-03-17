# User Stories — Blind Assistant

> Synthesized from: all 5 blind user persona agents
> Cycle: 1 — Phase 1 Discovery
> Date: 2026-03-17

---

## How to Read This Document

Each story follows the format:
> "As [persona], I want to [action] so that [benefit]."
> Acceptance criteria: [specific, testable conditions]

Personas:
- **Alex** — newly blind user (34, lost sight 18 months ago)
- **Dorothy** — blind elder user (68, blind since her 40s, low-tech confidence)
- **Marcus** — blind power user (41, born blind, software developer)
- **Jordan** — DeafBlind user (29, braille display only, no audio)
- **Sam** — experienced blind user (longtime NVDA user, practical tasks focus)

---

## Epic 1: Getting Started (Onboarding)

### Story 1.1 — Alex (Newly Blind)
> As Alex, I want to be able to set up Blind Assistant entirely by voice so that I don't
> need to ask my sister to help me configure it.

**Acceptance criteria**:
- [ ] Installer speaks all instructions aloud from the very first line
- [ ] No step requires reading text from the screen to proceed
- [ ] No step requires a screen reader to already be configured
- [ ] Installer confirms each step before moving to the next
- [ ] After setup: assistant says "I'm ready. What would you like to do?" — not an error or silence
- [ ] Installer can be restarted from any step if the user gets confused
- [ ] Total setup time under 10 minutes with voice guidance

### Story 1.2 — Dorothy (Elder)
> As Dorothy, I want the setup process to use plain everyday words so that I don't need
> to know computer terms to get started.

**Acceptance criteria**:
- [ ] No setup prompt uses terms like "API", "token", "daemon", "config", "terminal",
      "environment variable", or "JSON"
- [ ] Every technical step has a plain-language explanation ("I need a special password
      from Telegram — I'll tell you how to get it")
- [ ] User can say "say that again" at any point to repeat the last instruction
- [ ] User can say "I'm confused" and get a simpler explanation
- [ ] No step has a timeout that would cause it to fail if Dorothy takes a long time to respond

### Story 1.3 — Marcus (Power User)
> As Marcus, I want to be able to complete setup without any unnecessary verbosity so that
> I'm not listening to paragraphs of explanation for things I already know.

**Acceptance criteria**:
- [ ] Expert mode available: fewer explanations, faster pacing
- [ ] User can say "skip explanation" to go to the next step immediately
- [ ] Setup is completable in under 5 minutes for someone who knows what they're doing
- [ ] All setup can also be done via config file for CI/automation use

---

## Epic 2: Screen Observation

### Story 2.1 — Alex (Newly Blind)
> As Alex, I want to ask "what's on my screen?" and get a clear description in plain
> English so that I can understand what's happening in apps that don't work with my
> screen reader.

**Acceptance criteria**:
- [ ] Response is spoken aloud within 5 seconds
- [ ] Description uses plain English, not HTML/UI terms ("a button that says Submit"
      not "a `<button>` element with class 'submit-btn'")
- [ ] Description mentions the most important interactive elements first (buttons, forms)
      before describing background content
- [ ] If app is inaccessible (no labels), assistant reasons about what controls likely do
- [ ] Description is concise — not reading every pixel, but conveying what the user needs to act

### Story 2.2 — Sam (Experienced User)
> As Sam, I want the assistant to describe the part of the screen I'm asking about,
> not the whole screen, so that I can get quick answers for specific areas.

**Acceptance criteria**:
- [ ] User can ask "what does the top right of the screen say?"
- [ ] User can ask "describe the form I'm currently in"
- [ ] User can ask "is there a button to submit this?"
- [ ] Response is focused on the requested region, not a full-screen narration

### Story 2.3 — Jordan (DeafBlind)
> As Jordan, I want all screen descriptions to be available as text on my braille display
> so that I can read them without any audio.

**Acceptance criteria**:
- [ ] All descriptions are available as text output, not audio-only
- [ ] Descriptions are structured in navigable chunks (sentence or paragraph breaks)
- [ ] No emoji or special characters in descriptions sent to braille output
- [ ] Braille display can scroll through a long description in logical segments

---

## Epic 3: Navigating Inaccessible Apps

### Story 3.1 — Alex (Newly Blind)
> As Alex, I want the assistant to help me complete a task in an app that my screen
> reader can't navigate so that I'm not stuck waiting for sighted help.

**Acceptance criteria**:
- [ ] User describes what they're trying to do ("I'm trying to submit this form")
- [ ] Assistant identifies the relevant controls from screenshot
- [ ] Assistant can click buttons and fill fields on the user's behalf (with confirmation)
- [ ] Assistant narrates each action as it takes it
- [ ] If task fails, assistant explains what went wrong in plain language

### Story 3.2 — Dorothy (Elder)
> As Dorothy, I want the assistant to fill out an online form for me by asking me
> the answers one question at a time so that I don't have to navigate the form myself.

**Acceptance criteria**:
- [ ] Assistant reads each form field aloud and waits for the user's answer
- [ ] Assistant fills in the answer and moves to the next field
- [ ] At the end, assistant reads back all answers before submitting
- [ ] User can say "change the [field name]" to correct an answer before submitting
- [ ] Submission requires explicit "go ahead" confirmation

---

## Epic 4: Second Brain (Personal Knowledge Base)

### Story 4.1 — Dorothy (Elder)
> As Dorothy, I want to tell the assistant to remember something important and be able
> to ask about it later so that I don't have to keep everything in my head.

**Acceptance criteria**:
- [ ] "Remember that my doctor's appointment is March 20th at 2pm" → note created
- [ ] "What do I have on March 20th?" → "Doctor's appointment at 2pm"
- [ ] "Remember that I'm allergic to penicillin" → health note created
- [ ] "What are my allergies?" → reads back stored allergies
- [ ] Notes persist across sessions
- [ ] Notes are stored encrypted on the user's device

### Story 4.2 — Alex (Newly Blind)
> As Alex, I want to ask the assistant a question about something I told it before
> so that I can recall important information when I need it.

**Acceptance criteria**:
- [ ] "What did I note about the renter's insurance claim last week?" → relevant note
- [ ] "Who did I talk to at the insurance company?" → retrieves contact name from notes
- [ ] "What medications am I supposed to take in the morning?" → reads medication notes
- [ ] Notes searchable by topic, person, date, and keyword

### Story 4.3 — Marcus (Power User)
> As Marcus, I want to be able to add notes, search notes, and link notes entirely by
> keyboard commands so that I never have to slow down for a conversation I don't need.

**Acceptance criteria**:
- [ ] Single command to add note: shortcut key → dictate note → done
- [ ] Single command to search: shortcut key → speak query → result
- [ ] Notes stored in plain markdown (user can inspect/backup/export)
- [ ] Vault accessible by any markdown app if user wants to migrate

### Story 4.4 — Jordan (DeafBlind)
> As Jordan, I want to create and retrieve notes entirely through text on my braille
> display so that I can use the Second Brain without any audio.

**Acceptance criteria**:
- [ ] All Second Brain interactions available through text/braille only
- [ ] Note content returned in braille-readable format (40-char-friendly chunks)
- [ ] No audio-only confirmation — all confirmations available as text
- [ ] Can navigate through query results with braille key presses

---

## Epic 5: Ordering Food and Everyday Items

### Story 5.1 — Alex (Newly Blind)
> As Alex, I want to order food by telling the assistant what I want so that I can get
> a meal without needing to navigate the DoorDash or Uber Eats app myself.

**Acceptance criteria**:
- [ ] "Order me a pizza" → assistant identifies available services, asks preference
- [ ] Assistant asks conversational questions: "What kind of pizza? Any dietary restrictions?
      Which address should it be delivered to?"
- [ ] Before any payment is processed: risk disclosure spoken aloud
- [ ] User explicitly confirms order details before submission
- [ ] After order: confirmation with estimated delivery time spoken aloud
- [ ] If service not configured: assistant offers to set it up with user permission

### Story 5.2 — Dorothy (Elder)
> As Dorothy, I want the assistant to remember my usual order so that I don't have to
> describe what I want every time.

**Acceptance criteria**:
- [ ] "Order my usual from last time" → confirms stored order → places with confirmation
- [ ] User can update stored preferences by voice
- [ ] Each order still requires per-transaction payment confirmation (safety)
- [ ] Confirmation reads the order details aloud even for "usual" orders

### Story 5.3 — Sam (Experienced User)
> As Sam, I want to order groceries for delivery by telling the assistant my shopping
> list so that I can stock my fridge without help from anyone.

**Acceptance criteria**:
- [ ] "Order milk, bread, and my blood pressure medication refill" → assistant handles
      each item, separating grocery from pharmacy
- [ ] Assistant finds items, reads back options if ambiguous ("1% or 2% milk?")
- [ ] Summarizes full order before submitting
- [ ] Confirms each separate payment transaction independently

---

## Epic 6: Travel Research and Booking

### Story 6.1 — Alex (Newly Blind)
> As Alex, I want to research and book a vacation entirely through conversation so that
> I can plan a trip without needing sighted help to navigate travel websites.

**Acceptance criteria**:
- [ ] "I want to take a trip but I don't know where" → assistant asks preference questions
- [ ] Assistant researches accessible destinations for blind travelers
- [ ] Options presented as spoken summaries, not tables the user can't navigate
- [ ] User can ask "tell me more about option 2" for deeper detail
- [ ] Once user chooses: assistant gathers required booking info through conversation
- [ ] Risk disclosure before any payment details
- [ ] Booking confirmation read back clearly before submission

### Story 6.2 — Marcus (Power User)
> As Marcus, I want to book a specific flight I already know I want without having to
> hear a lengthy research preamble so that I can complete the task quickly.

**Acceptance criteria**:
- [ ] "Book me the cheapest nonstop flight from NYC to Chicago on March 25th" →
      assistant books it without asking for destination research
- [ ] Presents only one confirmation prompt with full details
- [ ] Process takes under 2 minutes of user time from command to confirmation

---

## Epic 7: Smart Home Control

### Story 7.1 — Dorothy (Elder)
> As Dorothy, I want to control my smart lights and locks by asking the assistant so
> that I don't have to find and operate a physical switch or remember multiple apps.

**Acceptance criteria**:
- [ ] "Turn off all the lights" → confirms "All lights are now off"
- [ ] "Lock the front door" → confirms "Front door is locked"
- [ ] "Is the stove on?" → reads current smart device status
- [ ] Works without knowing device names — can refer to "the living room light"

---

## Epic 8: Voice-First AI Interaction Quality

### Story 8.1 — Dorothy (Elder)
> As Dorothy, I want the assistant to speak slowly and clearly and wait for me to respond
> so that I can keep up without feeling rushed.

**Acceptance criteria**:
- [ ] Speech rate configurable by user (default: slower than normal)
- [ ] User can say "speak slower" at any time to reduce rate
- [ ] User can say "say that again" to repeat the last response
- [ ] User can say "I didn't catch that" to get a simpler re-explanation
- [ ] No timeout on user responses for conversational tasks (30-second default minimum)

### Story 8.2 — Marcus (Power User)
> As Marcus, I want the assistant's responses to be as brief as possible by default
> so that I can act on information without listening to preamble.

**Acceptance criteria**:
- [ ] Verbosity level configurable (brief / standard / detailed)
- [ ] Default brief mode: no "Certainly!" or "Great question!" prefixes
- [ ] Confirmations are short: "Order placed: $22.49, arrives in 35 min" not a paragraph
- [ ] User can ask for more detail: "explain that" → expands the brief response

### Story 8.3 — Jordan (DeafBlind)
> As Jordan, I want all assistant responses available as text that can be sent to my
> braille display so that I can use the assistant with no audio at all.

**Acceptance criteria**:
- [ ] Every response from the assistant is available as text, not just audio
- [ ] Text responses are structured with braille-friendly formatting (40-char lines)
- [ ] "Thinking" / loading states communicated as text: "[Working...]" not a spinner
- [ ] All features accessible with no audio output configured
- [ ] Text interface (via Desktop app, Web, or optionally Telegram) is available for Jordan's workflow; Jordan is NOT required to use Telegram — the braille display must work with native app interfaces

### Story 8.4 — Alex (Newly Blind)
> As Alex, I want the assistant to tell me what it's doing while it's working so that
> I know it's still there and haven't done something wrong.

**Acceptance criteria**:
- [ ] For any task taking more than 2 seconds: interim spoken update
  ("I'm searching for flights now...", "Looking at your screen...", "Placing your order...")
- [ ] If task fails: immediate explanation, not silence
- [ ] If task is taking longer than expected: "This is taking a bit longer than usual..."

---

## Epic 9: Privacy and Security (User Experience)

### Story 9.1 — Sam (Experienced User)
> As Sam, I want to know exactly what information the assistant has stored about me and
> be able to delete it by voice so that I'm always in control of my data.

**Acceptance criteria**:
- [ ] "What do you know about me?" → lists categories of stored information
- [ ] "Delete my payment information" → removes and confirms
- [ ] "Delete everything" → clears all stored data with confirmation
- [ ] "What did you install for me?" → lists all installed tools
- [ ] "Uninstall [tool]" → removes tool and its credentials

### Story 9.2 — Jordan (DeafBlind)
> As Jordan, I want to be warned before the assistant takes any action that could affect
> my security — all in text, not audio — so that I can make informed decisions.

**Acceptance criteria**:
- [ ] All security warnings available as text (not audio-only)
- [ ] Payment risk disclosure available as braille-readable text
- [ ] Per-transaction confirmations confirmable via text response
- [ ] "Confirm" and "cancel" work as text commands for all confirmations

---

## Summary Table

| Story | Persona | Epic | Priority | Phase Target |
|-------|---------|------|----------|--------------|
| 1.1 Voice-only setup | Alex | Onboarding | P1 | Phase 2 |
| 1.2 Plain-language setup | Dorothy | Onboarding | P1 | Phase 2 |
| 2.1 Screen description | Alex | Screen Obs. | P1 | Phase 2 |
| 2.3 Braille screen description | Jordan | Screen Obs. | P1 | Phase 2 |
| 4.1 Add/retrieve notes by voice | Dorothy | Second Brain | P1 | Phase 2 |
| 5.1 Order food by voice | Alex | Ordering | P1 | Phase 2 |
| 8.1 Slow speech, repeat | Dorothy | Voice Quality | P1 | Phase 2 |
| 8.3 Braille-only mode | Jordan | Voice Quality | P1 | Phase 2 |
| 8.4 Progress updates | Alex | Voice Quality | P1 | Phase 2 |
| 3.1 Navigate inaccessible apps | Alex | Navigation | P2 | Phase 2 |
| 4.2 Query notes conversationally | Alex | Second Brain | P2 | Phase 2 |
| 5.3 Grocery ordering | Sam | Ordering | P2 | Phase 3 |
| 6.1 Travel research + booking | Alex | Travel | P2 | Phase 3 |
| 8.2 Verbosity control | Marcus | Voice Quality | P2 | Phase 2 |
| 9.1 Data transparency + delete | Sam | Security | P2 | Phase 2 |
| 1.3 Expert setup mode | Marcus | Onboarding | P3 | Phase 3 |
| 2.2 Region-specific description | Sam | Screen Obs. | P3 | Phase 3 |
| 4.3 Keyboard shortcut notes | Marcus | Second Brain | P3 | Phase 3 |
| 5.2 Saved usual order | Dorothy | Ordering | P3 | Phase 3 |
| 6.2 Direct flight booking | Marcus | Travel | P3 | Phase 3 |
| 7.1 Smart home control | Dorothy | Smart Home | P3 | Phase 3 |
| 9.2 Security warnings in braille | Jordan | Security | P2 | Phase 2 |
