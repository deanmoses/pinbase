# Analytics Frontend Plan

Also see:

- [AnalyticsPlan.md](AnalyticsPlan.md) — orchestration and phase ordering
- [AnalyticsArchitecture.md](AnalyticsArchitecture.md) — contracts (abstraction interface, privacy lockdown)
- [AnalyticsBackendPlan.md](AnalyticsBackendPlan.md)
- [AnalyticsEventTaxonomy.md](AnalyticsEventTaxonomy.md)

This doc covers frontend implementation phase by phase. Contracts live in the architecture doc; event names and properties live in the taxonomy. This doc is _how_ to land them.

**Prerequisite:** Backend phase 2 ([AnalyticsBackendPlan.md § account_registered](AnalyticsBackendPlan.md#phase-2-account_registered)) must ship before frontend phase 3, because `identify()` consumes a pseudonym the backend puts in the page payload. Phases 1–2 of the frontend can proceed in parallel with backend work.

## Phase 1: Skeleton

Stand up `frontend/src/lib/analytics/` with the module structure from [AnalyticsArchitecture.md § Module Layout](AnalyticsArchitecture.md#module-layout). No events fire yet.

**Deliverables:**

- `index.ts` — public API exporting the active adapter as `analytics`. `capture()`, `pageview()`, `identify()`, `reset()` per the [`Analytics` interface](AnalyticsArchitecture.md#the-abstraction-api).
- `posthog.ts` — PostHog adapter. The init config goes here, exactly as specified in [AnalyticsArchitecture.md § Privacy Enforcement](AnalyticsArchitecture.md#privacy-enforcement). Do not deviate.
- `noop.ts` — no-op adapter for tests, dev, and opt-out.
- `config.ts` — the literal init options object, imported by `posthog.ts`. Isolating it makes the integration test below trivial.
- `events.ts` — empty `EventRegistry` type, ready to grow.
- `PUBLIC_POSTHOG_KEY` wired through SvelteKit env. Document in `.env.example`.
- ESLint `no-restricted-imports` rule banning `posthog-js` outside `posthog.ts`.

**Verification:**

- An integration test (vitest) that imports `config.ts` and asserts every locked-down option matches the architecture doc. Weakening any option fails the test.
- The dev-mode default adapter is `noop`, not PostHog. Confirm in a dev-run by inspecting the network tab — no requests to `eu.posthog.com`.

## Phase 2: Pageviews

PostHog's auto-pageview is off (`capture_pageview: false`); pageviews fire from a SvelteKit `afterNavigate` hook in the root layout, so every CSR route change is captured — not just the initial SSR load.

**Deliverables:**

- `afterNavigate` hook in `frontend/src/routes/+layout.svelte`:

  ```svelte
  <script lang="ts">
    import { afterNavigate } from "$app/navigation";
    import { analytics } from "$lib/analytics";

    afterNavigate(({ from, to }) => {
      if (!to) return;
      analytics.pageview(to.url.pathname, {
        referrer: from?.url.pathname ?? null,
      });
    });
  </script>
  ```

  `afterNavigate` fires after the initial load **and** after every subsequent CSR navigation, so a single hook covers the whole SPA. Without this, the SPA would look like a one-page-per-visit site to PostHog — pages-per-session would always be 1, bounce rate would be 100%.

- No pageview fires from `+layout.server.ts`. Server-rendered HTML doesn't imply the user saw the page (bots, prefetches, etc.).

**Verification:**

- A vitest using `RecordingAnalytics` that simulates an initial load + two CSR navigations and asserts three pageview events with the expected pathnames and internal `referrer` properties.
- Staging spot-check: load the homepage, click through a few links, find the events in PostHog. Confirm `$referrer` and `$referring_domain` are present (set by PostHog at session start from `document.referrer`), distinct from the internal `referrer` property which holds the previous in-SPA pathname.

## Phase 3: identify() and reset()

Connects authenticated journeys to the backend-derived pseudonym. Depends on the backend exposing pseudonym in the page payload — see [AnalyticsBackendPlan.md § account_registered](AnalyticsBackendPlan.md#phase-2-account_registered).

**Deliverables:**

- Root layout calls `analytics.identify(pseudonym)` once auth state hydrates and confirms the user is logged in. The pseudonym comes from the page payload, not a separate fetch.
- Logout calls `analytics.reset()`, clearing PostHog's in-memory `distinct_id`.
- Default aliasing behavior is accepted: when `identify()` fires after login within the same SPA instance, PostHog aliases the anonymous heap-bound `distinct_id` to the pseudonym, retroactively attributing pre-login browsing to the user. The user has consented to authenticated use; aliasing is bounded to one SPA instance because anonymous ids never persist past document replacement.

**Verification:**

- A vitest using `RecordingAnalytics` that captures a pageview, then calls `identify(p)`, then captures another pageview. Assert both events end up under the same id post-identify (the aliasing behavior).
- A vitest for logout: `identify(p)` → `reset()` → capture. Assert the post-reset event is anonymous (new heap-bound id, not `p`).
- Staging spot-check: log in. In PostHog, confirm the pre-login pageviews are now attributed to the logged-in pseudonym (aliasing succeeded), and the pseudonym is not a recognizable encoding of `user.id`.

## Phase 4: Client events

Land the rest of the client-side taxonomy. Each event ships with the feature it instruments.

**Deliverables:**

- `search_performed`, `search_zero_results` — search results component. Properties per [AnalyticsEventTaxonomy.md § Discovery Events](AnalyticsEventTaxonomy.md#discovery-events).
- `machine_page_viewed` — machine detail route. Fires on view, not on hover/prefetch. Properties per [AnalyticsEventTaxonomy.md § machine_page_viewed](AnalyticsEventTaxonomy.md#machine_page_viewed).
- `edit_started`, `edit_abandoned` — edit-flow lifecycle hooks. Properties per [AnalyticsEventTaxonomy.md § Contribution Events](AnalyticsEventTaxonomy.md#contribution-events).
- All call sites go through `analytics.capture()`. No direct `posthog.capture()` — the lint rule forbids it.

**Verification:**

- A vitest per event using `RecordingAnalytics`. Drive the UI to the state that should fire the event, assert exactly one event with the expected properties.
- For `edit_abandoned`: a vitest that simulates the abandon path (navigate away, close tab) and asserts the event fires. This is the easiest one to forget instrumenting because it has no obvious "user clicked submit" moment.

## Test patterns

The default adapter under vitest is `RecordingAnalytics`, which captures calls into an array and exposes them to assertions:

```ts
test("search records search_performed", () => {
  const a = new RecordingAnalytics();
  doSearch(a, "medieval madness");
  expect(a.events).toEqual([
    {
      event: "search_performed",
      properties: { query_length: 16, results_count: 1, logged_in: false },
    },
  ]);
});
```

The PostHog adapter is never exercised in unit tests. The phase 1 integration test on `config.ts` covers it.

## What this doc does NOT cover

- The abstraction contract, privacy lockdown spec, pseudonymization model — those are architecture, see [AnalyticsArchitecture.md](AnalyticsArchitecture.md).
- Event names and property schemas — see [AnalyticsEventTaxonomy.md](AnalyticsEventTaxonomy.md).
- Backend work — see [AnalyticsBackendPlan.md](AnalyticsBackendPlan.md).
- Cross-cutting sequencing and handoffs — see [AnalyticsPlan.md](AnalyticsPlan.md).
