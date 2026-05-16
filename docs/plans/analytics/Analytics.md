# Analytics

Also see:

- [AnalyticsArchitecture.md](AnalyticsArchitecture.md)
- [AnalyticsVendors.md](AnalyticsVendors.md)
- [AnalyticsPlan.md](AnalyticsPlan.md) — phased rollout
- [PublicDashboards.md](PublicDashboards.md)

## Purpose

Analytics in this project should support two narrow jobs:

1. Understanding **who visits the site and how they got here**, so we can grow reach and improve discovery.
2. Understanding **how contributors use the product**, so we can fix friction and prioritize improvements.

A third downstream surface — [public dashboards](PublicDashboards.md) — reuses the same data to celebrate preservation work and coordinate community effort.

## Audiences

- **Maintainers** — the [small team](../../SmallTeam.md) running the project. Primary consumers of all analytics.
- **Contributors** — community members, via [public dashboards](PublicDashboards.md). Consumers of curated aggregates only, never raw events.
- **Visitors** — the public, via the same dashboards.

No internal access tier above "maintainer"; no third-party data sharing.

## Capabilities

### Visitor Traffic Analytics

Aggregate, mostly-anonymous web traffic data.

- pageviews
- referral sources (search engines, social, direct, inbound links)
- popular content
- aggregate discovery trends

**Reach is measured by volume, not unique-person counts.** "Monthly Unique Visitors" is an ad-industry framing — useful for selling impressions, not for measuring whether a preservation database is serving its audience. Counting distinct people requires persistent identifiers and conflicts with the [privacy posture](#privacy) below. We read reach from pageview volume, referrer diversity, and (on the product side) search query diversity.

### Product Analytics

Event-based data about how authenticated and anonymous users interact with product surfaces. Three rough groupings:

- **Reading** — search success and failure, what content gets found, what doesn't.
- **Contribution** — edit and upload flows, where contributors drop off, time-to-first-contribution.
- **Community** — onboarding paths, retention of contributors over time.

**Event scope is deliberately narrow.** Each event must answer a specific product question; if you can't name the question, don't add the event. The intentional-not-just-in-case philosophy is the bulwark against engagement-addiction analytics drift.

### Public Dashboards

Curated, aggregate-only views built on top of the above. See [PublicDashboards.md](PublicDashboards.md).

## Constraints

### Privacy

- Privacy-respectful by default; see [Privacy.md](../../Privacy.md) for the project's overall stance.
- No ad-tech, no behavioral fingerprinting, no cross-site tracking, no advertising profiles.
- Analytics sets no cookies. The only cookies on the site are functional (auth session, CSRF).

#### Identifiability

- **Visitor traffic** is anonymous. No persistent identifier.
- **Product analytics for logged-in users** are linked via a per-user pseudonym, not the user's identity record. This decouples analytics data from the authoritative user table.
- **Product analytics for anonymous visitors** are not linked across sessions. Anonymous search events are explicitly wanted — they tell us what content to add or improve.
- **Raw search queries are stored.** The "content gaps" use case is the point of search analytics.

#### Retention

Analytics data is retained indefinitely. The pseudonymization posture above is what makes long retention privacy-safe — the data isn't directly joinable to user accounts.

### Operational

- **Low maintenance**. Maintainable by a [small team](../../SmallTeam.md) of volunteer developers.
- **Managed/hosted service**. We do not want to operate an analytics service ourselves.
- **Cost ceiling**: no more than $10/month, ideally free while the project is small. Vendor pricing should be evaluated against the traffic and event volumes in [GrowthProjections.md](../GrowthProjections.md) — roughly 2.5k pageviews/month at launch, ramping toward 400k/month by Year 1.
- **Vendor-neutral integration**: code calls our own abstraction, not a vendor SDK directly. See [AnalyticsArchitecture.md](AnalyticsArchitecture.md).
- **Geography**. Near the Railway web servers which are in Virginia; the cross-country browser→server hop is async and invisible to users. See [Hosting.md#geography](../../Hosting.md#geography).

## Non-Goals

We intentionally avoid:

- ad-tech ecosystems and ad-supported analytics providers
- behavioral fingerprinting and cross-site tracking
- advertising profiles or audience segmentation for marketing
- engagement-addiction metrics, manipulative retention analytics, predictive behavioral scoring
- operational telemetry (see below) — different system, different retention, different access

### Non-goal: Observability / Operational Telemetry

Operational telemetry is a separate concern with different purposes, retention policies, and access controls. It is **not** part of analytics. Examples of operational telemetry:

- server logs
- performance metrics
- error tracking
- abuse detection
- security auditing

See [Observability.md](../observability/Observability.md).
