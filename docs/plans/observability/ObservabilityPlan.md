# Observability Rollout Plan

Also see:

- [Observability.md](Observability.md)
- [ObservabilityArchitecture.md](ObservabilityArchitecture.md)

## Phases

- ✅ DONE: [Prerequisites](#prerequisites) — Sentry & Railway config
- ✅ DONE: [ObservabilityBackendPlan.md](ObservabilityBackendPlan.md) — notify about server exceptions
- ✅ DONE: [ObservabilityFrontendPlan.md](ObservabilityFrontendPlan.md) — notify about browser & SSR exceptions
- [Alert rules](#alert-rules) — actually send alerts to us
- ─────────── minimum viable product ───────────
- [Uptime monitor](#uptime-monitor) - periodically ping a health check endpoint
- [Tune browser `ignoreErrors`](#tune-browser-ignoreerrors) — pulled in the first time noise appears

## Prerequisites

Done in Sentry and Railway dashboards before either the backend or frontend deploys; no PRs.

- Sentry org created; `flipcommons-backend` and `flipcommons-frontend` projects exist.
- Both founders invited as org members with per-recipient notification routing configured.
- Railway production env vars set: `SENTRY_DSN` (backend project DSN), `PUBLIC_SENTRY_DSN` (frontend project DSN), `SENTRY_AUTH_TOKEN` (org-scoped, secret), `SENTRY_ORG`, `SENTRY_PROJECT=flipcommons-frontend`.
- Local, CI, and test environments leave all of the above unset — the empty-DSN guard in [ObservabilityArchitecture.md § Environment separation](ObservabilityArchitecture.md#environment-separation) is the master switch.
- **Advanced Data Scrubbing** rules added on each project (Project Settings → Security & Privacy → Advanced Data Scrubbing):
  - `[Mask] [@email] from [$string]`
  - `[Mask] [@ip] from [$string]`
  - `[Remove] [$request.query_string]`

  These are part of the privacy contract — without them, emails / IPs interpolated into log messages, or query-string contents, would be stored. See [ObservabilityArchitecture.md § Privacy enforcement](ObservabilityArchitecture.md#privacy-enforcement) for the full layering.

## Alert rules

Done in the Sentry dashboard after both code PRs are deployed.

- Alert rules created in both projects: new issue, regression of resolved issue. Spike-in-existing-issue is deferred until there's production data to tune the threshold against (per [ObservabilityArchitecture.md § Alerting](ObservabilityArchitecture.md#alerting)).
- Default issue assignment left as **unassigned** in both projects.

## Uptime monitor

- Sentry uptime monitor attached to `flipcommons-frontend`, hitting `/__health` on a 5-minute interval. The endpoint already exists; the architecture rationale is in [ObservabilityArchitecture.md § Uptime](ObservabilityArchitecture.md#uptime).
- Uptime-check-failure alert routed to both founders.

## Tune browser ignoreErrors

Tune the browser ignoreErrors list against the actual noise observed, not against a generic recipe.

Pull this in the first time noise appears in `flipcommons-frontend` — extension errors, `ResizeObserver loop limit exceeded`, `Non-Error promise rejection captured`, etc.
