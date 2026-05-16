# Analytics Architecture

Also see:

- [Analytics.md](Analytics.md) — product motivation, goals, non-goals
- [AnalyticsVendors.md](AnalyticsVendors.md) — vendor comparison
- [AnalyticsPlan.md](AnalyticsPlan.md) — phased rollout
  - [AnalyticsBackendPlan.md](AnalyticsBackendPlan.md) — backend implementation plan
  - [AnalyticsFrontendPlan.md](AnalyticsFrontendPlan.md) — frontend implementation plan

## A note on code blocks

Each fenced code block is tagged as one of:

- **Literal** — appears in the codebase verbatim. Implementers and reviewers should treat the block as a contract; the integration tests and lint rules enforce it.
- **Pseudocode** — illustrates a pattern or structure. The exact text is not in the codebase; the canonical definition lives in a linked doc or in the code itself. Reviewers should not flag drift between these snippets and real code.

## The Abstraction

Call our own abstraction throughout the codebase, never the vendor SDK directly:

**Pseudocode (illustrates the call pattern; `someVendor` is a placeholder, and `search_performed` is an illustrative candidate event name pending design):**

```ts
// Right
import { analytics } from "$lib/analytics";
analytics.capture("search_performed", {
  query_length: 12,
  results_count: 0,
  logged_in: false,
});

// Wrong
import someVendor from "some-vendor-sdk";
someVendor.capture("search_performed", { ... });
```

The abstraction buys us:

- **vendor independence** — switching providers is one file (see [Migration](#migration) below)
- **centralized privacy enforcement** — non-goal features can't slip in via ad-hoc SDK use
- **typed event surface** — properties are checked against the typed event registry in code (`events.ts` / `events.py`)
- **testable** — the harness swaps in a recording implementation (see [Testing](#testing) below)
- **consistent naming** — events live in one registry, so no string typos

### Module Layout

**Pseudocode (structure is normative; `<vendor>` placeholders are bound in [Provider Binding](#provider-binding-posthog)):**

```text
frontend/src/lib/analytics/
  index.ts            Public API: capture(), pageview(), identify(), reset()
  events.ts           Typed event registry (frontend-emitted events)
  <vendor>.ts         Vendor adapter — the only file that imports the vendor SDK
  noop.ts             No-op adapter (dev, tests, opt-out)
  config.ts           Vendor init options (the privacy lockdown lives here)

backend/apps/analytics/
  __init__.py         Public API: analytics.capture(), identify()
  events.py           Typed event registry (server-emitted events, as TypedDicts)
  <vendor>_adapter.py The only module that imports the vendor SDK
  noop.py
  pseudonym.py        HMAC-based pseudonym derivation
  middleware.py       Derives the request user's pseudonym and caches it per-request
```

Only the adapter modules import the vendor SDK. Everywhere else imports from `$lib/analytics` or `apps.analytics`. A lint rule pins this — ESLint's `no-restricted-imports` forbids the vendor SDK outside the adapter; ruff's `flake8-tidy-imports` does the same on the backend.

Concrete adapter filenames are determined by the chosen provider — see [Provider Binding](#provider-binding-posthog).

### The API

**Literal:**

```ts
export interface Analytics {
  pageview(path: string, properties?: PageviewProperties): void;
  capture<E extends EventName>(event: E, properties: EventProperties<E>): void;
  identify(pseudonym: string): void;
  reset(): void; // called on logout
}
```

Mirrored on the backend.

**Literal:**

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

### Where identify() runs

- **Frontend** — the root layout calls `analytics.identify(pseudonym)` once auth state hydrates. The pseudonym arrives in the page payload alongside the user object. Logout calls `analytics.reset()`. Details in [AnalyticsFrontendPlan.md § Phase 3](AnalyticsFrontendPlan.md#phase-3-identify-and-reset).
- **Backend** — `analytics.capture()` takes the pseudonym as a keyword argument. Middleware derives it once per request via `pseudonym_for(request.user.id)` and caches it on the request object so every view sees the same value. Details in [AnalyticsBackendPlan.md § Phase 1](AnalyticsBackendPlan.md#phase-1-skeleton).

### Testing

Both sides use a `RecordingAnalytics` adapter as the default test fixture, capturing calls into an array for assertions. The vendor adapter is never exercised in unit tests — one integration test per side asserts the locked-down init config and nothing else.

Concrete test patterns live in [AnalyticsBackendPlan.md § Test patterns](AnalyticsBackendPlan.md#test-patterns) and [AnalyticsFrontendPlan.md § Test patterns](AnalyticsFrontendPlan.md#test-patterns).

### Migration

The vendor boundary is one file per side (the adapter) plus the init config. Migrating means:

1. Write a new adapter implementing `Analytics`.
2. Swap the export in `index.ts` / `__init__.py`.
3. Update the event registry only if the new provider has naming constraints.

No call sites change. Pseudonyms are portable because they're derived from `user.id` and a key we own, not a vendor-issued ID.

## Identity & Pseudonymization

Every event is attributed under a single id within one SPA instance — from initial page load through every CSR navigation until the tab is closed or the document is replaced:

- **Anonymous visitors** — a heap-bound `distinct_id`, regenerated each new SPA instance. Not linked across instances (a hard refresh or new tab starts fresh).
- **Logged-in users** — a per-user pseudonym, derived from `user.id`. A contributor's journeys stitch together across instances via the pseudonym.

The vendor only ever sees the pseudonym, never `user.id` or any other identity field. The pseudonym is **derived, not stored**.

**Literal (the HMAC construction is the joinability contract; changing inputs or hash breaks the privacy guarantee):**

```python
def pseudonym_for(user_id: int) -> str:
    return hmac.new(
        settings.ANALYTICS_PSEUDONYM_KEY.encode(),
        str(user_id).encode(),
        hashlib.sha256,
    ).hexdigest()
```

`ANALYTICS_PSEUDONYM_KEY` lives in environment configuration, never in the database. There is no `AnalyticsIdentity` table and no FK keyed on the pseudonym — vendor data cannot be joined to the `User` table by any SQL query against our application database. Recovering the link requires both a database copy **and** the secret key.

This is what makes the "decouples analytics data from the authoritative user table" requirement in [Analytics.md](Analytics.md#identifiability) true: the decoupling is absence of a join, not indirection through another table.

### Salt rotation

Rotating `ANALYTICS_PSEUDONYM_KEY` orphans every previously-attributed event under its old pseudonym. Aggregate counts at the vendor survive rotation; the user→pseudonym link does not. This is the mechanism behind the "retention proportional to identifiability" principle in [Privacy.md](../../Privacy.md#retention) — raw events can be retained indefinitely because the link to a user account is bounded by the rotation cadence.

### Opt-out

A user opting out triggers a vendor delete-by-id API call for their current pseudonym; nothing in our database needs to change. If they later opt back in, the same `user.id` and key produce the same pseudonym, but the prior history is gone.

### Anonymous visitors

Not assigned a pseudonym. The vendor adapter is configured to store its `distinct_id` only in the JS heap, with no cookie or storage (see [Privacy Requirements](#privacy-requirements)). When the document is replaced, the id is gone.

### Anonymous-to-logged-in linking

When `identify(pseudonym)` runs after login within the same SPA instance, vendor SDKs typically alias the in-heap anonymous `distinct_id` to the pseudonym — so the minutes of pre-login browsing in that instance get retroactively attributed to the user's account. We accept this: the user has just consented to authenticated use, and the linkage is bounded to one SPA instance (anonymous history from previous instances is unreachable, because anonymous ids are heap-only). Provider-specific knobs for suppressing aliasing, if needed, live in [Provider Binding](#provider-binding-posthog).

## Privacy Requirements

The vendor integration must satisfy these constraints. The concrete knobs that implement them are in [Provider Binding](#provider-binding-posthog). Reviewers reject any adapter change that loosens them.

**No persistent client-side identity:**

- No cookies set by analytics
- No localStorage or sessionStorage entries
- `distinct_id` is heap-bound only; SPA navigations stay linked via the JS heap

**No fingerprinting-grade properties:**

- No screen or viewport dimensions
- No autocapture / implicit click / form tracking
- No session recording
- No surveys, heatmaps, or feature-flag-based behavioral cohorts

**No IP-based attribution:**

- Client IP stripped at ingest
- Server-side geoip disabled

**Pageviews are explicit, not auto-captured.** The vendor's auto-pageview is off; pageviews fire from a SvelteKit `afterNavigate` hook so every CSR route change is recorded — not just the initial SSR load. Implementation in [AnalyticsFrontendPlan.md § Phase 2](AnalyticsFrontendPlan.md#phase-2-pageviews).

Mapping to the [non-goals](Analytics.md#non-goals):

| Non-goal                  | Enforcement                                                                                 |
| ------------------------- | ------------------------------------------------------------------------------------------- |
| Cookies                   | persistence is heap-only; no cookies, no storage                                            |
| Behavioral fingerprinting | autocapture disabled, session recording disabled, screen and viewport properties denylisted |
| Cross-site tracking       | the chosen vendor is a first-party analytics tool, not a cross-property tracking network    |
| IP-based profiling        | IP stripped at ingest, server-side geoip disabled                                           |
| Engagement-addiction      | surveys disabled, feature-flag SDK unused                                                   |

## Events

Specific events have not yet been designed. This section specifies the _patterns_ events must follow once they exist; the canonical list is the typed registry in code (`events.ts` / `events.py`), not a separate doc.

### Where Events Originate

Events are emitted from the side that has the truth. The origin is determined by where the signal is observable, not by where it's most convenient to fire it from:

- **Client-side** when the signal lives only in the browser: CSR navigation (pageviews), UI lifecycle moments (edit-flow start/abandon), and actions that execute client-side (search if performed in the browser).
- **Server-side** when the signal is the outcome of a mutation or a transactional moment: post-write confirmations (edit saved, upload completed) and signup-time events. These must fire from inside the transaction to reflect the actual mutation, not from the UI hoping it succeeded.

Server-side events flow through the Python adapter using the pseudonym attached to the request by middleware. Server-side events require an authenticated user; there are no anonymous server-side events.

### Naming

- Format: `noun_past-tense-verb`, lowercase. Examples: `edit_saved`, `photo_uploaded`, `search_performed`.
- Object-first so related events group alphabetically.
- Past tense because events are facts about something that has happened.

Avoid:

- **vague names**: `user_event`, `signal_emitted`, `transaction_committed` — say nothing useful about what the user did.
- **vendor-specific naming**: `posthog_capture`, `mp_track` — couples the taxonomy to the current provider.
- **internal implementation details**: `useEffect_fired` — describes code mechanics, not user behavior.

### Each event must earn its keep

Each event must answer a specific product question. If you can't name the question, don't add the event. The intentional-not-just-in-case philosophy ([Analytics.md § Product Analytics](Analytics.md#product-analytics)) is the bulwark against engagement-addiction drift.

### Typed registry

The event registry is the single source of truth for event names and property shapes. Each side has its own registry covering only the events it emits — the frontend and backend registries are disjoint (see [Where Events Originate](#where-events-originate)). Both exist so `analytics.capture()` calls are type-checked and properties never devolve to `dict[str, Any]`.

**Pseudocode (shows the registry shape; specific events are illustrative candidates pending design):**

```ts
// events.ts — frontend-emitted events
type EventRegistry = {
  search_performed: {
    query_length: number;
    results_count: number;
    logged_in: boolean;
  };
  // ... grows as events are added
};
```

**Pseudocode (shows the TypedDict shape; specific events are illustrative candidates pending design):**

```python
# events.py — server-emitted events
class EditSaved(TypedDict):
    page_type: PageType
    duration_seconds: int
    is_first_edit: bool


# ... grows as events are added
```

Per the project's [strong-typing rule](../../Python.md), backend properties are TypedDicts, not `dict[str, Any]`. Adding a property to an event without updating the registry is a type error on both sides.

## Provider Binding: PostHog

[PostHog Cloud](https://posthog.com/) is the current provider. Rationale and vendor comparison live in [AnalyticsVendors.md](AnalyticsVendors.md).

PostHog ships several features that appear in our [non-goals](Analytics.md#non-goals): autocapture, session replay, heatmaps, surveys, behavioral cohorts. The init config below disables them at the integration boundary.

### Adapter files

- Frontend: `frontend/src/lib/analytics/posthog.ts` + `config.ts`
- Backend: `backend/apps/analytics/posthog_adapter.py`

These are the only files that import `posthog-js` or the `posthog` Python package. The lint pins in [Module Layout](#module-layout) enforce that.

### Frontend init lockdown

**Literal (locked-down init; the integration test asserts every option):**

```ts
posthog.init(PUBLIC_POSTHOG_KEY, {
  api_host: "https://eu.posthog.com",
  persistence: "memory", // satisfies "no persistent client-side identity"
  autocapture: false, // satisfies "no autocapture / implicit tracking"
  capture_pageview: false, // we call pageview() explicitly from afterNavigate
  capture_pageleave: false,
  disable_session_recording: true,
  disable_surveys: true,
  disable_external_dependency_loading: true,
  ip: false, // satisfies "no IP-based attribution"
  property_denylist: [
    "$ip", // belt-and-suspenders alongside ip: false
    "$screen_height", // satisfies "no fingerprinting-grade properties"
    "$screen_width",
    "$viewport_height",
    "$viewport_width",
  ],
});
```

### Backend init lockdown

**Literal (locked-down init; the integration test asserts every line):**

```python
posthog.host = "https://eu.posthog.com"
posthog.disable_geoip = True  # satisfies "no IP-based attribution"
```

### Aliasing suppression knob

If we ever need to suppress PostHog's default anonymous-to-logged-in aliasing (see [Anonymous-to-logged-in linking](#anonymous-to-logged-in-linking)), pass `$anon_distinct_id: null` to `posthog.identify()`.

### Integration test

An integration test on each side asserts these options are wired up; weakening any of them fails the test. See [AnalyticsBackendPlan.md § Phase 1](AnalyticsBackendPlan.md#phase-1-skeleton) and [AnalyticsFrontendPlan.md § Phase 1](AnalyticsFrontendPlan.md#phase-1-skeleton).
