# Contributing to Blind Assistant

Thank you for your interest in contributing. Blind Assistant is built by and for the blind
and visually impaired community — your contributions directly improve the independence of
real people's daily lives.

**Blind users, accessibility specialists, and disability advocates are especially welcome.**
You don't need to write code to contribute — feedback, user testing, documentation, and
issue reports are just as valuable.

---

## Ways to Contribute

### If you use a screen reader or are blind/visually impaired
- **Test the app** and report your experience as an issue (use the Accessibility Issue template)
- **Review proposed features** — your lived experience is the most valuable feedback we have
- **Join the discussion** on open feature requests and share what would actually help you
- **Write user stories** — describe tasks you wish you could do that you currently can't

### If you write code
- Fix a `good-first-issue` labeled issue
- Implement a feature from `docs/FEATURE_PRIORITY.md`
- Build a new integration (see `docs/INTEGRATION_MAP.md` for what's planned)
- Improve test coverage

### If you do documentation
- Improve `README.md` for screen reader clarity
- Add or improve inline code comments
- Translate docs to another language

---

## Setting Up Your Development Environment

### Requirements
- Python 3.11+
- A microphone (for testing voice features)
- A Claude API key (free tier works for development)

### Steps

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/blind-assistant
cd blind-assistant

# 2. Install with dev dependencies
pip install -e ".[dev]"

# 3. Store your Claude API key in the OS keychain (no .env files)
#    The setup wizard handles this interactively:
python installer/install.py
#    Or you can store the key manually and run the API server:
#      python -m blind_assistant.main --api

# 4. Run the tests
pytest tests/unit/ -q

# 5. Start the assistant (voice interface)
python -m blind_assistant.main --voice
```

If any step doesn't work, open an issue — setup friction is a bug.

**Note**: This project uses the OS keychain (via the `keyring` library) for all credentials.
There is no `.env` file in production. Credentials are stored securely at setup time and
retrieved by the app on each run.

### Screen Reader Users
The development environment is fully accessible:
- All commands are terminal-based (screen reader friendly)
- No GUI tools are required
- GitHub's web interface works with NVDA, JAWS, and VoiceOver for issues and PRs

---

## Making a Contribution

### 1. Find something to work on
- Browse issues labeled [`good-first-issue`](../../issues?q=label%3Agood-first-issue)
- Check [`ROADMAP.md`](ROADMAP.md) for current phase and upcoming features
- Check [`docs/FEATURE_PRIORITY.md`](docs/FEATURE_PRIORITY.md) for the full prioritized feature list
- Have an idea? Open a Feature Request issue first to discuss before building

### 2. Create a branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 3. Write your code
- Follow the existing code style (`ruff` handles formatting)
- Add tests for any new functionality
- Update `CHANGELOG.md` if your change affects users

### 4. Test your change
```bash
# Run all tests
pytest

# Run linting
ruff check .
mypy src/

# If you changed voice output, test it:
# Run the relevant blind user persona agent in Claude Code
```

### 5. Open a Pull Request
Use the PR template. Key checklist items:
- [ ] Does this work by voice with no visual interaction required?
- [ ] Did you test with a screen reader or describe your voice testing?
- [ ] Does `pytest` pass?
- [ ] Is `CHANGELOG.md` updated?

---

## Code Style

- **Python 3.11+** with full type hints
- **ruff** for linting and formatting (run `ruff check . --fix`)
- **mypy** for type checking
- Docstrings on public functions
- No bare `except:` — catch specific exceptions
- Secrets via `keyring`, never `.env` in production

---

## Accessibility Standards for All Contributions

Every change that affects how the assistant communicates must:
- Work entirely by voice — no visual-only feedback
- Use plain language — no jargon in user-facing strings
- Include a spoken error message if something fails
- Work for Dorothy (our elder user persona) — if it's confusing to a low-tech user, simplify it

---

## Questions?

Open a [Discussion](../../discussions) or ask in your PR. We respond to all first-time
contributor questions within 7 days.
