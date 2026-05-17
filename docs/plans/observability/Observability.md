# Observability

Also see:

- [ObservabilityVendors.md](ObservabilityVendors.md)
- [ObservabilityArchitecture.md](ObservabilityArchitecture.md)
- [ObservabilityPlan.md](ObservabilityPlan.md)

## Purpose

Observability in this project will initially support one narrow job:

1. Knowing when **production is broken** before a user has to explain it to us.

That means detecting real user-impacting failures, alerting the maintainers, and preserving enough diagnostic context to debug the problem without asking the user to reproduce it from memory.

## Audiences

- **Maintainers** — the [small team](../../SmallTeam.md) running the project. Primary consumers of alerts, errors, uptime checks, and operational diagnostics.
- **Contributors** — not direct consumers of raw observability data. They benefit from reliability improvements and may see curated status or incident information if we create that later.
- **Visitors** — not direct consumers of raw observability data.

No public raw telemetry. No third-party data sharing beyond the operational vendor(s) needed to run the monitoring system.

## Capabilities

### Error Monitoring

Capture production exceptions that indicate the application is failing unexpectedly.

Examples:

- unhandled backend exceptions
- unhandled frontend (browser-side) exceptions
- repeated HTTP 500 responses
- deploys that introduce a new production error
- unexpected failures in critical product flows such as signup, login callbacks, catalog editing, media upload, or claim writes

The goal is not "capture everything." The goal is to capture failures that a maintainer would plausibly need to investigate.

Frontend errors are in scope from day one. The setup cost (sourcemap upload during deploy, an ignore list for extension and third-party noise) doesn't shrink with user count, and silent client-side failures in the editing UI are exactly the failure mode that direct reporting misses — a contributor hits a broken save, sees nothing useful, and leaves without telling anyone.

### Alerting

Alert maintainers when production has an actionable problem.

Alert-worthy events:

- a new production exception appears
- a previously resolved production exception regresses
- production starts returning repeated 500s
- the deployed app is unavailable
- a critical user flow has a sustained failure pattern

Non-alert-worthy events:

- every warning log
- every denied permission
- normal 404s
- bot and scanner traffic
- validation errors
- expected auth failures
- expected rate-limit denials
- routine background noise that does not indicate user-impacting breakage

Alerting has failed if maintainers learn to ignore it. Low noise is a hard requirement, not a tuning preference.

### Recipients

Production alerts go for now to both founders as co-responders — either may pick up an alert; neither is solely on the hook. Each recipient is routed individually, may use a different destination, and may have different channel preferences (e.g. one on email, one on chat). The specific destinations and channels are implementation detail and may change over time; the charter-level requirement is only that the vendor support per-recipient routing and that adding or removing a maintainer be a low-friction administrative change.

### Uptime Monitoring

Detect whether the production site is reachable and responding.

Minimum useful signal:

- the public site answers a simple request
- the app is not returning a persistent 5xx
- failures notify maintainers

This is intentionally shallow. Flow-level synthetic checks (signup, login callback, media upload, catalog edit, claim write) are out of scope initially. A synthetic check earns its cost only when basic uptime won't catch the failure **and** error monitoring won't catch it either **and** the detection-window benefit outweighs the maintenance burden (test data pollution, auth scaffolding, false-positive triage). At this project's traffic level, most user-facing failures will be loud 5xx responses surfaced by error monitoring, and a real user will hit them within hours; a synthetic mostly buys a few hours of lead time at the cost of permanent maintenance. See [Future Considerations](#future-considerations) for when to revisit.

### Debug Context

For an actionable production failure, maintainers should be able to answer:

- what exception occurred?
- which route, endpoint, or operation failed?
- which deployed commit or release was running?
- when did the failure start?
- did it affect one request, one user, or many users?
- was the request anonymous or authenticated?
- was the failure backend, SSR, or browser-side?
- what non-sensitive breadcrumbs led up to the failure?

This does not require collecting full request bodies, cookies, session tokens, or personal data by default.

### Release Correlation

Production failures should be tied to the deployed version.

At minimum, operational events should include the deploy's git SHA when the hosting environment provides one. This lets maintainers distinguish an old bug from a regression introduced by the latest deploy.

### Operational Logs

Logs remain useful for detailed investigation, but logs are not the alerting system by themselves.

Expected log use:

- follow-up investigation after an alert
- reconstructing operational context around a failure
- reviewing non-incident signals such as authz denials, rate limits, or suspicious activity

Logs should not become a dashboard that someone must manually inspect every day.

## Constraints

### Privacy

Privacy-respectful by default; see [Privacy.md](../../Privacy.md) for the project's overall stance.

Operational telemetry must follow the same data-minimization principle as analytics: collect the smallest amount of data necessary to diagnose legitimate operational problems.

Avoid collecting:

- cookies
- session identifiers
- CSRF tokens
- access tokens or API keys
- WorkOS secrets or raw auth payloads
- full request bodies by default
- passwords or auth form fields
- uploaded file contents
- keystrokes
- generalized session replay
- behavioral profiles
- cross-site identifiers

Potentially acceptable when needed for debugging:

- route or endpoint name
- HTTP method and status
- exception type and stack trace
- release SHA
- environment name
- user id and username for authenticated requests (usernames are public on this project)
- anonymous/authenticated state
- coarse request metadata such as user agent family

Email addresses, IP addresses, and raw request bodies require a specific justification. They should not be enabled by default merely because a vendor can collect them.

### Operational

- **Low maintenance**. Maintainable by a [small team](../../SmallTeam.md) of volunteer developers.
- **Managed/hosted service**. We do not want to operate an observability stack ourselves.
- **Easy handoff**. A new maintainer should be able to understand where alerts go, how to access incidents, and what to do next.
- **Shared ownership**. Alerting and monitoring access must not depend on one person's private account.
- **Low noise**. Alert volume must stay small enough that alerts retain meaning.
- **Production-focused**. Local development and CI should not pollute production signal.
- **Budget**. Ideally free. Up to $10/mo for the first 12 months.
- **Geography**. Prefer near Virginia to be near web servers. See [Hosting.md#geography](../../Hosting.md#geography).

### Security

Operational telemetry is sensitive because it can contain stack traces, route names, deployment metadata, and user-linked debugging context.

Requirements:

- access limited to maintainers who need it
- no public raw telemetry
- no secrets in captured events
- scrubbing for headers, cookies, auth payloads, and sensitive form fields
- clear offboarding path when a maintainer leaves

## Non-Goals

We intentionally avoid, at least initially:

- building a general metrics platform
- self-hosting logs, traces, or dashboards
- OpenTelemetry as a project-wide abstraction
- distributed tracing across every request
- JSON-log migration as a prerequisite
- alerting on every warning or structured denial
- session replay as a default-on feature
- frontend behavior recording for analytics purposes
- business-intelligence dashboards
- daily manual log review
- "just in case" telemetry

## Relationship to Analytics

Observability is **not** [Analytics](../analytics/Analytics.md).

Analytics answers product questions:

- what are users trying to find?
- where do contributors get stuck?
- which content is popular or missing?
- how is the preservation effort progressing?

Observability answers operational questions:

- is production broken?
- what failed?
- when did it start?
- which deploy caused it?
- what context is needed to fix it?

The two systems may both observe events such as upload failures or signup failures, but they use the data differently. Analytics should measure workflow friction in aggregate. Observability should alert on unexpected operational breakage.

Do not use observability tooling as a backdoor analytics system.

## Relationship to Authz and Abuse Signals

Authorization denials, rate-limit hits, and suspicious traffic are useful operational signals, but most are not incidents.

Expected treatment:

- normal auth failures are not alerts
- expected permission denials are not alerts
- validation errors are not alerts
- bot 404s are not alerts
- unexpected exceptions inside authz enforcement are alerts
- sudden sustained spikes may be reviewable, but should not wake anyone by default

Authz telemetry should help maintainers understand whether policy changes are causing friction or abuse controls are firing unexpectedly. It should not create a noisy pseudo-security-alert system before the project has people to operate one.

## Future Considerations

### Flow-level synthetic checks

Add a synthetic for a specific flow only in response to an incident that uptime and error monitoring missed. Silent-failure modes — a 200 that hides a broken state, an upload that "succeeds" but can't be retrieved, an OAuth callback that completes into a malformed session — are the cases that justify the cost. Loud failures don't. Likeliest first candidates if traffic grows or storage proves flaky: WorkOS login callback, media upload roundtrip.
