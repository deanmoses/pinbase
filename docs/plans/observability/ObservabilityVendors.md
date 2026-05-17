# Observability Vendors

Also see:

- [Observability.md](Observability.md)
- [ObservabilityArchitecture.md](ObservabilityArchitecture.md)

## Background

Comparison of candidate vendors against the requirements in [Observability.md](Observability.md): managed/hosted, low maintenance for a [small team](../../SmallTeam.md), shared ownership, low-noise alerting with per-recipient routing, cheap or free at our [traffic level](../GrowthProjections.md), reasonable US geography, privacy-respecting defaults.

Observability has two distinct sub-problems:

- **error monitoring** - with sourcemaps, breadcrumbs, release correlation
- **uptime monitoring** - does the site answer?

Error monitoring is the primary decision. Uptime is a secondary axis: it only catches the disjoint set of failures the error reporter can't (total outage, bad deploys that fail to boot, cert/DNS issues, hosting outages) and the bar for "good enough" is low — a free external ping every few minutes. If the chosen error vendor includes serviceable uptime, use it; otherwise slot in a free specialist (e.g. UptimeRobot) as set-and-forget. Don't pick the error vendor based on its uptime feature.

## Decision: Sentry

1. **First-class Django and SvelteKit SDKs.** Both frameworks document Sentry as a first-citizen integration. Setup is one of the most-trodden paths in web tooling.
2. **Free tier covers the realistic year-one error volume.** 5k errors/month is comfortable when the site itself only does 2.5k → 400k _pageviews_/month. You'd need a runaway loop to overflow it.
3. **Maximally boring and well-documented.** Per [SmallTeam.md](../../SmallTeam.md), the criterion is "what a part-time volunteer can keep running a year from now." Sentry is the closest thing to a default in the industry — any new maintainer has either used it or can find a tutorial in 60 seconds.
4. **Privacy posture is configurable to match the doc.** Sourcemap pipeline, scrubbing rules, sample rates, session replay off — all standard SDK options.
5. **Shared ownership works out of the box.** Org-level accounts, per-recipient alert routing, role-based access, no single-person dependency.
6. **Uptime can ride along.** Sentry Uptime is good enough for the charter's [intentionally shallow](Observability.md#uptime-monitoring) bar; see [Uptime](#uptime-also-sentry) below.

The realistic alternatives and why they lose:

- **[BetterStack](#betterstack)** — cleanest bundled-everything UI; loses on maturity and price.
- **[GlitchTip](#glitchtip)** — "Sentry but cheaper," but Sentry is already free at this scale, so the savings are hypothetical and you trade ecosystem and longevity for them.
- **[Honeybadger](#honeybadger)** — lovely, but no free tier; $26/mo is a permanent line item.
- **[Rollbar](#rollbar) / [Bugsnag](#bugsnag)** — fine, but Sentry strictly dominates on SDK quality and community.

Confidence is high. The only reason to revisit is if Sentry's frontend SDK conflicts with [Privacy.md](../../Privacy.md) in some specific way during architecture — and even then, the more likely outcome is "configure it off" rather than "switch vendors."

## Free-tier quota

Sentry's free tier covers ~5k errors/month and retains events for 30 days. The [year-one projection](#sentry) is comfortably inside that, but a runaway loop on a single endpoint could burn it. If quota is exceeded, Sentry drops events rather than billing — the failure mode is "we go blind," not "surprise charge." Watch the org-level usage page monthly; cross the cliff only with a deliberate upgrade to the $26/mo Team plan, not by accident.

## Access & offboarding

- The Sentry org is owned at the project level, not by a personal account.
- Both founders are org members with admin-equivalent permissions.
- A new maintainer is added by inviting their email to the org and granting whatever role lets them resolve issues and configure their own notification destination.
- An outgoing maintainer is removed by revoking org membership. Their per-recipient routing destination vanishes with them; no separate cleanup needed.
- Org-enforced SSO is a paid-tier Sentry feature. Until we're on a tier that supports it, offboarding means a manual membership revoke — there's no GitHub-access shortcut.

## Uptime: also Sentry

Use Sentry Uptime. A single monitor against the public homepage on a 5-minute interval clears the charter's [intentionally shallow](Observability.md#uptime-monitoring) bar: the site answers, the app isn't returning a persistent 5xx, failures notify maintainers.

Reusing the error vendor rather than adding a second one wins on operational simplicity:

- one org account, one login, one offboarding step when a maintainer leaves
- per-recipient alert routing configured for errors works unchanged for uptime
- release correlation comes for free — an outage right after a deploy is already tagged with the SHA that shipped
- uptime failures land in the same issue stream as exceptions, so there's one place to look during an incident

The one real argument against this — a Sentry outage masking a simultaneous site outage — is a third-order risk at this project's traffic level. If it ever bites, or if we exceed Sentry's free uptime quota by needing a second monitor (e.g. a backend healthcheck), slot in a free [UptimeRobot](#uptimerobot) check next to Sentry. It's a 10-minute change and nothing else depends on which vendor answers the ping.

## Vendor Table

| Vendor                        | Uptime | Error | Reason rejected                                |
| ----------------------------- | ------ | ----- | ---------------------------------------------- |
| [Sentry](#sentry)             | basic  | ✅    |                                                |
| [GlitchTip](#glitchtip)       | ❌     | ✅    | Sentry's better for us                         |
| [BetterStack](#betterstack)   | ✅     | ✅    | Sentry's better for us                         |
| [Honeybadger](#honeybadger)   | ✅     | ✅    | Sentry's better for us                         |
| [Rollbar](#rollbar)           | ❌     | ✅    | Sentry's better for us                         |
| [Bugsnag](#bugsnag)           | ❌     | ✅    | Sentry's better for us                         |
| [AppSignal](#appsignal)       | ✅     | ✅    |                                                |
| [Highlight.io](#highlightio)  | ❌     | ✅    | Session replay is a non-goal                   |
| [PostHog](#posthog)           | ❌     | ✅    | Conflates analytics and observability          |
| [Grafana](#grafana)           | ✅     | basic | Exceeds maintenance appetite                   |
| [HyperDX](#hyperdx)           | ❌     | ✅    | OpenTelemetry and session replay are non-goals |
| [UptimeRobot](#uptimerobot)   | ✅     | ❌    |                                                |
| [Cronitor](#cronitor)         | ✅     | ❌    |                                                |
| [Healthchecks](#healthchecks) | ❌     | ❌    | Cron/heartbeat only                            |
| [Checkly](#checkly)           | ✅     | ❌    | Synthetic flows deferred initially             |
| [Site24x7](#site24x7)         | ✅     | ❌    |                                                |
| [StatusCake](#statuscake)     | ✅     | ❌    |                                                |
| [Datadog](#datadog)           | ✅     | ✅    | Enterprise cost, overkill                      |
| [New Relic](#new-relic)       | ✅     | ✅    | Enterprise cost, overkill                      |
| [Django](#django)             | ❌     | basic | Null baseline that any vendor must beat        |

## Vendors

### Sentry

Industry-standard error monitoring. First-class Django and SvelteKit SDKs, mature sourcemap pipeline, release tagging via git SHA, per-issue assignment and alert rules. Has bolted-on uptime monitoring (Sentry Crons / Uptime) but it's not the headline product. Free tier covers ~5k errors/month and limited replays; team plan jumps to $26/mo when free tier is exceeded.

Coverage: errors (backend + frontend), uptime (basic), some performance.

### GlitchTip

Open-source Sentry-protocol-compatible service. Uses the Sentry SDKs unchanged, but hosted by GlitchTip's team (or self-hosted, which we've ruled out). Cheaper than Sentry at low volumes; smaller feature set. Smaller company, less long-term certainty.

Coverage: errors (backend + frontend). No uptime.

### BetterStack

Bundled observability: errors, logs, uptime, status pages, on-call rotation, incident management. The "one vendor for the whole observability surface" play. Generous free tiers across all products; paid plans start cheap. Heartbeat/cron monitoring included. UI is opinionated and clean.

Coverage: errors, logs, uptime, status page, incident response.

Reason rejected: Sentry's error SDK is more mature for the specific frameworks we use (Django, SvelteKit) — BetterStack's error product is a newer bolt-on alongside their original logs/uptime focus, with less SDK maturity, less ecosystem depth (docs, Stack Overflow, LLM training data), and less battle-tested sourcemap tooling. Sentry's free error tier is also more generous (~5k events/mo vs. BetterStack's tighter error tier). The bundled extras BetterStack offers over Sentry — managed logs, status pages, on-call rotation — are explicit non-goals in [Observability.md](Observability.md), so we'd be paying (in attention if not money) for products we won't use.

### Honeybadger

Small-team-focused error monitoring with uptime checks and cron monitoring included. Calm, indie company; pricing is per-project rather than per-event-volume. No free tier — starts at $26/mo for the smallest paid plan. Strong reputation for low-noise alerting and quality support.

Coverage: errors (backend + frontend), uptime, cron.

### Rollbar

Long-time Sentry competitor. Strong free tier (5k events/month). Slightly heavier UI, less momentum than Sentry, but mature SDKs and stable feature set.

Coverage: errors (backend + frontend). No uptime.

### Bugsnag

Mature Sentry/Rollbar-class error monitoring product. Strong fit for backend and frontend exception triage, with the usual grouping, release, and alerting workflow. Free tier exists for solo/passion projects; paid event tiers start above what we likely need near launch. No meaningful uptime story, so it would need to be paired with UptimeRobot, Cronitor, Site24x7, or similar.

Coverage: errors (backend + frontend), some performance. No uptime.

### AppSignal

Developer-friendly APM bundle covering errors, performance, host monitoring, uptime monitoring, check-ins, metrics, and logs. Supports Python/Django and JavaScript, and is more integrated than a pure error inbox. Pricing is predictable but over the initial target budget after the trial: roughly $23/mo when billed annually for the smallest application-monitoring plan. Worth knowing about, but probably not a finalist for the first year unless we decide an all-in-one APM product is worth paying for.

Coverage: errors, performance, uptime, check-ins, logs, host metrics.

### Highlight.io

Newer, open-core, bundles errors + session replay + logs + traces. Session replay is a non-goal for us; we'd need to confirm it can be fully disabled. Free tier exists but tighter than Sentry's.

Coverage: errors, session replay (unwanted), logs, traces.

### PostHog

PostHog now includes error tracking with sourcemap support, logs, product analytics, feature flags, session replay, and other product tooling. The free tier is unusually generous for our scale, and PostHog Cloud offers a US Virginia region, which matches our geography preference. The downside is conceptual and privacy-related: PostHog is primarily a product analytics platform, and this plan explicitly keeps observability separate from analytics. If considered, it should be configured narrowly for error tracking/logs only, with session replay and behavioral analytics disabled unless separately approved.

Coverage: errors, logs, product analytics, session replay, feature flags. Uptime would need a separate vendor.

### Grafana

Grafana Cloud

Fully managed Grafana/Loki/Tempo/Mimir platform with logs, metrics, traces, frontend observability, synthetic checks, dashboards, alerting, and incident response. The free tier is much more substantial than most enterprise observability products. The tradeoff is operational complexity: Grafana Cloud is a platform for people who want to model observability data, not a calm small-team error inbox. It is worth listing as a capable free/cheap platform, but it likely exceeds the maintenance appetite unless we already want logs/metrics/dashboards.

Coverage: logs, metrics, traces, frontend observability, synthetic checks, alerting, incident response. Error monitoring is less productized than Sentry-style tools.

### HyperDX

Open-source/full-stack observability product built around OpenTelemetry, ClickHouse, logs, traces, metrics, errors, and session replay. Attractive if we wanted a Datadog-like debugging surface without Datadog pricing. For this project, it has the same concern as Highlight.io: session replay and broad request tracing are more telemetry than we want initially, and OpenTelemetry is explicitly a non-goal for day-one observability.

Coverage: errors, logs, traces, metrics, session replay. Uptime is not the main use case.

### UptimeRobot

Specialist uptime monitor. Free tier covers 50 monitors at 5-minute intervals. Email/SMS/webhook alerting. Pair with a separate error-monitoring vendor.

Coverage: uptime only.

### Cronitor

Specialist for cron, heartbeat, website, and API monitoring. Free tier is enough for a tiny project, and paid pricing is per monitor/user rather than an enterprise platform bundle. More useful than UptimeRobot if background jobs or scheduled ingestion checks become operationally important; otherwise it is another uptime-check option.

Coverage: uptime, API monitoring, cron/heartbeat monitoring, status pages.

### Healthchecks

Focused cron and heartbeat monitoring. Free hosted tier covers enough jobs for small projects, and the paid supporter tier is cheap. It does not replace uptime or error monitoring, but it is a good fit if we add production jobs whose silent failure matters, such as scheduled ingest, backups, or periodic media maintenance.

Coverage: cron/heartbeat monitoring only.

### Checkly

Developer-focused uptime and synthetic monitoring with API checks and Playwright browser checks. Has a useful free tier, and it would be a strong candidate if we later add flow-level synthetic checks. For the initial plan, synthetic flows are explicitly deferred because they add permanent maintenance cost and test-data problems.

Coverage: uptime, API checks, browser synthetic checks, status pages.

### Site24x7

UptimeRobot-class alternative for basic website availability checks. Site24x7 has a budget-compatible website-monitoring plan with 1-minute polling and multiple users. This would be a candidate to pair with a separate error-monitoring vendor, not replacements for one.

Coverage: uptime and related website monitoring. No error monitoring.

### StatusCake

UptimeRobot-class alternative for basic website availability checks. StatusCake has a simple free tier with 5-minute uptime checks. This would be a candidate to pair with a separate error-monitoring vendor, not replacements for one.

Coverage: uptime and related website monitoring. No error monitoring.

### Datadog

Enterprise APM platform. Has a free tier, but the free tier is a sales funnel — features and quotas push aggressively toward paid plans that start in the hundreds-of-dollars-per-month range. Almost certainly overkill and over-budget for this project; included here to be dismissed explicitly.

Coverage: everything, expensively.

### New Relic

Enterprise APM platform. Has a free tier, but the free tier is a sales funnel — features and quotas push aggressively toward paid plans that start in the hundreds-of-dollars-per-month range. Almost certainly overkill and over-budget for this project; included here to be dismissed explicitly.

Coverage: everything, expensively.

### Django

Railway built-in + Django logging

Null option: rely on Railway's deploy logs and a minimal Django email-on-exception handler, plus a free UptimeRobot check. No external error-monitoring vendor at all. Cheapest possible setup; loses sourcemap-resolved frontend errors, breadcrumb context, deduplication, release correlation, and per-recipient routing. Listed as the baseline that any chosen vendor must beat.

Coverage: backend logs and 5xx emails only.
