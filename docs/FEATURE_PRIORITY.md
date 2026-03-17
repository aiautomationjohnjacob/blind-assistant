# Feature Priority — Blind Assistant

> Written by: nonprofit-ceo agent
> Input documents: USER_STORIES.md, GAP_ANALYSIS.md, ARCHITECTURE.md
> Cycle: 1 — Phase 1 Discovery
> Date: 2026-03-17

---

## Strategic Assessment

We have three classes of users and a clear mission: independence.

The measure of every feature is: **does this meaningfully change what a blind person
can do independently today?**

After reviewing all 21 user stories, the following prioritization emerges. The top 5
stories, if implemented completely and accessibly, would represent a step-change in
real-world independence for blind users — something no current tool delivers.

---

## The Top 5 Stories by Mission Impact

### #1: Voice-Only Setup (Story 1.1 + 1.2)

**Why this matters more than anything else**:
If a blind user cannot set up the app themselves, every other feature is irrelevant
to them. Every powerful AI tool that exists today is inaccessible because setup requires
sighted help. We must be categorically different from day one.

The grant narrative here is obvious: "For the first time, a blind person can set up a
full-featured AI life assistant without asking anyone for help." That is measurable,
demonstrable, and fundable.

**Mission impact**: Maximum. This is the prerequisite for all other impact.

**Who benefits first**: Newly blind users (Alex) who have never configured assistive
tech before, and elderly blind users (Dorothy) who can't troubleshoot technical problems.

**Build before**: Everything else. No Phase 2 ships without an accessible installer.

---

### #2: Screen Observation + Inaccessible App Navigation (Stories 2.1, 3.1)

**Why this matters**:
30%+ of apps that blind users need to use are poorly labeled and break screen readers.
A blind person trying to use their bank's website, a healthcare portal, or a government
form is currently stuck — they must call someone for help or go without.

The assistant being able to see those screens and either describe them or navigate them
on the user's behalf is transformational. It removes the single largest daily frustration
blind users report: inaccessible apps.

**Mission impact**: Very high. Daily occurrence for most blind computer users.

**Who benefits first**: Alex and Sam — working-age users who hit inaccessible apps
constantly in work and daily life.

**Grant framing**: "Reduces dependency on sighted assistance for computer navigation by
[X]% — measured by user study."

---

### #3: Second Brain by Voice (Stories 4.1, 4.2)

**Why this matters**:
Blind users have no accessible personal knowledge management system today. Everything
lives in their head or in fragmented, unsearchable voice memos. For elderly users,
medication management, appointment tracking, and remembering important conversations
are safety-critical.

Being able to say "remember that I need to refill my blood pressure medication" and later
ask "what medications do I need to refill?" — and have that work reliably — is the kind
of daily independence improvement that changes lives.

**Mission impact**: High and broad. Every user benefits. Most critical for Dorothy and
users managing health conditions.

**Grant framing**: "Provides the first accessible personal knowledge base for blind users,
enabling independent management of medical, financial, and personal information."

---

### #4: Ordering Food and Groceries by Voice (Story 5.1, 5.3)

**Why this matters**:
Independently ordering food and groceries is a basic life task that sighted people do
effortlessly. For a blind user, the DoorDash app requires navigating a complex,
poorly-labeled interface. Instacart requires browsing a visual catalog. Many blind users
report needing sighted help just to order a meal.

This is not a luxury feature — it is basic daily independence. And the security model
(risk disclosure + payment tokenization + per-transaction confirmation) sets a standard
for how AI assistants should handle financial actions for vulnerable users.

**Mission impact**: High. Food security and basic shopping independence.

**Who benefits first**: Alex (wants independence from family), Dorothy (needs simpler
path to essential goods).

---

### #5: 24/7 Multi-Device Access via Telegram (implicit in most stories)

**Why this matters**:
Independence is only valuable if it's reliable. A blind person who can order food from
their laptop at home but not from their phone when they're out isn't truly independent.

The Telegram bot as primary interface means the assistant is available on every device,
24/7, without visual setup. It also means the assistant is reachable in emergencies —
a blind user who needs help navigating an unfamiliar situation can reach their AI from
anywhere.

**Mission impact**: High. Turns episodic assistance into persistent independence.

**Grant framing**: "24/7 AI life companion accessible from any device — reduces both
digital and physical-world dependency on sighted assistance."

---

## Full Priority Stack

### P1 — Must ship in Phase 2 (MVP)

| Feature | User Story | Mission Impact |
|---------|------------|----------------|
| Voice-only installer | 1.1, 1.2 | Maximum — prerequisite for all users |
| Screen description ("what's on my screen?") | 2.1, 2.3 | Very high — daily use case |
| Second Brain: add and retrieve notes by voice | 4.1, 4.2 | High — life management |
| Food ordering by voice with security flow | 5.1 | High — basic independence |
| Telegram bot as primary interface | All | High — 24/7 access |
| Braille-safe text output mode (Jordan) | 2.3, 8.3 | Sets accessibility floor |
| Speech rate and verbosity control | 8.1, 8.2 | Required for Dorothy and Marcus |
| Progress updates during long operations | 8.4 | Required for trust |
| Risk disclosure + payment confirmation flow | 5.1 | Security non-negotiable |
| Data transparency: what's stored, delete by voice | 9.1 | Trust non-negotiable |

### P2 — Phase 2-3 (Early expansion)

| Feature | User Story | Mission Impact |
|---------|------------|----------------|
| Navigate inaccessible apps by clicking/filling | 3.1 | High — daily frustration |
| Form filling by conversational Q&A | 3.2 | High — complex apps |
| Grocery ordering (Instacart) | 5.3 | High — basic independence |
| Travel research + booking | 6.1 | High — life expansion |
| Expert setup mode (Marcus) | 1.3 | Medium — power user adoption |
| Region-specific screen description | 2.2 | Medium — efficiency |
| Security warnings in braille text | 9.2 | Required for Jordan |

### P3 — Phase 3-4 (Full feature set)

| Feature | User Story | Mission Impact |
|---------|------------|----------------|
| Smart home control (Home Assistant) | 7.1 | High for home management |
| Saved usual order (Dorothy) | 5.2 | Medium — convenience |
| Direct flight booking (Marcus) | 6.2 | Medium — power user efficiency |
| Keyboard shortcut note-taking (Marcus) | 4.3 | Medium — power user efficiency |
| Calendar integration | New | High — scheduling independence |
| Email by voice | New | High — communication independence |

---

## Mission Risk Assessment

### Risks if we get priorities wrong:

**Risk 1: Ship features before accessible installer**
If the installer isn't voice-guided from day one, early users will be people who got
sighted help to install it. We'll never know if the app actually works for independent
setup. And we'll have established a pattern (sighted setup required) that will be hard
to fix later.

**Risk 2: Overindex on power user features**
Marcus's stories (keyboard shortcuts, verbosity control, expert mode) are important,
but they are not the stories that demonstrate mission impact to funders or to the
blind community. If we build primarily for Marcus, we'll have a tool for the 5% of
blind users who already get by with current tools. We need Dorothy and Alex to succeed.

**Risk 3: Build features without security model**
The ordering and travel features involve financial data. If we ship those without the
full security model (risk disclosure, payment tokenization, per-transaction confirmation),
we expose a vulnerable population to financial risk and destroy community trust permanently.
No feature that handles money ships without security-specialist sign-off.

**Risk 4: Skip braille support until Phase 3**
Jordan's stories are the accessibility floor. Every feature we ship without testing
against Jordan's constraints will need to be retrofitted. Building braille-safe from
the start (structured text output, no audio-only features) is far cheaper than
retrofitting it later.

---

## Key Metrics to Track

These are the independence outcomes that matter to funders and users:

1. **Setup independence rate**: % of blind users who complete setup without sighted help
2. **Inaccessible app navigation success rate**: % of tasks completed in poorly-labeled apps
3. **Ordering independence**: # of food/grocery orders placed without sighted assistance
4. **Second Brain usage**: # of notes added and retrieved per user per week
5. **Daily use rate**: % of users who interact with the assistant daily
6. **Net Promoter Score from blind users specifically** (not general users)

The mission is not "downloads" or "users" — it is "independence events":
moments where a blind person accomplished something independently that they could not
have accomplished alone before.
