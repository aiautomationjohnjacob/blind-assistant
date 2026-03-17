# Blind Assistant — Product Brief (Living Document)

> This document is maintained by the AI agents. Humans may edit it to redirect priorities.
> Last updated by: [agent will fill in]

## The Product

**Name**: Blind Assistant
**Type**: Open-source desktop AI assistant
**Mission**: Give blind and visually impaired users an AI that can see, navigate, and
control their computer on their behalf — making tasks possible that screen readers alone cannot.

## The Core Problem We Solve

Screen readers (NVDA, JAWS, VoiceOver) require apps to be correctly coded to be accessible.
When they're not — which is most of the time — blind users are simply stuck. They either
need sighted help or give up entirely.

Blind Assistant uses AI to bridge that gap. It can:
- Look at what's on screen and describe it intelligently
- Navigate to the right place even in unlabeled, inaccessible interfaces
- Explain what's happening in plain language
- Execute multi-step tasks on the user's behalf
- Learn the user's specific environment, preferences, and workflows

## Target Users (in priority order)

1. **Newly blind users** — People adapting to vision loss who need maximum support
2. **Elderly blind users** — Lower tech confidence; need patience and plain language
3. **Working-age experienced blind users** — Need efficiency and professional-grade tools
4. **DeafBlind users** — Braille-display primary; most demanding accessibility requirements

## What We Are NOT Building

- Another screen reader (NVDA/JAWS already do this well)
- A general-purpose AI assistant (plenty of those exist)
- A paid product (we are a nonprofit)
- Something that requires sighted setup to use

## Success Looks Like

A blind user can:
1. Install and configure Blind Assistant entirely without sighted help
2. Open any app on their computer and get meaningful audio description of what they see
3. Ask the AI to complete a task ("fill out this form", "read this document to me", "find
   the download button") and have it succeed — even in inaccessible apps
4. Do this faster than they could with NVDA alone

## Current Build Phase

See `docs/CYCLE_STATE.md` for current status.

## Technical Direction

See `docs/ARCHITECTURE.md` once the tech-lead agent creates it.

## Community & Ethics

- Built with the blind community, not for them
- Privacy-first: screen content never logged without explicit opt-in
- Open-source forever: no paywalls for blind users
- Partnerships: NFB, ACB, local lighthouse organizations for user testing
