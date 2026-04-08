# Testing

This document describes the project's testing expectations and strategy.

## Running Tests

### Main Commands

- `make test` runs the main backend and frontend test suites
- backend tests use `pytest`
- frontend tests use `vitest`

Use narrower commands when appropriate during development, then widen as needed for confidence.

### Core Rule

For any change, identify and run the smallest meaningful test set.

Do not default to running everything if a narrower test selection will give the answer you need.

### How To Choose a Test Scope

#### Prefer the smallest meaningful scope

Examples:

- a pure backend model/helper change: run the relevant backend tests first
- a frontend component or module change: run the relevant frontend tests first
- a schema or cross-cutting change: run the focused local tests, then widen appropriately

### Widen when risk increases

Run a broader set when:

- the change affects shared infrastructure
- the change crosses app boundaries
- the change affects generated API contracts or backend/frontend integration
- the narrow tests do not give enough confidence

## Writing Tests

### Bug Fixes Require TDD

When fixing a bug, follow this order:

1. Write a failing test that reproduces the bug.
2. Run the test and confirm it fails for the expected reason.
3. Fix the code.
4. Run the test again and confirm it passes.

Do NOT fix the bug first and backfill the test later.

### Backend Testing

Backend tests should generally cover:

- model behavior and DB constraints
- claim/provenance behavior
- ingest behavior
- API behavior
- management command behavior where it matters

When testing DB constraints, prefer direct ORM writes that hit the database constraint path rather than relying on `full_clean()`. See [DataModeling.md](DataModeling.md).

### Frontend Testing

Frontend tests should generally cover:

- TypeScript module logic
- component behavior where UI wiring matters
- data-shape expectations against the API contract where appropriate

Prefer testing logic in small TypeScript units where possible rather than over-relying on broad UI tests.

#### Frontend Test Tiers

The frontend has two vitest **projects** (configured in `vitest.config.ts`) that run in different environments:

| Project | Environment | File pattern    | What to test                                                |
| ------- | ----------- | --------------- | ----------------------------------------------------------- |
| `unit`  | Node        | `*.test.ts`     | Pure functions, SSR renders (`svelte/server`), data helpers |
| `dom`   | jsdom       | `*.dom.test.ts` | Component interactions, event handling, DOM behavior        |

Both run together via `pnpm test`. For focused iteration:

```bash
pnpm test:unit        # unit tests only
pnpm test:dom         # DOM tests only
pnpm test:dom:watch   # DOM tests in watch mode
```

#### Creating a DOM Test

Name the file `*.dom.test.ts` next to the component. The `.dom.` suffix routes it to the jsdom project automatically. Use `@testing-library/svelte` for rendering and queries, `userEvent` for interactions. See `wikilink-autocomplete.dom.test.ts` for the canonical example.

**Gotcha:** when calling exported component methods directly (e.g. `handleExternalKeydown`), wrap in `flushSync` from `svelte` — DOM updates from direct method calls are not automatically flushed.

#### jsdom Polyfills

The DOM project loads `src/tests/setup-dom.ts` which provides:

- `@testing-library/jest-dom/vitest` — DOM matchers (`toBeInTheDocument()`, `toHaveTextContent()`, etc.)
- `Element.prototype.scrollIntoView` — no-op (jsdom doesn't implement it)
- `document.execCommand` — returns `false` (triggers manual text insertion fallbacks)
