# Observability Frontend Plan

This doc covers frontend implementation of [ObservabilityPlan.md](ObservabilityPlan.md). Contracts live in [ObservabilityArchitecture.md](ObservabilityArchitecture.md).

## Prerequisites

Implement [ObservabilityBackendPlan.md](ObservabilityBackendPlan.md) first, because the debug route depends on `Activity.OBSERVABILITY_DEBUG` being registered on the backend.

## Phase: SDK

Stand up `@sentry/sveltekit` in both SSR and browser, with sourcemap upload at build time. Events flow for unhandled exceptions; no user attribution yet.

**Deliverables:**

- `@sentry/sveltekit` added to frontend dependencies.
- `frontend/src/hooks.server.ts` — `Sentry.init({...})` exactly per [ObservabilityArchitecture.md § Frontend init contract](ObservabilityArchitecture.md#frontend-init-contract), gated on a non-empty DSN. `handleErrorWithSentry` exported as `handleError`.
- `frontend/src/hooks.client.ts` — same pair, with the `ignoreErrors` noise floor (`ResizeObserver loop limit exceeded`, extension network errors, `Non-Error promise rejection captured`) inline next to init so future maintainers can find it.
- Both inits use `release: env.PUBLIC_RAILWAY_GIT_COMMIT_SHA`, `environment: "production"`, `tracesSampleRate: 0`, replay disabled, feedback widget disabled.
- `beforeSend` in each init mirrors the backend scrubber. Sync is kept by code review, not a shared module (the two SDKs have different event shapes).
- `frontend/vite.config.ts` — `sentrySvelteKit` plugin configured with `SENTRY_ORG`, `SENTRY_PROJECT`, `SENTRY_AUTH_TOKEN`, and `sourcemaps.filesToDeleteAfterUpload` set so maps don't ship to browsers.
- `RAILWAY_GIT_COMMIT_SHA` re-exposed as `PUBLIC_RAILWAY_GIT_COMMIT_SHA` in the SvelteKit env so the browser bundle gets the release tag baked in at build time. Already wired into the Dockerfile and `svelte.config.js`.
- `.env.example` documents all four Sentry env vars as unset for local/CI.

**Verification:**

- Unit test (vitest) asserting that when DSN is unset, neither `hooks.server.ts` nor `hooks.client.ts` calls `Sentry.init`. Weakening either guard fails this test.
- Unit test for the `beforeSend` callbacks: feeds a representative event with cookies, `Authorization`, a password field, a CSRF token, an email in `extra`, and an IP. Asserts each is stripped.
- Build-time smoke check: run a production build locally with `SENTRY_AUTH_TOKEN` unset and confirm the plugin skips upload cleanly instead of failing the build (so CI without secrets keeps working).
- Manual post-deploy: trigger a browser exception (any existing button that errors, or open dev tools and `throw new Error("test")`), confirm it lands in `flipcommons-frontend` with stack trace resolving to TypeScript source, release tag matching `RAILWAY_GIT_COMMIT_SHA`, no PII.

## Phase: User attribution

Attach `{id, username}` to the Sentry scope for authenticated users so events can be grouped by user.

**Deliverables:**

- The auth layout's `load` function calls `Sentry.setUser({ id, username })` when an authenticated user is present and `Sentry.setUser(null)` on logout. No email, no IP.

**Verification:**

- Vitest that drives a login → assert `setUser` was called with `{id, username}`; drive a logout → assert `setUser(null)`.
- Manual post-deploy: log in as a staff account, trigger an exception, confirm the Sentry event carries the logged-in user's id and username and no other user fields.

## Phase: Debug route

Add an on-demand exception trigger so the verification checklist in [ObservabilityArchitecture.md § First-event verification](ObservabilityArchitecture.md#first-event-verification) is repeatable for both SSR-load-time and browser-side capture paths.

**Prerequisite:** `Activity.OBSERVABILITY_DEBUG` must already be registered backend-side (see [ObservabilityBackendPlan.md § Debug route](ObservabilityBackendPlan.md#phase-debug-route)).

**Deliverables:**

- `/_sentry_test` SvelteKit route. The `+page.ts` load function calls `requireCapability({ fetch, url, activity: Activity.OBSERVABILITY_DEBUG })`, matching the pattern in [require-capability.ts](../../../frontend/src/lib/require-capability.ts). Non-staff get redirected to `/login` or `/verify-email` like any other gated route.
- The page contains two buttons: one calls `/api/sentry_test` (covers backend round-trip), one `throw`s in a client-side handler (covers browser capture).

**Verification:**

- Vitest for the load function: non-staff session → expects the redirect; staff session → expects load to succeed.
- Manual post-deploy: hit `/_sentry_test` as staff, click both buttons, confirm one event lands in `flipcommons-backend` and one in `flipcommons-frontend` within 30 seconds, both tagged with the deployed release.

## Test patterns

Frontend tests assert on Sentry SDK calls by mocking the `@sentry/sveltekit` module surface used at each call site (`init`, `setUser`, `captureException`). The real network transport is never exercised in unit tests. The SDK-phase guard tests are the only place that touch the real init code path, and they assert the DSN guard, not the network.

## What this doc does NOT cover

- The init shape, scrubber spec, sourcemap pipeline, environment separation — those are architecture, see [ObservabilityArchitecture.md](ObservabilityArchitecture.md).
- Backend work — see [ObservabilityBackendPlan.md](ObservabilityBackendPlan.md).
- Cross-cutting sequencing, dashboard setup, alert rules — see [ObservabilityPlan.md](ObservabilityPlan.md).
