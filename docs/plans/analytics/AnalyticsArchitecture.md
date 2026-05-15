# Analytics Architecture

## Provider

[PostHog Cloud (EU region)](https://posthog.com/) is the chosen provider. See [Analytics.md](Analytics.md) for the requirements it satisfies and [AnalyticsVendors.md](AnalyticsVendors.md) for the alternatives considered.

PostHog ships several features that appear in our [non-goals](Analytics.md#non-goals) — autocapture, session replay, heatmaps, surveys, behavioral cohorts. These are disabled at the integration boundary (see [Privacy Enforcement](#privacy-enforcement)). The abstraction layer below is what keeps that discipline enforceable in code review.

## Decouple from Provider

Call our own abstraction throughout the codebase, not the PostHog SDK directly:

```ts
// Right
import { analytics } from "$lib/analytics";
analytics.capture("search_performed", {
  query_length: 12,
  results_count: 0,
  logged_in: false,
});

// Wrong
import posthog from "posthog-js";
posthog.capture("search_performed", { ... });
```

The abstraction buys us:

- **vendor independence** — switching providers is one file
- **centralized privacy enforcement** — non-goal features can't slip in via ad-hoc SDK use
- **typed event surface** — properties are checked against [EventTaxonomy.md](EventTaxonomy.md)
- **testable** — the test harness swaps in a recording implementation
- **consistent naming** — events live in one registry, so no string typos

## Module Layout

```text
frontend/src/lib/analytics/
  index.ts            Public API: capture(), pageview(), identify(), reset()
  events.ts           Typed event registry (mirrors backend)
  posthog.ts          PostHog adapter — the only file that imports posthog-js
  noop.ts             No-op adapter (dev, tests, opt-out)
  config.ts           PostHog init options (the privacy lockdown lives here)

backend/apps/analytics/
  __init__.py         Public API: analytics.capture(), identify()
  events.py           Typed event registry (TypedDicts, mirrors frontend)
  posthog_adapter.py  The only module that imports the posthog package
  noop.py
  middleware.py       Binds the current user's pseudonym to the request
  models.py           AnalyticsIdentity (the pseudonym table)
```

Only the adapter modules import the vendor SDK. Everywhere else imports from `$lib/analytics` or `apps.analytics`. A lint rule pins this — ESLint's `no-restricted-imports` forbids `posthog-js` outside the adapter; ruff's `flake8-tidy-imports` does the same on the backend.

## The Abstraction API

```ts
export interface Analytics {
  pageview(path: string, properties?: PageviewProperties): void;
  capture<E extends EventName>(event: E, properties: EventProperties<E>): void;
  identify(pseudonym: string): void;
  reset(): void; // called on logout
}
```

Mirrored on the backend:

```python
class Analytics(Protocol):
    def capture(
        self,
        event: EventName,
        properties: EventProperties,
        *,
        pseudonym: str | None,
    ) -> None: ...

    def identify(self, pseudonym: str) -> None: ...
```

No `track()`, no `page()`, no provider-specific verbs. No raw properties dict that bypasses the typed registry.

## Identity & Pseudonymization

Every authenticated user has an `analytics_pseudonym` (UUIDv4) stored on a separate `AnalyticsIdentity` row joined to `User` by FK. PostHog only ever sees the pseudonym. Backend code that calls `analytics.capture()` reads the pseudonym from the request context, not from `request.user.id`.

- Created lazily on first identify call (idempotent)
- Rotatable: if a user opts out and back in, a new pseudonym is issued; old PostHog events are stranded under the old ID
- Logout calls `analytics.reset()` on the frontend, clearing PostHog's in-memory state

Anonymous visitors are not assigned a pseudonym. PostHog runs with `persistence: "memory"`: the distinct_id lives only in the JS heap. Because SvelteKit handles in-app navigation client-side, that heap survives every link click within a visit, so pages-per-session, entry/exit pages, and bounce rate all work for normal SPA browsing. A hard refresh or a new tab starts a fresh id — we don't try to link those — which is what "not linked across sessions" means in [Analytics.md](Analytics.md#identifiability). Nothing is written to cookies or storage.

The split between the `User` table and `AnalyticsIdentity` is what satisfies the "decouples analytics data from the authoritative user table" requirement: dropping `AnalyticsIdentity` severs the link, leaving PostHog data with orphan UUIDs.

## Privacy Enforcement

The PostHog adapter pins the following init options. Reviewers reject any change that loosens them:

```ts
posthog.init(PUBLIC_POSTHOG_KEY, {
  api_host: "https://eu.posthog.com",
  persistence: "memory", // no cookies, no storage; SPA navigations stay linked via the JS heap
  autocapture: false, // no implicit click/form tracking
  capture_pageview: false, // we call pageview() explicitly
  capture_pageleave: false,
  disable_session_recording: true,
  disable_surveys: true,
  disable_external_dependencies: true,
  ip: false, // strip client IP at ingest
  property_denylist: ["$ip", "$geoip_*"],
});
```

The backend SDK gets the same treatment:

```python
posthog.host = "https://eu.posthog.com"
posthog.disable_geoip = True
```

Mapping to the [non-goals](Analytics.md#non-goals):

| Non-goal                  | Enforcement                                                  |
| ------------------------- | ------------------------------------------------------------ |
| Cookies                   | `persistence: "memory"` (no cookies, no storage)             |
| Behavioral fingerprinting | `autocapture: false`, `disable_session_recording: true`      |
| Cross-site tracking       | EU host, no third-party cookies, no advertising integrations |
| IP-based profiling        | `ip: false`, `disable_geoip = True`                          |
| Engagement-addiction      | `disable_surveys: true`, no feature-flag SDK use             |

## Where Events Originate

| Event                                     | Origin | Why                                                   |
| ----------------------------------------- | ------ | ----------------------------------------------------- |
| pageviews                                 | client | needs real navigation, including SvelteKit CSR        |
| `search_performed`, `search_zero_results` | client | fires from the search UI                              |
| `machine_page_viewed`                     | client | server can't distinguish CSR routes from anchor jumps |
| `edit_started`, `edit_abandoned`          | client | UI lifecycle signals; never reach the server          |
| `edit_saved`, `photo_uploaded`            | server | post-write, must reflect the actual mutation          |
| `account_registered`                      | server | fires inside the signup transaction                   |
| `moderation_action`                       | server | server-only action                                    |

Server-side events flow through the Python adapter using the pseudonym attached to the request by middleware. Anonymous server-side events (rare) use a fresh random distinct_id and are not linked across requests.

## Typed Events

The event registry is the single source of truth for event names and property shapes. Adding an event means adding a row to both `events.ts` and `events.py`; a contract test asserts the two registries agree.

```ts
type EventRegistry = {
  search_performed: {
    query_length: number;
    results_count: number;
    logged_in: boolean;
  };
  search_zero_results: { normalized_query: string; logged_in: boolean };
  edit_saved: {
    page_type: PageType;
    duration_seconds: number;
    is_first_edit: boolean;
  };
  // ...
};
```

Per the project's [strong-typing rule](../../Python.md), backend properties are TypedDicts, not `dict[str, Any]`. Adding a property to an event without updating the registry is a type error on both sides.

## Testing

The default adapter in tests is `RecordingAnalytics`, which captures calls into an array and exposes them to assertions:

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

The PostHog adapter is never exercised in unit tests. One integration test asserts that `init()` is called with the locked-down config above; if anyone weakens an option, that test fails.

## Migration Path

The provider boundary is one file per side (`posthog.ts`, `posthog_adapter.py`) plus the init config. Migrating to a different provider — or splitting traffic and product analytics across two providers — means:

1. Write a new adapter implementing `Analytics`.
2. Swap the export in `index.ts` / `__init__.py`.
3. Update the event registry only if the new provider has naming constraints.

No call sites change. The pseudonym table is portable because it's our column, not a PostHog-issued ID.
