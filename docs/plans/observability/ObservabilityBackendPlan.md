# Observability Backend Plan

This doc covers backend implementation of [ObservabilityPlan.md](ObservabilityPlan.md). Contracts live in [ObservabilityArchitecture.md](ObservabilityArchitecture.md).

## Status: ✅ Implementd

Deployed to prod.

## Phase: SDK

Stand up the Sentry SDK in the Django process plus a staff-gated debug route so post-deploy verification is concrete and repeatable. Events flow for unhandled exceptions; no user attribution yet.

**Deliverables:**

- `sentry-sdk[django]` added to backend dependencies.
- `config/settings.py` initializes the SDK exactly per [ObservabilityArchitecture.md § Backend](ObservabilityArchitecture.md#backend), gated on a non-empty `SENTRY_DSN`. Init runs once per process. The init delegates privacy enforcement to Sentry's own layers: `send_default_pii=False`, `max_request_body_size="never"`, `EventScrubber(recursive=True)`. There is **no** `before_send` hook — pattern-shaped PII (emails, IPs) and `request.query_string` are dropped by server-side Advanced Data Scrubbing rules listed in [ObservabilityPlan.md § Prerequisites](ObservabilityPlan.md#prerequisites).
- `ignore_errors=IGNORE_ERRORS` enforces the [Capture scope](ObservabilityArchitecture.md#capture-scope) "don't capture" list (`ValidationError`, Ninja `ValidationError`, `PermissionDenied`, `Http404`, `StructuredApiError`). List lives in [`backend/config/sentry_options.py`](../../../backend/config/sentry_options.py) and is covered by `test_ignore_errors_drops_each_listed_class`.
- `auto_session_tracking=True` so release-health sessions flow and the dashboard surfaces crash-free request rate per release. Works without tracing enabled.
- `shutdown_timeout=5` so SIGTERM at Railway deploys gets a 5s flush window instead of the default 2s — reduces the chance that the exception that caused a crash doesn't make it out.
- `LoggingIntegration(level=logging.INFO, event_level=None)` is wired so log records become breadcrumbs but never standalone events (see [ObservabilityArchitecture.md § Logs and error events are decoupled](ObservabilityArchitecture.md#logs-and-error-events-are-decoupled)).
- `Activity.OBSERVABILITY_DEBUG` registered in [apps/core/authz/rules.py](../../../backend/apps/core/authz/rules.py) with predicates `is_authenticated, email_verified, is_staff`. Mirrors the existing `RATE_LIMIT_EXEMPT` pattern; `DJANGO_ADMIN_ACCESS` is the documented exception to the email-verified default ([ObservabilityArchitecture.md § First-event verification](ObservabilityArchitecture.md#first-event-verification) covers the reasoning).
- `/api/sentry_test` (Django Ninja, `tags=["private"]`, `auth=django_auth`), decorated `@requires(Activity.OBSERVABILITY_DEBUG)`, raises an exception when hit.
- `.env.example` documents `SENTRY_DSN` as unset for local/CI.

**Verification:**

- Unit test asserting that when `SENTRY_DSN` is unset, the SDK has no active client (`sentry_sdk.get_client().is_active()` is `False`). Weakening the guard fails this test.
- API test for `/api/sentry_test`: anonymous request → 401/403; non-staff authenticated → 403; staff → 500 with the exception captured. Assert via the `sentry_recording` fixture in `backend/conftest.py` that exactly one event was captured with the expected exception type.
- Manual post-deploy: hit `/api/sentry_test` from a staff account, confirm the event lands in `flipcommons-backend` tagged with the current `RAILWAY_GIT_COMMIT_SHA` and no PII, within 30 seconds.

## Phase: User attribution

Attach `{id, username}` to the Sentry scope for authenticated requests so events can be grouped by user.

**Deliverables:**

- `SentryScopeMiddleware` in [apps/core/middleware/sentry_scope.py](../../../backend/apps/core/middleware/sentry_scope.py), registered immediately after `AuthenticationMiddleware`. For authenticated requests, calls `sentry_sdk.set_user({"id": ..., "username": ...})`; for anonymous requests, no user is attached. No email, no IP — usernames are public on this project; the others are not (see [Privacy.md](../../Privacy.md)).
- The `{id, username}` keep-list is the **privacy chokepoint** for the user dict — there is no `before_send` scrubber to catch a refactor that adds `email` here. The middleware docstring and `test_authenticated_user_has_no_email_or_ip_in_scope` both flag this load-bearing role.
- Sets two tags on every request (anonymous included) so the issue stream is filterable on auth state and traffic source: `auth_state` (`"auth"` | `"anon"`) and `ua_family` (`"chrome"` | `"firefox"` | `"safari"` | `"edge"` | `"bot"` | `"other"` | `"unknown"`). UA-family is a coarse substring sniff, not a parser library — the goal is filterable bucketing, not version accuracy.
- Gated on `sentry_sdk.get_client().is_active()` so the calls don't pollute the in-process isolation scope when Sentry isn't initialized (dev / CI / tests).
- Relies on `DjangoIntegration`'s per-request scope isolation so user data from request N never leaks into request N+1; the anonymous-request test is the regression guard.

**Verification:**

- Unit tests cover: (a) authenticated request → scope carries exactly `{id, username}` plus `auth_state="auth"` and the right `ua_family`; (b) anonymous request → scope user unset, `auth_state="anon"`, `ua_family` set; (c) email/IP keep-list invariant pinned; (d) inactive-client no-op leaves user and tags untouched; (e) bot UA → `ua_family="bot"`; (f) missing UA → `ua_family="unknown"`.

## Test patterns

Shared Sentry test fixtures live in [`backend/conftest.py`](../../../backend/conftest.py):

- `sentry_active` — boots Sentry with an active no-op client for tests that gate on `get_client().is_active()`.
- `sentry_recording` — boots Sentry with a `SentryRecordingTransport` that captures every envelope; assert on `transport.events` to verify what would have been sent.

Both fixtures clear process-global Sentry scope state on setup and teardown — Sentry's scope survives SDK re-init, so without this reset earlier tests leak into later ones. New Sentry-touching tests should use these fixtures rather than reinvent the dance.

## What this doc does NOT cover

- The init shape, scope of capture, environment separation, privacy layering — those are architecture, see [ObservabilityArchitecture.md](ObservabilityArchitecture.md).
- Server-side Sentry dashboard rules (`@email`, `@ip`, `$request.query_string`) — see [ObservabilityPlan.md § Prerequisites](ObservabilityPlan.md#prerequisites).
- Frontend work — see [ObservabilityFrontendPlan.md](ObservabilityFrontendPlan.md).
