---
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "tests/**"
  - "__tests__/**"
---

# Testing Rules (Auto-loaded for test files)

## Accessibility Tests Are Mandatory
- Every UI component must have an axe-core/jest-axe test
- Keyboard navigation tests required for all interactive components
- Screen reader announcement tests for dynamic content (aria-live regions)

## Test Standards
- Tests must be deterministic — no flakiness allowed
- Mock only external services (APIs, databases) — never mock accessibility behavior
- Prefer integration tests over unit tests for UI components
- Use React Testing Library (RTL) queries in accessible order:
  1. `getByRole` (most preferred — mirrors screen reader experience)
  2. `getByLabelText`
  3. `getByPlaceholderText`
  4. `getByText`
  5. `getByDisplayValue`
  6. `getByAltText`
  7. `getByTitle`
  8. `getByTestId` (last resort only)

## Accessibility Test Pattern
```typescript
import { render } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
expect.extend(toHaveNoViolations)

test('MyComponent has no accessibility violations', async () => {
  const { container } = render(<MyComponent />)
  expect(await axe(container)).toHaveNoViolations()
})

test('MyComponent is keyboard navigable', async () => {
  const { getByRole } = render(<MyComponent />)
  const button = getByRole('button', { name: 'Submit' })
  button.focus()
  expect(document.activeElement).toBe(button)
  // Fire keyboard events...
})
```

## Coverage Requirements
- Minimum 80% coverage on all new code
- 100% coverage on accessibility utility functions
- Critical user flows (login, main nav, core feature) must have e2e tests
