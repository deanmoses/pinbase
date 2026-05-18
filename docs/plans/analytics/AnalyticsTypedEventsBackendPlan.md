# Analytics Typed Events Backend Plan

This doc covers the backend side of the typed-events track of [AnalyticsPlan.md](AnalyticsPlan.md). Contracts live in [AnalyticsArchitecture.md](AnalyticsArchitecture.md).

Specific events have not yet been designed; the candidate event names below are illustrative until the taxonomy review pass happens.

## Phase: Skeleton

Stand up the `apps/analytics/` app with the module structure from [AnalyticsArchitecture.md § Module Layout](AnalyticsArchitecture.md#module-layout). No events fire yet.

**Deliverables:**

- `apps/analytics/__init__.py` — public API re-exporting `analytics.capture()` and `analytics.identify()`.
- `apps/analytics/pseudonym.py` — `pseudonym_for(user_id)` per the spec in [AnalyticsArchitecture.md § Identity & Pseudonymization](AnalyticsArchitecture.md#identity--pseudonymization).
- `apps/analytics/posthog_adapter.py` — implements the `Analytics` Protocol, applies the locked-down init (`posthog.host = "https://us.posthog.com"`, `posthog.disable_geoip = True`).
- `apps/analytics/noop.py` — no-op adapter for tests and dev.
- `apps/analytics/middleware.py` — derives the request user's pseudonym once and caches it on the request object. Anonymous requests get `None`.
- `apps/analytics/events.py` — empty `TypedDict` registry, ready to grow.
- `ANALYTICS_PSEUDONYM_KEY` wired through Django settings from `.env`. Document in `.env.example`.
- Ruff `flake8-tidy-imports` rule banning `import posthog` outside `posthog_adapter.py`.
- Middleware registered in `MIDDLEWARE` after auth.

**Verification:**

- A unit test for `pseudonym_for()` asserting determinism (same `user_id` + key → same output) and key-dependence (rotating the key changes the output).
- A unit test for middleware: authenticated request gets `request.analytics_pseudonym` set; anonymous gets `None`; middleware does not query the DB on anonymous requests.
- One integration test asserts the backend SDK's `posthog.host` and `posthog.disable_geoip` are set as specified. Weakening either fails this test.

## Phase: first transactional event

The first event to land is a server-side transactional event. Signup conversion is the obvious candidate (must fire from inside the signup transaction, low volume, easy to verify the pseudonym round-trips cleanly without volume noise) — illustrative name: `account_registered`. The specific event, name, and properties get decided during taxonomy review.

**Deliverables:**

- A `TypedDict` for the event in `events.py`.
- A `capture()` call from the relevant view, using `pseudonym=pseudonym_for(user.id)` for events that fire before middleware has run (e.g. the signup view, which creates the user).
- The new user's pseudonym added to the page payload that the SPA hydrates from. This is the field the frontend will eventually consume from `analytics.identify()` (see [AnalyticsPlan.md § Handoff](AnalyticsPlan.md#handoff-backend--frontend)).

**Verification:**

- A test that runs the real flow and asserts (with `RecordingAnalytics`) that exactly one event was captured, with the expected properties and the pseudonym for the newly-created user.
- A staging/PostHog spot-check: trigger the flow, find the event in PostHog, inspect it. Confirm no `$ip`, no geoip-derived city/country, no `User.email` or `User.id`, only the pseudonym.
- A SQL check on production-like data: `SELECT * FROM auth_user JOIN <anything> ON pseudonym` returns no rows because no such table or FK exists.

## Phase: first post-write event

A second event, post-write, that fires inside a normal request cycle (not at signup). Purpose: prove the middleware-cached pseudonym is reused across multiple events in the same authenticated session, not re-derived. Illustrative candidate: `edit_saved`.

**Deliverables:**

- A `TypedDict` for the event in `events.py`.
- A `capture()` call from the relevant view, using `pseudonym=request.analytics_pseudonym` (the middleware-attached value, not re-derived inline).

**Verification:**

- A test that performs the action and asserts the event is captured with the expected properties.
- A test that performs two of the action in the same authenticated session and asserts both events use the same pseudonym — proves the middleware cache is doing its job, not just luck of two HMACs agreeing.

## Phase: Remaining events

Land additional server-side events as the relevant feature code is touched. Illustrative candidates include upload-completion and moderation events, but the actual list comes from the taxonomy review.

**Verification:**

- Per-event test asserting the event is captured with the expected properties.

## Test patterns

Backend tests use the no-op adapter swapped for a recording adapter as a fixture:

```python
@pytest.fixture
def recording_analytics(settings):
    settings.ANALYTICS_ADAPTER = "apps.analytics.testing.RecordingAnalytics"
    yield apps.analytics.adapter
```

Assertions go against `recording_analytics.events`, a list of `(event_name, properties, pseudonym)` tuples. Per the project's [strong-typing rule](../../Python.md), `events` is typed — not `list[Any]`.

The PostHog adapter itself is never exercised in unit tests. The one integration test that loads it asserts the locked-down init config and nothing else.

## What this doc does NOT cover

- The pseudonym mechanism, privacy lockdown, abstraction contract, naming conventions — those are architecture, see [AnalyticsArchitecture.md](AnalyticsArchitecture.md).
- Frontend work — see [AnalyticsTypedEventsFrontendPlan.md](AnalyticsTypedEventsFrontendPlan.md).
- SDK setup and pageviews — see [AnalyticsUntypedEventsPlan.md](AnalyticsUntypedEventsPlan.md).
- DB-derived stats — see [AnalyticsDbStatsPlan.md](AnalyticsDbStatsPlan.md).
- Cross-cutting sequencing — see [AnalyticsPlan.md](AnalyticsPlan.md).
