# Pull Request

## What does this change?
*A clear description of what this PR adds, fixes, or changes.*

## Why?
*Link to the issue this addresses, or explain the motivation.*

Closes #

## Type of change
- [ ] Bug fix
- [ ] New feature / integration
- [ ] Accessibility improvement
- [ ] Documentation
- [ ] Tests
- [ ] CI/DevOps
- [ ] Refactor (no behavior change)

---

## Accessibility Checklist

*Required for any change that affects user-facing behavior.*

- [ ] **Voice-only**: this change works entirely by voice with no visual interaction required
- [ ] **Plain language**: all user-facing strings use plain language (no jargon)
- [ ] **Error handling**: failures produce a spoken explanation and a suggested next step
- [ ] **Tested by persona**: I ran this through at least one blind user persona agent (or tested with a real screen reader)
- [ ] **Dorothy test**: a low-tech elderly blind user could understand this interaction

## Security Checklist

*Required for any change that touches credentials, personal data, or external services.*

- [ ] No credentials or API keys in source code
- [ ] Sensitive data not logged
- [ ] Risk disclosure shown before any payment details requested
- [ ] `pip-audit` / `safety` passes with no new CVEs

## General Checklist

- [ ] Tests pass (`pytest`)
- [ ] Linting passes (`ruff check .`)
- [ ] Type checking passes (`mypy src/`)
- [ ] `CHANGELOG.md` updated (if user-facing change)
- [ ] Docs updated (if behavior changed)

---

## Testing Notes
*How did you test this? What edge cases did you consider?*
