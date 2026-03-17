---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.html"
  - "**/*.vue"
  - "**/*.svelte"
---

# Accessibility Rules (Auto-loaded for UI files)

## WCAG 2.1 AA Compliance — Always Required

### Perceivable
- All non-decorative images have descriptive `alt` text (not "image" or filename)
- Decorative images use `alt=""` and `aria-hidden="true"`
- Color contrast: 4.5:1 for normal text, 3:1 for large text (18pt or 14pt bold)
- Non-text UI components (inputs, icons, focus indicators): 3:1 contrast ratio
- No information conveyed by color alone — always pair with text or pattern
- Captions for all video content; transcripts for all audio content

### Operable
- ALL functionality operable by keyboard alone
- No keyboard traps (focus must be escapable at all times)
- Tab order must match logical reading order
- Keyboard focus ALWAYS visible — never `outline: none` without a styled replacement
- Skip navigation link must be the first focusable element
- Minimum touch target: 44x44px

### Understandable
- Language attribute on `<html>` element
- Error messages must identify the field AND describe how to fix it
- Form labels are persistent — do not use placeholder as sole label
- Instructions appear before the form field they describe

### Robust (ARIA Rules)
- Only use ARIA when native HTML semantics are insufficient
- All ARIA states/properties reference existing elements
- Interactive custom widgets must implement full keyboard pattern from APG
- `aria-live` regions must exist in DOM before content is injected
- `role="dialog"` must trap focus; must restore focus on close
- Never put interactive elements inside `aria-hidden="true"` containers

## Common ARIA Patterns — Do This Correctly

```html
<!-- Button with icon only -->
<button aria-label="Close dialog">
  <svg aria-hidden="true">...</svg>
</button>

<!-- Toggle button -->
<button aria-pressed="false">Mute</button>

<!-- Expandable section -->
<button aria-expanded="false" aria-controls="menu-id">Menu</button>
<ul id="menu-id" hidden>...</ul>

<!-- Required field -->
<label for="email">Email <span aria-hidden="true">*</span></label>
<input id="email" type="email" required aria-required="true"
       aria-describedby="email-error" />
<span id="email-error" role="alert" aria-live="polite"></span>

<!-- Skip link -->
<a href="#main-content" class="skip-link">Skip to main content</a>
```

## React/JSX Specific
- Use `htmlFor` not `for` for label associations
- Avoid spreading unknown props onto DOM elements (`<div {...props}>` may pass invalid attrs)
- After route changes: move focus to `<h1>` or main content area
- Modals: use `aria-modal="true"` and `inert` on background content
- Lists of items: use `<ul>`/`<ol>` + `<li>`, never divs with role="list" unless necessary
