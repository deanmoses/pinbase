# Analytics Untyped Events Plan

This doc covers the untyped-events track of [AnalyticsPlan.md](AnalyticsPlan.md). Contracts live in [AnalyticsArchitecture.md](AnalyticsArchitecture.md).

This is the launch path. It stands up the SDK with the locked-down privacy config and starts firing anonymous pageviews. No typed events, no backend involvement, no pseudonym, no identify. The PostHog firehose alone answers most of the high-level questions in [AnalyticsQuestions.md § Root questions](AnalyticsQuestions.md#root-questions) — see [AnalyticsPlan.md § Which phase answers which question](AnalyticsPlan.md#which-phase-answers-which-question) for the mapping.

## Phase: Skeleton

Stand up `frontend/src/lib/analytics/` with the module structure from [AnalyticsArchitecture.md § Module Layout](AnalyticsArchitecture.md#module-layout). The SDK is initialized with the locked-down config; pageviews therefore start firing in any environment where `PUBLIC_POSTHOG_KEY` is set to a real value (i.e. staging/prod). The next phase is then a no-code verification phase.

**Deliverables:**

- `index.ts` — public API exporting the active adapter as `analytics`. Selects `noop` when `import.meta.env.DEV`, or when `PUBLIC_POSTHOG_KEY` is missing/blank at runtime, or under SSR (`browser` from `$app/environment` is false); the PostHog adapter otherwise. The SSR fallback to noop keeps server-side `analytics.*` calls from hitting an uninitialized SDK once typed-events lands real call sites. The key-presence check means staging/preview/CI builds without a real key fall back to noop instead of crashing at init. After selecting the PostHog adapter, `index.ts` calls its `init(key)` once. `capture()`, `pageview()`, `identify()`, `reset()` per the [`Analytics` interface](AnalyticsArchitecture.md#the-api). `identify()`/`reset()` are no-ops until typed-events; `pageview()` is a no-op everywhere because PostHog's `capture_pageview: 'history_change'` handles pageviews automatically (the method exists for symmetry with the backend interface and future-proofing if we switch providers).
- `posthog.ts` — PostHog adapter. Module scope is side-effect-free: the only top-level statements are the `import posthog from 'posthog-js'`, the import of the options from `config.ts`, and the exported adapter object with an `init(key)` method that wraps `posthog.init(key, config)`. The browser-only call to `init()` lives in `index.ts`, not at module load. With the init config alone, the SPA pageview firehose is already wired — no additional adapter logic is required at this phase.
- `noop.ts` — no-op adapter for dev and opt-out. The `RecordingAnalytics` test fixture described in [AnalyticsArchitecture.md § Testing](AnalyticsArchitecture.md#testing) ships with the typed-events frontend plan, when the first `analytics.*` call sites land — this phase has none.
- `config.ts` — the literal init options object (including `before_send`), imported by `posthog.ts`. Isolating it makes the integration test below trivial. Specified in [AnalyticsArchitecture.md § Frontend init lockdown](AnalyticsArchitecture.md#frontend-init-lockdown); do not deviate.
- `events.ts` — empty `EventRegistry` type, ready to grow.
- `PUBLIC_POSTHOG_KEY` read via `$env/dynamic/public`. This matches the established project pattern for optional PUBLIC\_ vars (see the `PUBLIC_SENTRY_DSN` handling in [hooks.client.ts](../../../frontend/src/hooks.client.ts) — same shape: optional runtime var + early guard as the master switch). The runtime key check is the master switch for whether events fire; posthog-js itself ships in every production bundle that imports `$lib/analytics`, key or no key (Rollup can't see through a runtime guard, and posthog-js doesn't declare `sideEffects: false`). See [AnalyticsArchitecture.md § Bundle cost](AnalyticsArchitecture.md#bundle-cost) for the rationale. Document `PUBLIC_POSTHOG_KEY` in `.env.example` as a commented-out entry following the `PUBLIC_SENTRY_DSN` precedent; no global "must be defined" contract.
- ESLint `no-restricted-imports` rule banning `posthog-js` outside `posthog.ts`.
- Side-effect import of `$lib/analytics` in `src/routes/+layout.svelte`. Nothing else triggers the analytics module's adapter selection and PostHog `init()` — without this consumer the rest of the skeleton is dead code. Layout is the natural home: it loads on every page and runs before any route-level code.
- `manualChunks` config in `vite.config.ts` that splits `posthog-js` and `@sentry/sveltekit` into their own chunks. Both SDKs load eagerly from the root layout (~150 KB gzipped combined); without splitting they'd land in the layout chunk whose hash rolls on every app deploy, forcing users to re-download unchanged SDK bytes. See [AnalyticsArchitecture.md § Bundle cost](AnalyticsArchitecture.md#bundle-cost).

**Verification:**

- An integration test (vitest) that imports `config.ts` and asserts every locked-down option matches the architecture doc, including driving the `before_send` hook with a synthetic event whose `$current_url` / `$pathname` / `$prev_pageview_pathname` carry query strings, and asserting they come out stripped. Weakening any option fails the test.
- A parametrized vitest covering adapter selection: (a) `DEV=true` → noop, (b) `DEV=false` + blank key → noop, (c) `DEV=false` + key set → PostHog adapter, _and_ `posthog.init` was called exactly once with the key and the config object from `config.ts`. Folding the init-call assertion into case (c) guards the contract that selecting the PostHog adapter actually wires the locked-down init — a refactor that drops the call to `init()` would otherwise pass silently. `PUBLIC_POSTHOG_KEY` comes from `$env/dynamic/public`, so per-case it must be mocked with `vi.doMock('$env/dynamic/public', () => ({ env: { PUBLIC_POSTHOG_KEY: '...' } }))` followed by `vi.resetModules()` before re-importing `index.ts`. `vi.stubEnv` is the right knob for `import.meta.env.DEV`.
- A separate vitest that mocks `posthog-js` and `$app/environment`, then imports `index.ts` with `DEV=false` + a non-empty key under `browser: false`. Assert that `posthog.init` is never called on SSR. The browser-side init-was-called assertion lives in case (c) above.

## Phase: Pageviews

With `capture_pageview: 'history_change'` in the init config, PostHog fires `$pageview` on the initial load and on every SvelteKit CSR navigation automatically — no per-route wiring required. The `before_send` hook in [AnalyticsArchitecture.md § Frontend init lockdown](AnalyticsArchitecture.md#frontend-init-lockdown) strips query strings; PostHog populates `$prev_pageview_pathname` for in-SPA referrer attribution, and the existing `$referrer` / `$referring_domain` cover external referrers.

This phase therefore ships nothing new in code — the Skeleton-phase deliverables (locked-down config + layout-level side-effect import) are the entire implementation. Verification:

- Staging spot-check: load the homepage, click through a few links (including a link with `?foo=bar`), find the events in PostHog. Assert `$pageview` fires on the initial load and each CSR navigation; `$current_url` and `$pathname` have no query string; `$prev_pageview_pathname` reflects the previous in-SPA pathname; `$referrer` / `$referring_domain` reflect the external referring document on the first event of the session.

## Test patterns

The default adapter under vitest is `RecordingAnalytics`, which captures calls into an array and exposes them to assertions. Application code that calls `analytics.*` is tested against `RecordingAnalytics`, never against PostHog.

Two narrow exceptions exercise the PostHog adapter directly, both with `posthog-js` mocked at the module boundary: the `config.ts` integration test asserts the locked-down options (including `before_send`), and the init test asserts `posthog.init` is called once in the browser with that config and never on SSR. Neither hits the network. No other test should import the PostHog adapter.

## What this doc does NOT cover

- The abstraction contract, privacy lockdown spec, naming conventions — those are architecture, see [AnalyticsArchitecture.md](AnalyticsArchitecture.md).
- Typed events (server- or client-side) — see [AnalyticsTypedEventsBackendPlan.md](AnalyticsTypedEventsBackendPlan.md) and [AnalyticsTypedEventsFrontendPlan.md](AnalyticsTypedEventsFrontendPlan.md).
- DB-derived stats — see [AnalyticsDbStatsPlan.md](AnalyticsDbStatsPlan.md).
- Cross-cutting sequencing — see [AnalyticsPlan.md](AnalyticsPlan.md).
