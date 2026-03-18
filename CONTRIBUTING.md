# Contributing to Blind Assistant

Thank you for your interest in contributing. Blind Assistant is built **by and for** the blind
and visually impaired community. Your contributions directly expand what blind people can
independently do on a computer.

---

## A Special Welcome to Blind Contributors

**If you are blind or visually impaired, you are the most important contributor here.**

You do not need to write code. Your lived experience — what works, what breaks, what's
confusing, what would genuinely help — is the input that shapes everything we build.

Ways you can contribute without writing code:
- **Test the app with your screen reader** (NVDA, JAWS, VoiceOver, TalkBack, or a braille display)
  and report what doesn't work using the Accessibility Issue template
- **Review open feature requests** — your first-hand experience of what it's like to use
  a computer without sight is something no sighted contributor can replicate
- **Write user stories** — describe in plain language a task you wish you could do independently
  that you currently cannot, or can only do with sighted assistance
- **Tell us when something is confusing** — if you don't understand an instruction, that's a bug,
  not a failing on your part

**Braille display users**: we specifically want to hear from you. The deafblind user experience
(no audio, no visual output — braille only) is one of the hardest to get right, and we have
the fewest testers. Open an issue or start a Discussion. We are listening.

**First-time GitHub users**: if GitHub is new to you, or if GitHub's interface is difficult
with your screen reader, open an issue using the Accessibility Issue template and describe
your experience. Someone on the team will help you through it.

---

## Ways to Contribute

### For blind and visually impaired users
- **Test and report** — use the Accessibility Issue template on the Issues tab
- **Review features** — your lived experience is evidence; share it on open issues
- **Write user stories** — plain language descriptions of tasks you want to be able to do
- **Share what you use today** — what screen readers, tools, and workarounds you rely on

### For developers
- Fix a `good-first-issue` labeled issue (see the Issues tab)
- Implement a feature from `docs/FEATURE_PRIORITY.md`
- Build a new integration (see `docs/INTEGRATION_MAP.md` for what's planned)
- Add tests to improve coverage

### For documentation and translation writers
- Improve `README.md` for screen reader clarity
- Add or improve inline code comments
- Translate docs or user-facing strings to another language

---

## Who Is Dorothy?

Our development team uses **Dorothy** as a reference persona: a 70-year-old woman who lost
her sight two years ago and has low technical confidence. She has never heard of an API, a
backend server, or a passphrase in a technical context.

We also use **Alex**, who is newly blind and still learning assistive technology.

**Every user-facing change must work for Dorothy.** If Dorothy would be confused or stuck,
it's not ready. When reviewing code, ask: "Could Dorothy set this up without sighted help?
Could she recover if something went wrong?"

---

## Setting Up Your Development Environment

### Requirements
- Python 3.11 or later
- Node.js 18+ and npm (for the mobile and web app)
- A microphone (for testing voice features)
- A Claude API key (free tier works for development — get one at console.anthropic.com)

### Steps

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/blind-assistant
cd blind-assistant

# 2. Install Python dependencies with dev extras
pip3 install -e ".[dev]"

# 3. Store your Claude API key in the OS keychain (no .env files)
#    The voice-guided setup wizard handles this:
python3 installer/install.py
#    Or store the key manually and run the API server directly:
#      python3 -m blind_assistant.main --api

# 4. Run the Python tests
pytest tests/unit/ -q

# 5. Run the JavaScript/React Native tests (mobile and web app)
cd clients/mobile
npm ci
npm test
cd ../..

# 6. Start the assistant (voice interface, local)
python3 -m blind_assistant.main --voice
```

**If any step doesn't work, open an issue** — setup friction is a bug, not your fault.

**Note on credentials**: This project uses the OS keychain (`keyring` library) for all
credentials. There is no `.env` file in production. The setup wizard stores keys securely
and the app retrieves them on each run. You never put API keys in source files.

### Screen Reader Users

The development environment is fully accessible:
- All commands are terminal-based — no GUI required
- No drag-and-drop or visual setup steps anywhere
- GitHub's web interface works with NVDA, JAWS, VoiceOver, and TalkBack for issues and PRs
- If any part of the setup requires visual interaction, that is a bug — report it

---

## Good First Issues

Look for the `good-first-issue` label on GitHub Issues. These are well-defined tasks that
don't require deep knowledge of the codebase.

**Types of good first issues in this project:**
- Add a missing unit test for an existing Python function
- Fix a specific WCAG accessibility label in the React Native app
- Add a docstring to a public function that is missing one
- Improve an error message to be more understandable for a non-technical blind user
- Add a new user story from a persona we have heard less from
- Translate a user-facing string to another language
- Fix a typo or clarity issue in README.md or CONTRIBUTING.md
- Add an accessibility assertion to an existing test

If you spot one of these gaps and no issue exists for it, open a Feature Request or Bug
Report — it may become a good-first-issue that you then fix yourself.

---

## Making a Contribution

### 1. Find something to work on
- Browse issues labeled [`good-first-issue`](../../issues?q=label%3Agood-first-issue)
- Check [`ROADMAP.md`](ROADMAP.md) for the current phase and upcoming work
- Check [`docs/FEATURE_PRIORITY.md`](docs/FEATURE_PRIORITY.md) for the full prioritized feature list
- Check [`docs/OPEN_ISSUES.md`](docs/OPEN_ISSUES.md) for tracked gaps (some are ready to fix)
- Have an idea? Open a Feature Request issue first to discuss it before building

### 2. Create a branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 3. Write your code
- Follow the existing code style (`ruff` handles Python formatting automatically)
- Add tests for any new functionality
- Add a docstring to any new public function
- Update `CHANGELOG.md` if your change affects users

### 4. Test your change

**Python tests:**
```bash
# Unit tests only (fast — run these every time)
pytest tests/unit/ -q

# Full suite with coverage
pytest tests/ --cov=src/blind_assistant --cov-report=term-missing

# Linting and type checking
ruff check .
mypy src/
```

**JavaScript/React Native tests:**
```bash
cd clients/mobile
npm test
npm run type-check
```

### 5. Open a Pull Request
Use the PR template. Key checklist items:
- [ ] Does this work by voice with no visual interaction required?
- [ ] Did you test with a screen reader, or describe your voice testing?
- [ ] Does `pytest tests/unit/` pass?
- [ ] Does `npm test` pass (if you changed the mobile app)?
- [ ] Is `CHANGELOG.md` updated (if the change affects users)?

---

## Code Style

**Python:**
- Python 3.11+ with full type hints on all public functions
- `ruff` for linting and formatting — run `ruff check . --fix` to auto-fix
- `mypy` for type checking — `mypy src/` must report 0 errors
- Docstrings on all public functions (one line explaining what it does, not just restating the name)
- No bare `except:` — catch specific exceptions
- Secrets via `keyring`, never in `.env` files in production

**JavaScript/TypeScript (React Native/Expo):**
- TypeScript strict mode
- Functional components with React hooks
- Accessibility props on every interactive element (`accessibilityLabel`, `accessibilityRole`)
- No `// @ts-ignore` without a comment explaining why

---

## Accessibility Standards for All Contributions

Every change that affects how the assistant communicates must:
- **Work entirely by voice** — no visual-only feedback allowed
- **Use plain language** — no jargon in user-facing strings (no "API", "endpoint", "token",
  "backend" in anything a user reads or hears)
- **Include a spoken error message** if something fails — error messages must say what went
  wrong AND what the user can do next
- **Pass the Dorothy test** — a 70-year-old with low technical confidence who is newly blind
  could understand this and complete the task without sighted help

When in doubt, ask yourself: "If Dorothy tried this alone, would she succeed or give up?"

---

## Commit Message Format

We use a structured commit message format so the history is readable:

```
[type]([scope]): [what changed, max 72 chars]

[2-4 sentences explaining WHY this change was made — not just what.
Reference the issue or user story it addresses.]

Test plan:
- [test file(s) and count]
- [what the tests cover]
- coverage: [X%]
- gap: [known gap or 'none']
```

Types: `feat` `fix` `docs` `a11y` `security` `test` `refactor` `ci` `chore`

Example:
```
fix(setup-wizard): replace "API token" with "connection code" throughout

Dorothy (elder persona) and newly-blind users do not recognize the term
"API token". Replacing it with "connection code" removes a barrier that
left users stuck during setup with no path forward.

Test plan:
- clients/mobile/app/__tests__/SetupWizardScreen.test.tsx: 2 new regression tests
- covers: empty input guard, too-short input guard
- coverage: 100% of changed strings
- gap: none
```

---

## Questions?

- Open a [Discussion](../../discussions) or ask in your Pull Request
- We respond to all first-time contributor questions within 7 days
- If GitHub is hard to navigate with your screen reader, tell us and we will help

**There are no stupid questions here. Setup confusion is our bug, not your mistake.**
