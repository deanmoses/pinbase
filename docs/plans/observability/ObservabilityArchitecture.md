# Observability Architecture

Also see:

- [Observability.md](Observability.md) — purpose, audiences, goals
- [ObservabilityVendors.md](ObservabilityVendors.md) — vendor evaluation
- [ObservabilityPlan.md](ObservabilityPlan.md) — detailed plan

## System shape

Three in-process SDKs feed events to our [§ observability vendor](#observability-vendor) through a single scrubber per runtime; alerts fan out to per-maintainer destinations.

Dataflow for a single error:

```text
exception (Django | SSR | browser)
   │
   ▼
SDK in-process
   │
   ▼
pre-send hook  ──── drops or scrubs ────▶ /dev/null
   │
   ▼
observability vendor (backend + frontend streams)
   │
   ▼
alert rules ──▶ per-maintainer destination (email/chat)
```

Components:

- **Backend** (Django) — vendor SDK in-process; scrubber in a dedicated module.
- **SSR** (SvelteKit Node) — vendor SDK in-process; scrubber inline in `hooks.server.ts`.
- **Browser** — vendor SDK shipped to client; scrubber inline in `hooks.client.ts`.
- **Build pipeline** — uploads sourcemaps at build time and tags releases by `RAILWAY_GIT_COMMIT_SHA`. Sourcemaps are upload-only artifacts: deleted from the build output so they don't ship to browsers.
- **[Observability vendor](#observability-vendor)** — backend and frontend events are kept in separate streams so Python and JS stack traces group cleanly and per-stream alert routing lets us tune signal independently.
- **Uptime monitor** — hits `/__health` every 5 minutes. Detail in [§ Uptime](#uptime).
- **Alert routing** — per-maintainer destinations. Detail in [§ Alerting](#alerting).

Trust boundaries:

- The pre-send hooks are the only place code we control sees raw event data before it leaves the process. Anything crossing into the vendor has been through scrubbing. Detail in [§ Privacy enforcement](#privacy-enforcement).
- User id and username cross to the vendor (usernames are public on this project per [Privacy.md](../../Privacy.md)); email and IP do not.
- Sourcemaps are upload-only build artifacts and never ship to browsers.

## Design decisions

### Scrubbing is a single chokepoint per runtime

The SDK's pre-send hook runs on every event regardless of origin, so privacy enforcement is one hook to audit rather than N call sites to trust. Application code never has to remember to scrub. The chokepoint also makes the [§ Capture scope](#capture-scope) "don't capture" list enforceable: drops happen in the hook, not at the point of `raise`.

The Python and JS hooks are kept in sync by code review, not a shared module — the two SDKs have different event shapes, so a shared abstraction would be more code than the divergence costs.

### Logs and error events are decoupled

Application logging (`logger.info/warning/error`) flows to stdout, collected by Railway. It never becomes an alert-emitting event. To page someone, code must call the SDK's explicit capture API — the contract is "if you want it in the observability vendor, say so." This keeps Observability.md's [non-alert list](Observability.md#alerting) (authz denials, validation errors, rate-limit hits) out of the alert stream by construction, not by allowlist. Detail in [§ Logging](#logging).

### DSN presence is the master environment switch

SDK init runs only when the ingestion-endpoint env var (DSN) is non-empty. Local, CI, and test runs leave it unset and the init block is a no-op. There is no per-environment config matrix, no runtime kill switch, no "disabled in dev" branch — just one variable, and the same guard applies to both runtimes. Detail in [§ Environment separation](#environment-separation).

### Vendor defaults are disabled at init

The SDK ships several features that appear in our [non-goals](Observability.md#non-goals): session replay, profiling, full-request performance tracing, and a user-feedback widget. These are explicitly disabled at the SDK init boundary. Privacy and noise discipline are configured in code where they show up in review, not assumed from the vendor.

## Capture scope

What we capture:

- unhandled exceptions on the backend (framework integration)
- unhandled exceptions on the frontend in SSR and browser
- explicit capture calls for swallowed-but-noteworthy cases

What we don't capture:

- validation errors (`ValidationError`, Ninja schema rejects)
- expected 401/403 from authz enforcement (see [Authz.md](../../Authz.md))
- expected 404s, including bot/scanner traffic
- rate-limit denials
- WorkOS callback states that resolve to a user-facing error page
- `IntegrityError`s used as control flow (e.g. unique-constraint races)

The "don't capture" list is enforced by the pre-send hook for the unhandled-exception path; see [§ Privacy enforcement](#privacy-enforcement).

## Privacy enforcement

Scrubbing runs in the SDK's pre-send hook on every runtime. The Python implementation lives in a dedicated scrubber module; the JS implementations live next to each init call. (Exact files in [§ Vendor binding](#vendor-binding).)

Stripped before send:

- `Cookie` and `Set-Cookie` headers
- `Authorization` header
- `X-CSRFToken` header and `csrfmiddlewaretoken` form field
- `password`, `password_confirm`, and any field whose name contains `token`, `secret`, or `key`
- request body by default (drop unless the request has been explicitly safe-listed)
- email addresses appearing in `extra` or `contexts`
- IP addresses (`request.env.REMOTE_ADDR`, `user.ip_address`)

Kept (per [Observability.md §Privacy](Observability.md#privacy)):

- route or endpoint name
- HTTP method and status code
- exception type, message, stack trace
- release SHA, environment, deploy timestamp
- user id and username, for authenticated requests
- anonymous/authenticated state
- coarse User-Agent family (browser, OS, bot/not-bot)

The scrubber prefers strictness: when in doubt, drop. The "kept" list is the intent; the implementation is a deny list applied to the SDK's default event shape rather than a literal allow-list rebuild, because reconstructing every nested context dict ourselves is more code than the privacy gain justifies.

## Environment separation

SDK init runs **only when the DSN is set**. The init block is the master switch:

- production → DSN set in Railway → init runs → events flow
- local dev → no DSN → init no-ops → no events
- CI / pytest → no DSN → init no-ops → no events
- a maintainer testing SDK changes locally → opts in by setting the DSN themselves; events tagged `environment="production"` would mix with real prod, so use a separate vendor project or a `development` environment tag if you do this

`environment="production"` is hardcoded today. If staging or preview environments are ever introduced, this becomes env-var-driven and set per Railway environment.

Disabling observability in production requires removing the DSN and redeploying — there is no runtime kill switch. If the vendor is itself down or rate-limiting us, the SDK queues and drops events internally without crashing the app, so we accept the temporary blindness.

## Alerting

Per-recipient routing is configured in the vendor's UI. Each founder is a member of the org with their own notification destination (email or chat, per their preference). Adding or removing a maintainer is a single membership change — see [ObservabilityVendors.md § Access & offboarding](ObservabilityVendors.md#access--offboarding).

Alert rules (configured per project, mirrored across both):

- **new issue** → alert all maintainers
- **regression of a resolved issue** → alert all maintainers
- **uptime check failure** → alert all maintainers (the project the uptime monitor is attached to doesn't affect routing — all maintainers get pinged either way)
- **spike in an existing issue** → alert all maintainers, threshold to be tuned from production data after launch

Non-alerting activity (assignment changes, comments, resolution events) stays in-product.

Default issue assignment: **unassigned**. Either founder may grab an issue. We chose this over auto-assigning both because diffusion-of-responsibility hasn't been a real failure mode at this team size, and double-paging both founders for every event creates noise. Revisit if anything falls through the cracks.

## Uptime

Single uptime monitor against `/__health` on a 5-minute interval. The endpoint already exists ([frontend/src/routes/\_\_health/+server.ts](../../../frontend/src/routes/__health/+server.ts)) and proxies to the Django `/api/health` ([backend/config/api.py:56-60](../../../backend/config/api.py#L56-L60)), which performs a `SELECT 1`. A successful response proves Caddy + SvelteKit SSR + Django + DB are all alive in one ping.

Keep `/__health` shallow. `SELECT 1` is the right depth: deep enough to catch a dead app server or DB, shallow enough not to false-positive on transient external blips. Do **not** grow it into a per-subsystem dependency check (R2 reachability, Redis ping, external API liveness) — those failures should surface as errors when product code hits them, not as uptime flapping.

The monitor is hosted alongside the [observability vendor](#observability-vendor) for operational simplicity — one org, one login, one offboarding step, shared alert routing. See [§ Vendor binding](#vendor-binding) for the fallback if the vendor's free uptime quota is exceeded.

## First-event verification

Two staff-gated routes, one per side, that exist to trigger an event on demand. Both gate on a new `Activity.OBSERVABILITY_DEBUG`, registered with predicates `is_authenticated, is_staff` — operator-area activities are an established pattern in [rules.py](../../../backend/apps/core/authz/rules.py) (`DJANGO_ADMIN_ACCESS`, `RATE_LIMIT_EXEMPT`), and using a dedicated Activity for this gate keeps the route inventory complete and the frontend gate consistent with the rest of the SPA.

- **Backend** — `/api/sentry_test` (Django Ninja, `tags=["private"]`), decorated `@requires(Activity.OBSERVABILITY_DEBUG)`. Raises an exception when hit.
- **Frontend** — `/_sentry_test` (SvelteKit route). The `+page.ts` load function calls `requireCapability({ fetch, url, activity: Activity.OBSERVABILITY_DEBUG })`, matching the existing pattern in [require-capability.ts](../../../frontend/src/lib/require-capability.ts) — non-staff visitors are redirected to `/login` or `/verify-email` like any other gated route. The page contains two buttons: one that calls the backend route, one that `throw`s in a client-side handler. Covers both SSR-load-time and browser-side capture paths.

The frontend gate is UX-only per [project convention](../../../CLAUDE.md) (the SPA auth check is advisory; the backend is the source of truth) — the backend `@requires` is what actually keeps non-staff out.

Use after any of: initial vendor setup, SDK upgrade, sourcemap-plugin config change, alert-rule edit, environment-variable change. Hit both routes from a staff account, then confirm in the vendor UI within 30 seconds:

- the event appears in the expected project
- the `release` tag matches the deployed `RAILWAY_GIT_COMMIT_SHA`
- frontend stack traces resolve to TypeScript source (not minified JS)
- alerts route to the configured recipients

## Observability vendor

The chosen vendor is **Sentry** — see [ObservabilityVendors.md](ObservabilityVendors.md) for the choice rationale and rejected alternatives.

## Vendor binding

Everything in this section is the concrete binding between the architecture above and the Sentry SDK. If we ever swapped vendors, the sections above stay; this section gets rewritten.

### Projects

Two projects in the Sentry org, one per runtime:

- `flipcommons-backend` — Python/Django
- `flipcommons-frontend` — JavaScript/SvelteKit

### Backend init contract

Package: `sentry-sdk[django]`. Init in `config/settings.py`, gated on `SENTRY_DSN`:

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment="production",
        release=os.environ.get("RAILWAY_GIT_COMMIT_SHA", "").strip(),
        send_default_pii=False,
        traces_sample_rate=0.0,
        profiles_sample_rate=0.0,
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=None),
        ],
        before_send=scrub_event,  # implemented in config/sentry_scrubber.py
    )
```

User identification is set in a middleware that runs after `AuthenticationMiddleware`. Authenticated requests attach `{id, username}` to the Sentry scope; anonymous requests attach nothing.

### Logging

`LoggingIntegration(level=logging.INFO, event_level=None)` means:

- log records at `INFO` and above attach as **breadcrumbs** on real events (diagnostic context for whatever exception comes next)
- log records **never become standalone Sentry events**, regardless of level

This is the implementation of the [Logs and error events are decoupled](#logs-and-error-events-are-decoupled) design decision.

### Frontend init contract

Package: `@sentry/sveltekit`. The adapter ships the right defaults for SvelteKit's split SSR/browser model; we use it rather than raw `@sentry/browser` so the framework integration stays on the doc-blessed path.

Three init sites:

- `frontend/src/hooks.server.ts` — `Sentry.init({...})` plus `handleErrorWithSentry` exported as `handleError`
- `frontend/src/hooks.client.ts` — same pair, for browser errors
- `frontend/vite.config.ts` — the `sentrySvelteKit` plugin for sourcemap upload (see [§ Releases & sourcemaps](#releases--sourcemaps))

Both `Sentry.init` calls use the same shape as the backend: `environment="production"`, `tracesSampleRate: 0`, replay disabled, feedback widget disabled. `beforeSend` mirrors the backend scrubber.

The SSR side reads `RAILWAY_GIT_COMMIT_SHA` from `process.env` at runtime; the browser side gets it baked in at build time as `PUBLIC_RAILWAY_GIT_COMMIT_SHA`, since runtime env doesn't reach the client bundle.

Browser-side `ignoreErrors` covers the standard noise floor: `ResizeObserver loop limit exceeded`, network errors from extensions, `Non-Error promise rejection captured`, and similar. The list lives next to the init call so a new maintainer can find it.

User identification on the frontend follows the same rule: id + username for authenticated, nothing for anonymous. Set via `Sentry.setUser(...)` in the auth layout's load function.

### Releases & sourcemaps

`@sentry/vite-plugin` (wrapped by `@sentry/sveltekit`'s `sentrySvelteKit` helper) handles sourcemap upload at build time:

1. Vite emits sourcemaps as part of the production build.
2. The plugin uploads them to Sentry, tagged with the release name from `RAILWAY_GIT_COMMIT_SHA`.
3. The plugin deletes the sourcemap files from the build output via `sourcemaps.filesToDeleteAfterUpload`, so they don't ship to browsers. This is configured explicitly; the plugin doesn't delete by default.
4. Sentry resolves browser stack traces against the uploaded maps at issue time.

Required env at build time:

- `SENTRY_AUTH_TOKEN` — org-scoped, Railway secret. This is the only Sentry value that is actually a secret; `SENTRY_DSN` is a public key (it ends up in the frontend bundle by design).
- `SENTRY_ORG` and `SENTRY_PROJECT` — set in `vite.config.ts`, pointing at `flipcommons-frontend`.
- `RAILWAY_GIT_COMMIT_SHA` — already wired through the Docker build (`ARG RAILWAY_GIT_COMMIT_SHA` in [Dockerfile](../../../Dockerfile)) and into [`svelte.config.js`](../../../frontend/svelte.config.js); the same value is used for the backend Sentry init at runtime, so events from both projects share a release name.

### Uptime monitor

Sentry Uptime hosts the `/__health` monitor described in [§ Uptime](#uptime). Hosting it inside Sentry rather than adding a second vendor means one org, one login, one offboarding step, and uptime failures land in the same issue stream as exceptions. If Sentry's free uptime quota is ever exceeded, slot in a free [UptimeRobot](ObservabilityVendors.md#uptimerobot) check next to it — nothing else depends on which vendor answers the ping.
