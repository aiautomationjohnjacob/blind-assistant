# Blind Assistant Project

## Mission
This project creates an AI assistant designed specifically for blind and visually impaired users,
helping them navigate computers more effectively. Accessibility is not a feature — it is the
core product requirement. Every decision must first ask: "How does this serve our blind users?"

## Sub-Agents Available
This project uses specialized sub-agents defined in `.claude/agents/`. Claude will proactively
invoke them based on context. Key agents:
- **nonprofit-ceo** — Strategic direction and mission alignment
- **blind-user-tester** — Simulates blind user experience with screen readers
- **accessibility-reviewer** — WCAG 2.1 AA and ARIA compliance
- **screen-reader-expert** — NVDA/JAWS/VoiceOver behavioral differences
- **tech-lead** — Architecture decisions and code standards
- **code-reviewer** — Code quality and correctness (no modifications)
- **goal-adherence-reviewer** — Verifies implementation matches stated goals

## Custom Skills (Slash Commands)
- `/audit-a11y` — Full WCAG accessibility audit via parallel sub-agents
- `/review-pr [#]` — Multi-persona PR review posted to GitHub
- `/fix-wcag` — Batch-fix WCAG violations from latest audit report

## Stack (TBD — to be decided by tech-lead agent)
- Language: TypeScript / Python (TBD)
- Testing: includes jest-axe / axe-core for accessibility
- Accessibility libraries: react-aria or similar

## Non-Negotiable Rules
- Every interactive element MUST have an accessible name
- Every PR MUST pass accessibility audit before merge
- No `outline: none` without a visible focus replacement
- All form fields must have associated labels via htmlFor/aria-labelledby
- Color must NEVER be the sole conveyor of information
- All user-facing strings must support internationalization

## Git Workflow
- Feature branches: `feature/description`
- Commit messages: conventional commits format (feat:, fix:, a11y:, docs:, test:)
- PRs require: code-reviewer + accessibility-reviewer approval

## Build & Test
- Details TBD — to be populated when stack is finalized

## Detailed Rules
@.claude/rules/accessibility.md
@.claude/rules/testing.md
