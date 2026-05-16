# Analytics Architecture

Also see:

- [Analytics.md](Analytics.md) — product motivation, goals, non-goals
- [AnalyticsVendors.md](AnalyticsVendors.md) — vendor comparison
- [AnalyticsEventTaxonomy.md](AnalyticsEventTaxonomy.md) — event names and property shapes
- [AnalyticsPlan.md](AnalyticsPlan.md) — phased rollout

This doc is the contract: what is true regardless of which events we ship. Implementation phasing lives in [AnalyticsPlan.md](AnalyticsPlan.md) and its child plans.

## Provider

[PostHog Cloud](https://posthog.com/) is the chosen analytics provider. See [AnalyticsVendors.md](AnalyticsVendors.md) for the vendor comparison.

PostHog ships several features that appear in our [non-goals](Analytics.md#non-goals): autocapture, session replay, heatmaps, surveys, behavioral cohorts. These are disabled at the integration boundary (see [Privacy Enforcement](#privacy-enforcement)). The abstraction layer below is what keeps that discipline enforceable in code review.

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

- **vendor independence** — switching providers is one file (see [Migration Path](#migration-path))
- **centralized privacy enforcement** — non-goal features can't slip in via ad-hoc SDK use
- **typed event surface** — properties are checked against [AnalyticsEventTaxonomy.md](AnalyticsEventTaxonomy.md)
- **testable** — the test harness swaps in a recording implementation
- **consistent naming** — events live in one registry, so no string typos

## Module Layout

```text
frontend/src/lib/analytics/
  index.ts            Public API: capture(), pageview(), identify(), reset()
  events.ts           Typed event registry (frontend-emitted events)
  posthog.ts          PostHog adapter — the only file that imports posthog-js
  noop.ts             No-op adapter (dev, tests, opt-out)
  config.ts           PostHog init options (the privacy lockdown lives here)

backend/apps/analytics/
  __init__.py         Public API: analytics.capture(), identify()
  events.py           Typed event registry (server-emitted events, as TypedDicts)
  posthog_adapter.py  The only module that imports the posthog package
  noop.py
  pseudonym.py        HMAC-based pseudonym derivation
  middleware.py       Derives the request user's pseudonym and caches it per-request
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

Every event is attributed under a single id within one SPA instance — from initial page load through every CSR navigation until the tab is closed or the document is replaced:

- **Anonymous visitors** — a heap-bound `distinct_id`, regenerated each new SPA instance. Not linked across instances (a hard refresh or new tab starts fresh).
- **Logged-in users** — a per-user pseudonym, derived from `user.id`. A contributor's journeys stitch together across instances via the pseudonym.

PostHog only ever sees the pseudonym, never `user.id` or any other identity field. The pseudonym is **derived, not stored**:

```python
def pseudonym_for(user_id: int) -> str:
    return hmac.new(
        settings.ANALYTICS_PSEUDONYM_KEY.encode(),
        str(user_id).encode(),
        hashlib.sha256,
    ).hexdigest()
```

`ANALYTICS_PSEUDONYM_KEY` lives in environment configuration, never in the database. There is no `AnalyticsIdentity` table and no FK keyed on the pseudonym — PostHog data cannot be joined to the `User` table by any SQL query against our application database. Recovering the link requires both a database copy **and** the secret key.

This is what makes the "decouples analytics data from the authoritative user table" requirement in [Analytics.md](Analytics.md#identifiability) true: the decoupling is absence of a join, not indirection through another table.

### Salt rotation

Rotating `ANALYTICS_PSEUDONYM_KEY` orphans every previously-attributed event under its old pseudonym. Aggregate counts inside PostHog survive rotation; the user→pseudonym link does not. This is the mechanism behind the "retention proportional to identifiability" principle in [Privacy.md](../../Privacy.md#retention) — raw events can be retained indefinitely because the link to a user account is bounded by the rotation cadence.

### Opt-out

A user opting out triggers a PostHog delete API call for their current pseudonym; nothing in our database needs to change. If they later opt back in, the same `user.id` and key produce the same pseudonym, but the prior history is gone.

### Anonymous visitors

Not assigned a pseudonym. PostHog runs with `persistence: "memory"` (see [Privacy Enforcement](#privacy-enforcement)): the `distinct_id` lives only in the JS heap, with no cookie or storage. When the document is replaced, the id is gone.

### Where identify() runs

The contract is symmetric across the two sides; implementation detail lives in the plan docs.

- **Frontend** — the root layout calls `analytics.identify(pseudonym)` once auth state hydrates. The pseudonym arrives in the page payload alongside the user object. Logout calls `analytics.reset()`. Details in [AnalyticsFrontendPlan.md § Phase 3](AnalyticsFrontendPlan.md#phase-3-identify-and-reset).
- **Backend** — `analytics.capture()` takes the pseudonym as a keyword argument. Middleware derives it once per request via `pseudonym_for(request.user.id)` and caches it on the request object so every view sees the same value. Details in [AnalyticsBackendPlan.md § Phase 1](AnalyticsBackendPlan.md#phase-1-skeleton).

### Anonymous-to-logged-in linking

When `identify(pseudonym)` runs after login within the same SPA instance, PostHog's default behavior is to alias the in-heap anonymous `distinct_id` to the pseudonym — so the minutes of pre-login browsing in that instance get retroactively attributed to the user's account. We accept this: the user has just consented to authenticated use, and the linkage is bounded to one SPA instance (anonymous history from previous instances is unreachable, because anonymous ids are heap-only). If we ever need to suppress aliasing, pass `$anon_distinct_id: null` to `posthog.identify()`.

## Privacy Enforcement

We do not link anonymous journeys across SPA instances, fingerprint, set cookies, or persist any identifier to storage. The PostHog adapter pins the following init options to enforce that. Reviewers reject any change that loosens them:

```ts
posthog.init(PUBLIC_POSTHOG_KEY, {
  api_host: "https://eu.posthog.com",
  persistence: "memory", // no cookies, no storage; SPA navigations stay linked via the JS heap
  autocapture: false, // no implicit click/form tracking
  capture_pageview: false, // we call pageview() explicitly from afterNavigate
  capture_pageleave: false,
  disable_session_recording: true,
  disable_surveys: true,
  disable_external_dependency_loading: true,
  ip: false, // strip client IP at ingest (also disables server-side geoip)
  property_denylist: [
    "$ip", // belt-and-suspenders alongside ip: false
    "$screen_height", // entropy-bearing, used in fingerprinting
    "$screen_width",
    "$viewport_height",
    "$viewport_width",
  ],
});
```

The backend SDK gets the same treatment:

```python
posthog.host = "https://eu.posthog.com"
posthog.disable_geoip = True
```

An integration test on each side asserts these options are wired up; weakening any of them fails the test (see [AnalyticsBackendPlan.md](AnalyticsBackendPlan.md#phase-1-skeleton) and [AnalyticsFrontendPlan.md](AnalyticsFrontendPlan.md#phase-1-skeleton)).

Mapping to the [non-goals](Analytics.md#non-goals):

| Non-goal                  | Enforcement                                                                                                                         |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Cookies                   | `persistence: "memory"` (no cookies, no storage)                                                                                    |
| Behavioral fingerprinting | `autocapture: false`, `disable_session_recording: true`, screen and viewport properties denylisted                                  |
| Cross-site tracking       | PostHog is a first-party analytics tool, not a cross-property tracking network; no third-party cookies, no advertising integrations |
| IP-based profiling        | `ip: false`, `disable_geoip = True`, `$ip` denylisted as belt-and-suspenders                                                        |
| Engagement-addiction      | `disable_surveys: true`, no feature-flag SDK use                                                                                    |

## Where Events Originate

Events are emitted from the side that has the truth. Client-side captures UI lifecycle and CSR navigation; server-side captures post-write confirmation and transactional moments.

| Event                                     | Origin | Why                                                   |
| ----------------------------------------- | ------ | ----------------------------------------------------- |
| pageviews                                 | client | CSR navigations don't reach the server                |
| `search_performed`, `search_zero_results` | client | search executes client-side                           |
| `machine_page_viewed`                     | client | server can't distinguish CSR routes from anchor jumps |
| `edit_started`, `edit_abandoned`          | client | UI lifecycle signals never reach the server           |
| `edit_saved`, `photo_uploaded`            | server | post-write — must reflect the actual mutation         |
| `account_registered`                      | server | fires inside the signup transaction                   |
| `moderation_action`                       | server | moderation runs server-side                           |

Pageviews fire from a SvelteKit `afterNavigate` hook, not auto-capture, so every CSR route change is recorded — not just the initial SSR load. Without explicit firing, the SPA would look like a one-page-per-visit site to PostHog. Implementation in [AnalyticsFrontendPlan.md § Phase 2](AnalyticsFrontendPlan.md#phase-2-pageviews).

Server-side events flow through the Python adapter using the pseudonym attached to the request by middleware. All server-side events in the registry require an authenticated user; there are no anonymous server-side events.

## Typed Events

The event registry is the single source of truth for event names and property shapes. Each side has its own registry covering only the events it emits — the frontend and backend taxonomies are disjoint (see [Where Events Originate](#where-events-originate)). Both registries exist so `analytics.capture()` calls are type-checked and properties never devolve to `dict[str, Any]`.

```ts
// events.ts — frontend-emitted events
type EventRegistry = {
  search_performed: {
    query_length: number;
    results_count: number;
    logged_in: boolean;
  };
  // ... see AnalyticsEventTaxonomy.md for the full list
};
```

```python
# events.py — server-emitted events
class EditSaved(TypedDict):
    page_type: PageType
    duration_seconds: int
    is_first_edit: bool


# ... see AnalyticsEventTaxonomy.md for the full list
```

Per the project's [strong-typing rule](../../Python.md), backend properties are TypedDicts, not `dict[str, Any]`. Adding a property to an event without updating the registry is a type error on both sides.

Full event list and property semantics live in [AnalyticsEventTaxonomy.md](AnalyticsEventTaxonomy.md).

## Testing

Both sides use a `RecordingAnalytics` adapter as the default test fixture, capturing calls into an array for assertions. The PostHog adapter is never exercised in unit tests — one integration test per side asserts the locked-down init config and nothing else.

Concrete test patterns live in [AnalyticsBackendPlan.md § Test patterns](AnalyticsBackendPlan.md#test-patterns) and [AnalyticsFrontendPlan.md § Test patterns](AnalyticsFrontendPlan.md#test-patterns).

## Migration Path

The provider boundary is one file per side (`posthog.ts`, `posthog_adapter.py`) plus the init config. Migrating to a different provider — or splitting traffic and product analytics across two providers — means:

1. Write a new adapter implementing `Analytics`.
2. Swap the export in `index.ts` / `__init__.py`.
3. Update the event registry only if the new provider has naming constraints.

No call sites change. Pseudonyms are portable because they're derived from `user.id` and a key we own, not a PostHog-issued ID.
