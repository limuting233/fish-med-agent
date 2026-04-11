# Frontend Collaboration Guide

## Project Context

This frontend lives in a `Vue 3 + Vite + TypeScript` workspace and will support the Fish Med Agent user experience, including conversation flows, image upload, diagnosis presentation, and session management.

When contributing here, optimize for a codebase that is easy to extend, easy to reason about, and visually consistent from the start.

## Design Source of Truth

Before working on any UI design, visual refinement, layout update, or frontend styling, review [DESIGN.md](/Users/limuting/Desktop/fish-med-agent/frontend/DESIGN.md).

Treat `frontend/DESIGN.md` as the primary design reference for:
- visual direction and overall atmosphere
- typography, spacing, and layout decisions
- color usage and interaction states
- component styling and presentation details

All new UI work should stay aligned with the principles and patterns defined in `frontend/DESIGN.md` unless a task explicitly calls for a different direction.

## Core Working Principles

- Build from reusable primitives instead of page-specific one-off markup.
- Prefer clear structure and maintainability over clever abstractions.
- Keep visual output consistent across pages, states, and screen sizes.
- Preserve a calm, product-focused interface; avoid noisy decoration and arbitrary visual effects.
- Make incomplete or loading states intentional, not accidental.

## Expected Frontend Structure

- Keep application logic separated from presentation logic when possible.
- Prefer small, focused Vue components with clear responsibilities.
- Extract shared UI into reusable components once a pattern appears more than once or is clearly foundational.
- Keep page-level composition in views or top-level containers, and keep presentational concerns inside components.
- Avoid creating deeply nested component trees when a flatter structure is easier to maintain.

## Component Guidelines

- Components should have a single clear purpose.
- Props and emitted events should be explicit, typed, and minimal.
- Prefer predictable data flow over implicit shared state.
- Use semantic naming for components, props, and events.
- Do not introduce a component abstraction unless it reduces repetition or clarifies behavior.
- Reusable components should handle common states where relevant, such as loading, empty, error, disabled, and active states.

## Styling Rules

- Keep styling consistent with `frontend/DESIGN.md`.
- Prefer design tokens, CSS variables, and shared style decisions over hard-coded one-off values.
- Reuse spacing, radius, color, and typography patterns instead of inventing new values for each component.
- Avoid adding visual styles that conflict with the established design language.
- Use motion sparingly and purposefully; transitions should support clarity, not distract from content.
- Do not add a third-party UI framework or utility system unless the task explicitly requires it.

## Responsive Behavior

- Every new UI should work on both desktop and mobile layouts.
- Design for narrow screens intentionally rather than relying on accidental wrapping.
- Protect content hierarchy, readability, and tap targets on small screens.
- Verify that critical flows remain usable across common viewport sizes.

## Accessibility Expectations

- Use semantic HTML wherever possible.
- Ensure interactive elements are keyboard accessible.
- Provide visible focus states for controls.
- Maintain sufficient contrast for text and interactive elements.
- Use meaningful labels, alt text, and accessible names where applicable.
- Do not rely on color alone to communicate status or meaning.

## State and Feedback

- Loading, success, empty, and error states should be explicitly designed.
- Avoid silent failures; surface useful feedback when actions fail.
- Destructive or irreversible actions should be visually and behaviorally clear.
- Prefer straightforward status messaging over vague UI hints.

## Code Quality

- Keep TypeScript types accurate and specific.
- Favor simple composition patterns that match the current codebase.
- Remove dead code, placeholder markup, and unused styles when replacing scaffolding.
- Keep files readable; split code when a file becomes hard to scan.
- Add brief comments only when behavior is non-obvious and the code would otherwise be difficult to parse.

## Delivery Checklist

Before considering frontend work complete, verify that:
- the UI follows `frontend/DESIGN.md`
- the implementation is reusable where reuse is expected
- desktop and mobile layouts are both handled
- interactive states are visible and coherent
- accessibility basics are covered
- type checking and build expectations are not broken
- placeholder template content has been removed when replaced by real product UI
