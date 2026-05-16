# Analytics Backend Plan

Also see:

- [AnalyticsPlan.md](AnalyticsPlan.md) — orchestration and phase ordering
- [AnalyticsArchitecture.md](AnalyticsArchitecture.md) — contracts (pseudonymization, privacy lockdown, abstraction interface)
- [AnalyticsFrontendPlan.md](AnalyticsFrontendPlan.md)
- [AnalyticsEventTaxonomy.md](AnalyticsEventTaxonomy.md)

This doc covers backend implementation phase by phase. Contracts live in the architecture doc; event names and properties live in the taxonomy. This doc is _how_ to land them.

## Phase 1: Skeleton

Stand up the `apps/analytics/` app with the module structure from [AnalyticsArchitecture.md § Module Layout](AnalyticsArchitecture.md#module-layout). No events fire yet.

**Deliverables:**

- `apps/analytics/__init__.py` — public API re-exporting `analytics.capture()` and `analytics.identify()`.
- `apps/analytics/pseudonym.py` — `pseudonym_for(user_id)` per the spec in [AnalyticsArchitecture.md § Identity & Pseudonymization](AnalyticsArchitecture.md#identity--pseudonymization).
- `apps/analytics/posthog_adapter.py` — implements the `Analytics` Protocol, applies the locked-down init (`posthog.host = "https://eu.posthog.com"`, `posthog.disable_geoip = True`).
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

## Phase 2: account_registered

First end-to-end event. Server-only by necessity — fires inside the signup transaction.

**Deliverables:**

- `AccountRegistered` `TypedDict` in `events.py`. Properties per [AnalyticsEventTaxonomy.md § account_registered](AnalyticsEventTaxonomy.md#account_registered).
- Signup view calls `analytics.capture("account_registered", AccountRegistered(referral_source=..., invite_source=...), pseudonym=pseudonym_for(user.id))`.
- The new user's pseudonym is added to the page payload that the SPA hydrates from. This is the field the frontend will eventually consume from `analytics.identify()`. (See [AnalyticsPlan.md § Handoff](AnalyticsPlan.md#handoff-backend--frontend).)

**Verification:**

- A test that signs up a user via the real signup flow and asserts (with `RecordingAnalytics`) that exactly one `account_registered` event was captured, with the expected properties and the pseudonym for the newly-created user.
- A staging/PostHog spot-check: sign up, find the event in PostHog, inspect it. Confirm no `$ip`, no geoip-derived city/country, no `User.email` or `User.id`, only the pseudonym.
- A SQL check on production-like data: `SELECT * FROM auth_user JOIN <anything> ON pseudonym` returns no rows because no such table or FK exists.

## Phase 3: edit_saved

Second event. Validates the middleware-cached pseudonym story across multiple events in the same authenticated session.

**Deliverables:**

- `EditSaved` `TypedDict` in `events.py`. Properties per [AnalyticsEventTaxonomy.md § edit_saved](AnalyticsEventTaxonomy.md#edit_saved).
- The edit-save view path calls `analytics.capture("edit_saved", EditSaved(...), pseudonym=request.analytics_pseudonym)`.
- All call sites use the middleware-attached pseudonym, not `pseudonym_for(request.user.id)` re-derived inline.

**Verification:**

- A test that performs a save and asserts the event is captured with the expected properties.
- A test that performs two saves in the same authenticated session and asserts both events use the same pseudonym (proves the middleware cache is doing its job, not just luck of two HMACs agreeing).

## Phase 4: Remaining server events

Land the rest of the server-side taxonomy as the relevant feature code is touched.

**Deliverables:**

- `PhotoUploaded` `TypedDict` + capture call in the upload completion path. Properties per [AnalyticsEventTaxonomy.md § photo_uploaded](AnalyticsEventTaxonomy.md#photo_uploaded).
- `ModerationAction` `TypedDict` + capture call in moderation action handlers. Properties per [AnalyticsEventTaxonomy.md § moderation_action](AnalyticsEventTaxonomy.md#moderation_action).

These aren't urgent — they ship as those code paths get touched. No hurry to backfill before the frontend lands.

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

- The pseudonym mechanism, privacy lockdown, abstraction contract — those are architecture, see [AnalyticsArchitecture.md](AnalyticsArchitecture.md).
- Event names and property schemas — see [AnalyticsEventTaxonomy.md](AnalyticsEventTaxonomy.md).
- Frontend work — see [AnalyticsFrontendPlan.md](AnalyticsFrontendPlan.md).
- Cross-cutting sequencing and handoffs — see [AnalyticsPlan.md](AnalyticsPlan.md).
