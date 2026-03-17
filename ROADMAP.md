# Roadmap

> This is a living document. Community input shapes priorities.
> See `docs/FEATURE_PRIORITY.md` for the detailed agent-researched priority list.

## Now — Phase 1: Foundation
*Current focus of the autonomous development loop*

- [ ] Technology stack decision and architecture document
- [ ] Gap analysis of existing accessibility tools
- [ ] Security model for handling sensitive data
- [ ] Initial project scaffold with voice-guided setup
- [ ] User stories from 5 blind user personas

## Next — Phase 2: Core Experience

The minimum a blind user can actually try:
- [ ] Screen description: "What's on my screen?" → spoken answer
- [ ] Voice conversation loop (speak → AI responds → speak back)
- [ ] One complete agentic task end-to-end (e.g. food ordering)
- [ ] Telegram bot interface (24/7 access from any device)
- [ ] Risk-disclosure flow for payment details

## Later — Phase 3: Life Assistant Features

- [ ] Second Brain: voice-add notes, voice-query your knowledge base
- [ ] Research + action: "Research accessible vacation options and book one"
- [ ] Home Assistant integration: control smart home by voice
- [ ] Calendar and appointment management
- [ ] Email management by voice

## Future — Phase 4 & 5: Polish and Community

- [ ] WCAG 2.1 AA compliance audit (zero critical findings)
- [ ] Dorothy test: elder blind user can set up and use without sighted help
- [ ] Community user testing with NFB/ACB chapters
- [ ] Multi-language support
- [ ] Mobile companion app (Android/iOS Telegram-based)

## Parallel Track: Education Website (`learn.blind-assistant.org`)

*Runs alongside the main app — can be contributed to independently*

- [ ] Accessible course platform scaffold (Astro/Next.js/Eleventy)
- [ ] Course 1: How to use Blind Assistant (setup → advanced)
- [ ] Course 2: AI literacy for blind users
- [ ] Course 3: Second Brain by voice
- [ ] Course 4: Navigating the digital world (banking, travel, shopping)
- [ ] Course 5: Advocating for yourself (rights, WCAG, reporting)
- [ ] NVDA end-to-end test: any course completable with zero mouse use

---

## What We Will NOT Build

- **Another screen reader** — NVDA and JAWS do this well; we integrate with them
- **A paid tier** — core features are free forever for blind users
- **A desktop GUI** — everything is voice-first; visual UI is secondary
- **Anything that requires sighted setup** — this is a hard constraint, always

---

## How to Influence the Roadmap

1. Open a [Feature Request](../../issues/new?template=feature_request.md) issue
2. Comment on existing roadmap items with your use case
3. Vote (👍) on issues to signal priority
4. Share your lived experience — "I can't do X today and it costs me Y" is the most
   powerful input we receive
