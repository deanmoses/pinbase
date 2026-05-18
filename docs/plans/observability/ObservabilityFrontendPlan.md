# Observability Frontend Plan

This doc covers frontend implementation of [ObservabilityPlan.md](ObservabilityPlan.md). Contracts live in [ObservabilityArchitecture.md](ObservabilityArchitecture.md).

## Phases

- ✅ DONE: [Prerequisites](#prerequisites) — implement backend, configure scrubbing rules in Sentry
- ✅ DONE: [SDK](#phase-sdk) — install Sentry SDK, init SSR + browser, upload sourcemaps
- ✅ DONE: [User attribution](#phase-user-attribution) — attach id + username to events
- ✅ DONE: [Debug route](#phase-debug-route) — staff-gated on-demand exception triggers

Each phase is its own commit. 🛑 STOP before committing each phase for user review.

## Prerequisites

- [ObservabilityBackendPlan.md](ObservabilityBackendPlan.md) merged — the debug route depends on `Activity.OBSERVABILITY_DEBUG` being registered.
- Advanced Data Scrubbing rules configured on the `flipcommons-frontend` Sentry project (`@email`, `@ip`, `$request.query_string`) per [ObservabilityPlan.md § Prerequisites](ObservabilityPlan.md#prerequisites). These are the same rules already required on `flipcommons-backend`; without them, pattern-shaped PII would be stored even though the in-process layers don't emit it deliberately.

## Phase: SDK

Stand up `@sentry/sveltekit` in SSR and browser, with sourcemap upload at build time. Events flow for unhandled exceptions; no user attribution yet.

**Deliverables:**

- `@sentry/sveltekit` (>= 10.8.0) added to frontend dependencies. `@sentry/vite-plugin` comes transitively via `sentrySvelteKit`.
- `frontend/svelte.config.js` — set `kit.experimental.instrumentation.server: true` so SvelteKit loads `instrumentation.server.ts` before any other server import. `tracing.server` stays unset (we're not tracing).
- `frontend/src/instrumentation.server.ts` — `Sentry.init({...})` exactly per [ObservabilityArchitecture.md § Frontend](ObservabilityArchitecture.md#frontend), gated on a non-empty `PUBLIC_SENTRY_DSN` (SSR is part of the frontend project, not the backend). This is the load-order-safe init site for the OpenTelemetry-powered server SDK; **do not** call `Sentry.init` from `hooks.server.ts`.
- `frontend/src/hooks.server.ts` — exports `handle` and `handleError` only; no `Sentry.init`:

  ```ts
  import { sequence } from "@sveltejs/kit/hooks";
  import * as Sentry from "@sentry/sveltekit";
  import { handleServerError } from "$lib/sentry/handle-error";

  export const handle = sequence(Sentry.sentryHandle());
  export const handleError = Sentry.handleErrorWithSentry(handleServerError);
  ```

  `sentryHandle()` is the doc-blessed server hook; it provides per-request scope isolation so user data from request N doesn't leak into request N+1, and attaches request context to events. Required even though we're not tracing. New app handles get composed into the `sequence(...)` later.

  `handleErrorWithSentry` receives `handleServerError` rather than being called with no argument — see the bullet on `lib/sentry/handle-error.ts` below for why.

- `frontend/src/hooks.client.ts` — `Sentry.init({...})` gated on a non-empty `PUBLIC_SENTRY_DSN`, plus `export const handleError = Sentry.handleErrorWithSentry(handleClientError)`.
- `frontend/src/lib/sentry/handle-error.ts` — exports `handleServerError` and `handleClientError`. Both are passed to `Sentry.handleErrorWithSentry(...)` explicitly so Sentry's `defaultErrorHandler` (which dumps a full stack via `console.error(error?.stack)` for every error, 4xx included) is never used. Sentry's SDK already filters 4xx out of `captureException`, but its default _logging_ behavior would fill build logs with stacks from prerender's link-discovery 404s on `/api/*` preload hints. Our handler logs a single line for 4xx (matching SvelteKit's own `format_server_error` output) and a line plus stack for 5xx (stack also lives in Sentry; the stderr copy gives Railway log readers immediate context to grep by). Unit-tested directly in `handle-error.test.ts`.
- Both `Sentry.init` calls use:
  - `dsn`: both SSR and browser read `PUBLIC_SENTRY_DSN` from `$env/dynamic/public`. SSR is frontend code, so its events go to the `flipcommons-frontend` Sentry project — the same project as the browser. The backend project (`flipcommons-backend`, read by Django from `SENTRY_DSN`) gets Python errors only. Using `$env/dynamic/public` server-side is fine; `PUBLIC_` vars are readable from both runtimes, and `dynamic` (not `static`) keeps the import from failing at build time when the var is unset (the runtime DSN guard is the master switch — a `static` import of an undefined var is a Vite build error rather than a no-op).
  - `environment: "production"`, `release` set to the appropriate `RAILWAY_GIT_COMMIT_SHA` flavor (private on the server, `PUBLIC_` on the browser).
  - `tracesSampleRate: 0`, `sendDefaultPii: false`.
  - SSR init only: `integrations: [Sentry.httpIntegration({ maxIncomingRequestBodySize: 'none' })]` to suppress incoming request body capture. The JS server SDK captures up to 10KB by default — this is the JS equivalent of the backend's `max_request_body_size="never"` and the layer the architecture doc's "SDK never extracts the request body" claim depends on.
  - `integrations`: no `replayIntegration`, no `feedbackIntegration` — omitted entirely so the SDK never ships those bundles to the browser. The bundle-size and recording-cost cases for Session Replay are real; we're explicitly opting out for launch and can revisit once we know our event volume.
  - `ignoreErrors`: a single shared const `IGNORE_ERRORS` exported from `frontend/src/lib/sentry/ignore-errors.ts` and imported by both inits. Single source of truth, no dedicated tests — the list is short enough that the value of a test is below the cost of writing one. Start with the unambiguous noise:
    - `ResizeObserver loop limit exceeded`
    - `ResizeObserver loop completed with undelivered notifications`
    - `Non-Error promise rejection captured`
    - `AbortError` / `The operation was aborted` (navigation aborts, fetch aborts)
    - `ChunkLoadError` / `Loading chunk \d+ failed` (post-deploy stale-bundle navigations)

    Do **not** add generic network-failure strings like `Failed to fetch`, `Load failed`, or `NetworkError when attempting to fetch resource` to the initial list — those can also indicate real production breakage (API endpoint down, CORS misconfig, server returning HTML to a fetch). Add them later only if they actually dominate the noise floor, per [ObservabilityPlan.md](ObservabilityPlan.md)'s "tune after noise appears" policy.

  - **No** `beforeSend`. Privacy enforcement is layered per [ObservabilityArchitecture.md § Privacy enforcement](ObservabilityArchitecture.md#privacy-enforcement): SDK options + built-in scrubber + server-side Advanced Data Scrubbing.

- `frontend/vite.config.ts` — `sentrySvelteKit` plugin configured with the current root-level options shape (the older nested `sourceMapsUploadOptions` is deprecated as of `@sentry/sveltekit@10.x`, and `disable` was never a field on that nested object — it lives on `sourcemaps.disable` in the new shape, but the cleaner gate is `autoUploadSourceMaps`):

  ```ts
  sentrySvelteKit({
    autoUploadSourceMaps:
      !!process.env.SENTRY_AUTH_TOKEN &&
      !!process.env.SENTRY_ORG &&
      !!process.env.SENTRY_PROJECT,
    telemetry: false,
    org: process.env.SENTRY_ORG,
    project: process.env.SENTRY_PROJECT,
    authToken: process.env.SENTRY_AUTH_TOKEN,
    release: { name: process.env.RAILWAY_GIT_COMMIT_SHA, inject: true },
    sourcemaps: {
      filesToDeleteAfterUpload: ["./.svelte-kit/**/*.map", "./build/**/*.map"],
    },
  });
  ```

  Plugin order: `sentrySvelteKit()` before `sveltekit()`, per the SDK docs. `autoUploadSourceMaps` makes the no-secrets local/CI behavior explicit instead of relying on the plugin's internal no-op when `SENTRY_AUTH_TOKEN` is missing; `telemetry: false` opts the build plugin out of phoning home, matching our privacy posture.

- `RAILWAY_GIT_COMMIT_SHA` is the single source of truth for the release name. `vite.config.ts` mirrors it into `process.env.PUBLIC_RAILWAY_GIT_COMMIT_SHA` (only if unset) before SvelteKit builds, so the browser bundle's `release` field, the sourcemap-upload release tag, and the SSR `release` field all derive from the same value by construction. Without this mirror they'd be two separate Railway-side variables that have to stay in sync manually; with it, the Dockerfile only needs to inject `RAILWAY_GIT_COMMIT_SHA` (which it already does for `version.json`).
- `.env.example` documents `SENTRY_DSN`, `PUBLIC_SENTRY_DSN`, `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT` as unset for local/CI. `SENTRY_DSN` (Django → `flipcommons-backend` project) and `PUBLIC_SENTRY_DSN` (SSR + browser → `flipcommons-frontend` project) are **different** DSNs pointing at different projects — see the DSN bullet above for why SSR uses the public one.

**Verification:**

- Vitest: when `PUBLIC_SENTRY_DSN` is unset, neither `instrumentation.server.ts` nor `hooks.client.ts` calls `Sentry.init`. Weakening either guard fails the test.
- Vitest: with `PUBLIC_SENTRY_DSN` set, `instrumentation.server.ts` calls `Sentry.init` with an `integrations` array containing `httpIntegration` configured `{ maxIncomingRequestBodySize: 'none' }`. Pins the JS-server request-body suppression that the architecture doc's privacy contract depends on — a refactor that drops the option fails this test.
- Vitest: mocking both `$env/dynamic/public` (with a frontend DSN) **and** `$env/dynamic/private` (with a _different_ backend DSN), `instrumentation.server.ts` initializes against the frontend DSN. Pins the SSR-routes-to-frontend-project invariant so a refactor that switches back to reading `SENTRY_DSN` fails.
- Build-time smoke check: run a production build locally with `SENTRY_AUTH_TOKEN` unset and confirm the plugin skips upload cleanly rather than failing the build (CI without secrets keeps working).
- Manual post-deploy: trigger a browser exception (dev tools `throw new Error("test")`), confirm it lands in `flipcommons-frontend` with a stack trace resolving to TypeScript source, `release` tag matching `RAILWAY_GIT_COMMIT_SHA`, no email/IP/query-string in the event payload.

## Phase: User attribution

Attach `{id, username}` and the `auth_state` tag to browser-side Sentry events whenever the auth store changes. Browser scope only for v1 — SSR attribution is explicitly deferred (see below).

**Deliverables:**

- [auth.svelte.ts](../../../frontend/src/lib/auth.svelte.ts) `set()` is the chokepoint: every login, refresh, and logout flows through it. Add Sentry calls there:
  - Authenticated → `Sentry.setUser({ id, username })` + `Sentry.setTag('auth_state', 'auth')`
  - Anonymous → `Sentry.setUser(null)` + `Sentry.setTag('auth_state', 'anon')`
- The `{id, username}` keep-list is the **privacy chokepoint** for the user dict — there is no `beforeSend` to catch a refactor that adds `email` or any other field. The call-site docstring flags this load-bearing role and the test below pins it.
- Calls are gated on `Sentry.isInitialized()` so they don't pollute the scope when the SDK isn't initialized (dev / CI / tests), **and** on `typeof window !== 'undefined'`. The browser guard is defensive: `auth.svelte.ts` is a module singleton and is browser-only in practice today, but SSR Sentry is also initialized, so without the window check a future SSR caller of `set()` would attach user data to a per-request scope that survives across requests via the module singleton. Mirrors the existing `registerOnPolicyDenied` guard in the same file.

**SSR attribution — deferred.** The browser auth store doesn't run on the server, so SSR-side events are anonymous in v1. Backend events (where the bulk of authenticated traffic surfaces anyway) still carry full user attribution via `SentryScopeMiddleware`, so the gap is narrow: only SSR-load-time errors during authenticated navigations are missing user context. If that turns out to matter, the fix is a SvelteKit `handle` step composed into `sequence(sentryHandle(), …)` that reads the user from `event.locals` (after auth resolution) and calls `Sentry.setUser` — straightforward, but not worth the auth-resolution-in-`handle` plumbing pre-launch.

**Verification:**

- Vitest drives `auth.refresh()` (or whatever public entry point fetches `/me/`) against a mocked authenticated response → asserts `setUser` was called with exactly `{id, username}` (no other keys) and `setTag('auth_state', 'auth')`; drives `auth.logout()` against a mocked logout response → asserts `setUser(null)` and `setTag('auth_state', 'anon')`. Tests go through the public surface; `set()` stays private. The "exactly `{id, username}`" assertion is what pins the keep-list invariant — a refactor that adds `email` to the `setUser` arg fails the test.
- Manual post-deploy: log in as a staff account, trigger a browser exception, confirm the Sentry event carries the logged-in user's `id` and `username` and no other user fields, with `auth_state: auth` on the tag list.

## Phase: Debug route

Add on-demand exception triggers so the verification checklist in [ObservabilityArchitecture.md § First-event verification](ObservabilityArchitecture.md#first-event-verification) is repeatable for SSR-load-time and browser-side capture paths. (Backend capture is verified via `/api/sentry_test` from the backend plan, not duplicated here.)

**Prerequisite:** `Activity.OBSERVABILITY_DEBUG` must already be registered backend-side (see [ObservabilityBackendPlan.md § Phase: SDK](ObservabilityBackendPlan.md#phase-sdk)).

**Deliverables:**

- `/_sentry_test` SvelteKit route gated by a `+page.server.ts` load that calls `requireCapability({ fetch, url, activity: Activity.OBSERVABILITY_DEBUG })`, matching the pattern in [require-capability.ts](../../../frontend/src/lib/require-capability.ts). Non-staff get redirected to `/login` or `/verify-email` like any other gated route. The same load throws when `url.searchParams.has('throw')`, giving the SSR trigger; `+page.server.ts` is unambiguously server-only, unlike a universal `+page.ts` load (which runs on the server only for the first hit and in the browser for every SPA nav after).
- **Server-only gate, no `+page.ts`.** Other gated routes pair a server gate with a universal gate so SPA navs skip the server round-trip. That pattern currently trips a latent project bug — direct URL hits to any `+page.ts` using `requireCapability` 500 in SSR because `openapi-fetch@0.17` reads `Content-Length` on every response and SvelteKit's hydration-serialization layer filters it out. Direct URL hits are the only path that matters for this route, so server-only gating sidesteps the bug without committing the project to broadening `filterSerializedResponseHeaders`. Fixing the broader issue is tracked separately.
- The page contains two controls:
  1. **"Throw in SSR load"** — `<a href="/_sentry_test?throw=ssr-load" data-sveltekit-reload>`. `data-sveltekit-reload` forces a full document navigation so the request hits the server even when triggered from inside the SPA, which makes the `+page.server.ts` throw fire reliably. Covers SSR-load-time capture via `handleError`.
  2. **"Throw in browser"** — button, `throw`s in an `onclick` handler. Covers browser capture via `handleError` on the client.

**Verification:**

- Vitest for `+page.server.ts` load: non-staff → redirect; staff without `?throw` → succeeds; staff with `?throw=ssr-load` → throws.
- Manual post-deploy: hit `/_sentry_test` as staff, click both controls, confirm two events land in `flipcommons-frontend` (one SSR, one browser) within 30 seconds, both tagged with the deployed release.

## Test patterns

Frontend tests assert on Sentry SDK calls by mocking the `@sentry/sveltekit` module surface used at each call site (`init`, `setUser`, `setTag`, `captureException`, `isInitialized`). The real network transport is never exercised in unit tests. The SDK-phase guard tests are the only place that touch the real init code path, and they assert the DSN guard, not the network.

## What this doc does NOT cover

- The init shape, scrubber layering, sourcemap pipeline, environment separation — those are architecture, see [ObservabilityArchitecture.md](ObservabilityArchitecture.md).
- Backend work — see [ObservabilityBackendPlan.md](ObservabilityBackendPlan.md).
- Cross-cutting sequencing, dashboard setup, alert rules — see [ObservabilityPlan.md](ObservabilityPlan.md).
