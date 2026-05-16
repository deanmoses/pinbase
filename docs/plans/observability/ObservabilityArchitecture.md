# Observability Architecture

Also see:

- [Observability.md](Observability.md)
- [ObservabilityVendors.md](ObservabilityVendors.md)

## Provider

We chose [Sentry](https://sentry.io) as the observability provider. Uptime monitoring also lives in Sentry; see [Uptime](#uptime) below.

Sentry ships several features that appear in our [non-goals](Observability.md#non-goals): session replay, profiling, full-request performance tracing, and the user-feedback widget. These are disabled at the SDK init boundary, not "left at defaults and trusted." Privacy and noise discipline are configured in code, not assumed from the vendor.

The Sentry org has two projects:

- `flipcommons-backend` (platform: Python/Django)
- `flipcommons-frontend` (platform: JavaScript/SvelteKit)

Two projects instead of one, because Python and JS stack traces group cleanly when separated and per-project alert routing lets us tune signal independently.

## Scope

What we capture:

- unhandled exceptions on the backend (caught by Sentry's Django integration)
- unhandled exceptions on the frontend in SSR and browser (caught by `handleErrorWithSentry`)
- explicit `Sentry.capture_exception(exc)` for swallowed-but-noteworthy cases

What we don't capture:

- validation errors (`ValidationError`, Ninja schema rejects)
- expected 401/403 from authz enforcement
- expected 404s, including bot/scanner traffic
- rate-limit denials
- WorkOS callback states that resolve to a user-facing error page
- `IntegrityError`s used as control flow (e.g. unique-constraint races)

Scrubbing happens in `before_send` (see [Privacy enforcement](#privacy-enforcement)), not at every call site. The "don't capture" list above is the intent; the hook is what enforces it for the unhandled-exception path.

## Backend integration

Package: `sentry-sdk[django]`. Init in `config/settings.py`, gated on `SENTRY_DSN`:

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

SENTRY_DSN = env.str("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment="production",
        release=env.str("GIT_SHA", default=""),
        send_default_pii=False,
        traces_sample_rate=0.0,
        profiles_sample_rate=0.0,
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=None),
        ],
        before_send=scrub_event,
    )
```

User identification is set in a middleware that runs after `AuthenticationMiddleware`. Authenticated requests attach `{id, username}` to the Sentry scope; anonymous requests attach nothing. Usernames are public on this project (see [Privacy.md](../../Privacy.md)) so including them in events is acceptable; emails and IP addresses are not.

Init runs once per process. The empty-DSN guard is the master switch for [Environment separation](#environment-separation) — local, CI, and test runs leave `SENTRY_DSN` unset and the init block is a no-op.

## Frontend integration

Package: `@sentry/sveltekit`. The adapter ships the right defaults for SvelteKit's split SSR/browser model; we use it rather than raw `@sentry/browser` so the framework integration stays on the doc-blessed path.

Three init sites:

- `frontend/src/hooks.server.ts` — `Sentry.init({...})` plus `handleErrorWithSentry` exported as `handleError`
- `frontend/src/hooks.client.ts` — same pair, for browser errors
- `frontend/vite.config.ts` — the `sentrySvelteKit` plugin for sourcemap upload (see [Releases & sourcemaps](#releases--sourcemaps))

Both `Sentry.init` calls use the same shape as the backend: `environment="production"`, `release` from the `PUBLIC_GIT_SHA` build-time env var, `tracesSampleRate: 0`, replay disabled, profiling disabled, feedback widget disabled. `beforeSend` mirrors the backend scrubber.

Browser-side `ignoreErrors` covers the standard noise floor: `ResizeObserver loop limit exceeded`, network errors from extensions, `Non-Error promise rejection captured`, and similar. The list lives next to the init call so a new maintainer can find it.

User identification on the frontend follows the same rule: id + username for authenticated, nothing for anonymous. Set via `Sentry.setUser(...)` in the auth layout's load function.

## Releases & sourcemaps

`@sentry/vite-plugin` (wrapped by `@sentry/sveltekit`'s `sentrySvelteKit` helper) handles sourcemap upload at build time. The pipeline:

1. Vite emits sourcemaps as part of the production build.
2. The plugin uploads them to Sentry, tagged with the release name from `GIT_SHA`.
3. The plugin deletes the sourcemap files from the build output, so they never ship to browsers.
4. Sentry resolves browser stack traces against the uploaded maps at issue time.

Required env at build time:

- `SENTRY_AUTH_TOKEN` — org-scoped, Railway secret
- `SENTRY_ORG` and `SENTRY_PROJECT` — set in `vite.config.ts`
- `GIT_SHA` — same value used by the Django init, so the same release name appears on both projects

The release tag is the contract: an event with `release=abc123` from `flipcommons-backend` and an event with `release=abc123` from `flipcommons-frontend` are the same deploy. This is what makes "did the latest deploy cause this?" answerable in one click.

## Environment separation

Sentry initializes **only when `SENTRY_DSN` is set**. The init block is the master switch:

- production → `SENTRY_DSN` set in Railway → init runs → events flow
- local dev → no DSN → init no-ops → no events
- CI / pytest → no DSN → init no-ops → no events
- a maintainer testing SDK changes locally → opts in by setting `SENTRY_DSN` themselves; events tagged `environment="production"` would mix with real prod, so use a separate Sentry project or a `development` environment tag if you do this

`environment="production"` is hardcoded today. If staging or preview environments are ever introduced, this becomes `env.str("SENTRY_ENVIRONMENT", default="production")` and the value is set per Railway environment.

## Privacy enforcement

Scrubbing happens in `before_send` (Python) and `beforeSend` (JS). The hooks run on every event regardless of where it originated, so there's one chokepoint rather than per-call-site discipline.

Always stripped:

- `Cookie` and `Set-Cookie` headers
- `Authorization` header
- `X-CSRFToken` header and `csrfmiddlewaretoken` form field
- `password`, `password_confirm`, and any field whose name contains `token`, `secret`, or `key`
- request body by default (drop unless the request has been explicitly safe-listed)
- email addresses appearing in `extra` or `contexts`
- IP addresses (`request.env.REMOTE_ADDR`, `user.ip_address`)

Allowed through (per [Observability.md §Privacy](Observability.md#privacy)):

- route or endpoint name
- HTTP method and status code
- exception type, message, stack trace
- release SHA, environment, deploy timestamp
- user id and username, for authenticated requests
- anonymous/authenticated state
- coarse User-Agent family (browser, OS, bot/not-bot)

The scrubber is conservative on purpose: anything not on the allow list above gets dropped. Adding a new field requires a deliberate code change, not an SDK setting flip.

## Logging integration

Sentry's Python SDK auto-enables `LoggingIntegration`. We configure it as:

```python
LoggingIntegration(level=logging.INFO, event_level=None)
```

This means:

- log records at `INFO` and above attach as **breadcrumbs** on real events (diagnostic context for whatever exception comes next)
- log records **never become standalone Sentry events**, regardless of level

The decoupling is deliberate. Application code keeps calling `logger.info/warning/error(...)` as today, and those lines continue to flow to stdout where Railway collects them for investigation. They do not page anyone. If a maintainer wants a log line to alert, they call `Sentry.capture_exception(exc)` or `Sentry.capture_message("...", level="error")` explicitly — the discipline is "if you want it in Sentry, say so in code." This keeps the charter's [non-alert list](Observability.md#alerting) (authz denials, validation errors, rate-limit hits, expected auth failures) out of the alert stream by construction.

## Alerting

Per-recipient routing is configured in Sentry's UI. Each founder is a member of the org with their own notification destination (email or chat, per their preference). Adding or removing a maintainer is a single membership change in the org settings.

Alert rules (configured per project):

- **new issue** → alert all maintainers
- **regression of a resolved issue** → alert all maintainers
- **uptime check failure** (on `flipcommons-backend` project, owned by the Sentry Uptime monitor) → alert all maintainers
- **spike in an existing issue** → alert all maintainers (threshold: 10× the 24h baseline)

Non-alerting activity (assignment changes, comments, resolution events) stays in-product.

Default issue assignment: **unassigned**. Either founder may grab an issue. We chose this over auto-assigning both because diffusion-of-responsibility hasn't been a real failure mode at this team size, and double-paging both founders for every event creates noise. Revisit if anything falls through the cracks.

## Uptime

Single Sentry Uptime monitor against `/__health` on a 5-minute interval. The endpoint already exists ([frontend/src/routes/\_\_health/+server.ts](../../../frontend/src/routes/__health/+server.ts)) and proxies to the Django `/api/health` ([backend/config/api.py:56-60](../../../backend/config/api.py#L56-L60)), which performs a `SELECT 1`. A successful response proves Caddy + SvelteKit SSR + Django + DB are all alive in one ping.

Keep `/__health` shallow. `SELECT 1` is the right depth: deep enough to catch a dead app server or DB, shallow enough not to false-positive on transient external blips. Do **not** grow it into a per-subsystem dependency check (R2 reachability, Redis ping, external API liveness) — those failures should surface as errors when product code hits them, not as uptime flapping.

If the homepage monitor ever proves insufficient or Sentry Uptime hits a quota limit, swap in a free [UptimeRobot](ObservabilityVendors.md#uptimerobot) check. See [ObservabilityVendors.md §Uptime](ObservabilityVendors.md#uptime-also-sentry) for the decision context.

## Access & offboarding

- The Sentry org is owned at the project level, not by a personal account.
- Both founders are org members with admin-equivalent permissions.
- A new maintainer is added by inviting their email to the org and granting whatever role lets them resolve issues and configure their own notification destination.
- An outgoing maintainer is removed by revoking org membership. Their per-recipient routing destination vanishes with them; no separate cleanup needed.
- Org-level SSO via GitHub is enabled when Sentry's tier supports it, so maintainer offboarding piggybacks on revoking their GitHub access to the project.

## First-event verification

Two staff-gated routes, one per side, that exist to trigger a Sentry event on demand:

- **Backend** — `/api/__sentry_test` (Django Ninja, `tags=["private"]`, gated by `@requires(Activity.X)` where the activity is staff-only). Raises an exception when hit.
- **Frontend** — `/__sentry_test` (SvelteKit route, SSR guard checks `locals.user?.is_staff`). The page contains two buttons: one that calls the backend route, one that `throw`s in a client-side handler. Covers both SSR and browser-side capture paths.

Use after any of: initial Sentry setup, SDK upgrade, sourcemap-plugin config change, alert-rule edit, environment-variable change. Hit both routes from a staff account, then confirm in the Sentry UI within 30 seconds:

- the event appears in the expected project
- the `release` tag matches the deployed `GIT_SHA`
- frontend stack traces resolve to TypeScript source (not minified JS)
- alerts route to the configured recipients

Keeping the routes permanent rather than one-shot scripts means verification is a 30-second sanity check after every deploy that touches observability — the part of the system most likely to silently rot.
