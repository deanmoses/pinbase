# Frontend Improvements

Audit of `frontend/` against modern SvelteKit best practices. The setup is already strong — Svelte 5 runes, current SvelteKit/Vite/TS/ESLint-flat/Prettier 3, `openapi-typescript` + `openapi-fetch` wired to Django Ninja, strict TS, vitest unit/DOM split, `adapter-node`. The items below are additive.

## High value

- **Add Playwright E2E tests.** No end-to-end coverage today. Auth, create/edit, and revert flows aren't exercised by unit or DOM tests. Pairs naturally with `adapter-node`. Add a `test:e2e` script.
- **Bundle visibility.** No `rollup-plugin-visualizer` (or equivalent). Worth a one-time run to see where FontAwesome and other heavy deps sit in the bundle.

## Medium value

- **Evaluate FontAwesome → lucide-svelte.** Lucide is tree-shaken per-icon and small; FA typically ships more than is used. Decide by measuring current icon-related bundle weight.
- **MSW for API mocking.** Tests currently either hit the real client or hand-stub. [MSW](https://mswjs.io) gives one mock layer that works across unit and E2E.
- **Frontend-scoped pre-commit.** Repo has root pre-commit hooks but no `lint-staged` on staged frontend files specifically. Minor DX win.

## Low / optional

- **Commitlint** — only if conventional commits are to be enforced.
- **Changesets** — overkill for a single-app monorepo; skip unless per-package versioning becomes a need.
- **paraglide / inlang** — only if i18n lands on the roadmap.

## Explicitly not changing

- **Runes-mode adoption** — complete, no legacy patterns.
- **`openapi-typescript` + `openapi-fetch`** — the modern choice; do not swap for tRPC-style tooling.
- **No Tailwind** — Open Props + scoped Svelte CSS is a deliberate, defensible choice given the `:global` restriction in CLAUDE.md.
- **`adapter-node`** — correct given the Caddy + Django co-hosted Railway deployment.

## Scripts

Current set (`dev`, `build`, `preview`, `start`, `check`, `check:watch`, `lint`, `format`, `test`, `test:unit`, `test:dom`, `api:gen`) is complete. Additions implied by the items above: `test:e2e` (Playwright) and `knip`.

## Suggested order

1. knip (fastest signal, zero risk)
2. Bundle visualizer run (one-off, informs icon decision)
3. Playwright + first critical-path spec
4. MSW once Playwright is in place
