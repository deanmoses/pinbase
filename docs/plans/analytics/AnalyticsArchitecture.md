# Analytics Architecture

Also see:

- [Analytics.md](Analytics.md)
- [AnalyticsVendors.md](AnalyticsVendors.md)
- [EventTaxonomy.md](EventTaxonomy.md)
- [PublicDashboardIdeas.md](PublicDashboardIdeas.md)

## Provider

[PostHog Cloud](https://posthog.com/) is the chosen analytics provider.

PostHog ships several features that appear in our [non-goals](Analytics.md#non-goals) — autocapture, session replay, heatmaps, surveys, behavioral cohorts. These are disabled at the integration boundary (see [Privacy Enforcement](#privacy-enforcement)). The abstraction layer below is what keeps that discipline enforceable in code review.

## Tracking Scope

**We deliberately track a user's journey across one HTTP instance of the SPA.** From the initial page load through every client-side route change, search, and contribution event, until the tab is closed or the document is replaced (hard refresh, external navigation). This is the product goal of analytics, not an incidental side-effect — we want to answer questions like:

- What do visitors read after the homepage?
- Which entry pages lead to a search? To a contribution?
- Where do contributors drop off in the edit flow?
- Which referrers bring people who actually explore vs. bounce?

Within one SPA instance, every event is linked under a single id:

- **Anonymous visitors** — a heap-bound `distinct_id`, regenerated for each new SPA instance. Not linked across instances (a hard refresh or new tab starts fresh).
- **Logged-in users** — the per-user pseudonym (see [Identity & Pseudonymization](#identity--pseudonymization)). A contributor's journeys stitch together across instances via the pseudonym.

What we explicitly do **not** do: link anonymous journeys across SPA instances, fingerprint, set cookies, or persist any identifier to storage.

See [Pageviews](#pageviews) for the mechanism that turns CSR route changes into recorded events.

## Pageviews

PostHog's auto-pageview is off. Pageviews fire from a SvelteKit [`afterNavigate`](https://svelte.dev/docs/kit/$app-navigation#afterNavigate) hook in the root layout, so every client-side route change is captured — not just the initial SSR load:

```svelte
<!-- frontend/src/routes/+layout.svelte -->
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

`afterNavigate` fires after the initial load **and** after every subsequent CSR navigation, so a single hook covers the whole SPA. Without this, the SPA would look like a one-page-per-visit site to PostHog — pages-per-session would always be 1 and bounce rate would be 100%. These are per-instance aggregate counts that need no persistent identity, consistent with [Analytics.md's reach-as-volume stance](Analytics.md#visitor-traffic-analytics).

External referrer (`document.referrer`) is captured by PostHog at session start as `$referrer` and `$referring_domain`. The internal `referrer` property in the hook above is the previous in-SPA pathname, used for journey reconstruction.

No pageview is fired from `+layout.server.ts`: server-rendered HTML doesn't imply the user actually saw the page (bots, prefetches, etc.).

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

PostHog only ever sees a per-user pseudonym, never `user.id` or any other identity field. The pseudonym is **derived, not stored**:

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

Not assigned a pseudonym. PostHog runs with `persistence: "memory"`: the `distinct_id` lives only in the JS heap, with no cookie or storage. That heap-bound id is what links anonymous events within one SPA instance (see [Tracking Scope](#tracking-scope)); when the document is replaced, the id is gone.

### When `identify()` is called

- **Frontend** — the root layout calls `analytics.identify(pseudonym)` once auth state hydrates and confirms the user is logged in. The pseudonym arrives in the page payload alongside the user object. On logout, the layout calls `analytics.reset()`, clearing PostHog's in-memory state.
- **Backend** — `analytics.capture()` derives the pseudonym from `request.user.id` via `pseudonym_for()`; middleware caches it per-request so the signup view's `account_registered` event uses the same value as every subsequent event.

### Anonymous-to-logged-in linking

When `identify(pseudonym)` runs after login within the same SPA instance, PostHog's default behavior is to alias the in-heap anonymous `distinct_id` to the pseudonym — so the minutes of pre-login browsing in that instance get retroactively attributed to the user's account. We accept this: the user has just consented to authenticated use, and the linkage is bounded to one SPA instance (anonymous history from previous instances is unreachable, because anonymous ids are heap-only). If we ever need to suppress aliasing, pass `$anon_distinct_id: null` to `posthog.identify()`.

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

Mapping to the [non-goals](Analytics.md#non-goals):

| Non-goal                  | Enforcement                                                                                                                         |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Cookies                   | `persistence: "memory"` (no cookies, no storage)                                                                                    |
| Behavioral fingerprinting | `autocapture: false`, `disable_session_recording: true`, screen and viewport properties denylisted                                  |
| Cross-site tracking       | PostHog is a first-party analytics tool, not a cross-property tracking network; no third-party cookies, no advertising integrations |
| IP-based profiling        | `ip: false`, `disable_geoip = True`, `$ip` denylisted as belt-and-suspenders                                                        |
| Engagement-addiction      | `disable_surveys: true`, no feature-flag SDK use                                                                                    |

## Where Events Originate

| Event                                     | Origin | Why                                                   |
| ----------------------------------------- | ------ | ----------------------------------------------------- |
| pageviews                                 | client | CSR navigations don't reach the server                |
| `search_performed`, `search_zero_results` | client | search executes client-side                           |
| `machine_page_viewed`                     | client | server can't distinguish CSR routes from anchor jumps |
| `edit_started`, `edit_abandoned`          | client | UI lifecycle signals never reach the server           |
| `edit_saved`, `photo_uploaded`            | server | post-write — must reflect the actual mutation         |
| `account_registered`                      | server | fires inside the signup transaction                   |
| `moderation_action`                       | server | moderation runs server-side                           |

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
  search_zero_results: { normalized_query: string; logged_in: boolean };
  machine_page_viewed: {
    machine_id: string;
    manufacturer: string;
    era: Era;
    has_media: boolean;
  };
  edit_started: { page_type: PageType; logged_in: boolean };
  edit_abandoned: { page_type: PageType; duration_seconds: number };
};
```

```python
# events.py — server-emitted events
class EditSaved(TypedDict):
    page_type: PageType
    duration_seconds: int
    is_first_edit: bool


class PhotoUploaded(TypedDict):
    machine_id: str
    image_type: ImageType
    upload_size_bucket: SizeBucket


class AccountRegistered(TypedDict):
    referral_source: str | None
    invite_source: str | None


class ModerationAction(TypedDict):
    action_type: ModerationActionType
    content_type: ContentType
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

No call sites change. Pseudonyms are portable because they're derived from `user.id` and a key we own, not a PostHog-issued ID.
