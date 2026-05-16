# Analytics Vendor Research

Also see:

- [Analytics.md](Analytics.md)
- [AnalyticsArchitecture.md](AnalyticsArchitecture.md)
- [EventTaxonomy.md](EventTaxonomy.md)
- [PublicDashboardIdeas.md](PublicDashboardIdeas.md)

## Status

**No vendor selected yet.** This document records the candidates and the evaluation against the requirements in [Analytics.md](Analytics.md).

## Open Questions

- **Public-dashboard read path** — do we query the vendor's API, or mirror aggregates into our own Postgres? Independent of vendor choice; affects dashboard freshness, vendor rate-limit exposure, and how much of the read path we own.

## Evaluation Criteria

Drawn from [Analytics.md](Analytics.md); not restated in full here.

- **Coverage**: visitor traffic, product events, or both
- **Cookieless** (no cookies, no localStorage persistence)
- **No ad-tech lineage** — provider and feature set not built for advertising
- **Pseudonymous user linkage** — can accept an opaque per-user id, not real identity
- **Anonymous events** — supports unidentified event capture (for search-gap analytics)
- **Raw query storage** — string event properties retained, not stripped or hashed
- **Cost** at 2.5k pageviews/mo launch, ramping to 400k/mo by Year 1 (ceiling $10/mo, free preferred)
- **Managed / hosted** — no self-hosting
- **Retention** — long retention without per-row fees
- **Geography** — ingest reachable from US/Virginia without painful latency
- **Maintenance fit** for a small volunteer team

## Comparison Matrix

| Vendor                        | Covers traffic | Covers events | Cookieless | Funnels        | Retention / cohorts | Cost at 2.5k pv | Cost at 400k pv           | Maintenance |
| ----------------------------- | -------------- | ------------- | ---------- | -------------- | ------------------- | --------------- | ------------------------- | ----------- |
| [PostHog](#posthog-cloud)     | ✅             | ✅            | ✅         | ✅             | ✅                  | free            | free (under 1M events/mo) | medium      |
| [Plausible](#plausible-cloud) | ✅             | ✅            | ✅         | ✅ (2–8 steps) | ❌                  | ~$9/mo          | ~$29/mo                   | low         |
| [Pirsch](#pirsch)             | ✅             | ✅            | ✅         | ✅ (Plus tier) | ❌                  | ~$6/mo          | ~$19/mo                   | low         |
| [Umami Cloud](#umami-cloud)   | ✅             | ✅            | ✅         | ✅             | ✅                  | free            | $20/mo (Pro)              | low         |
| [GoatCounter](#goatcounter)   | ✅             | ❌            | ✅         | ❌             | ❌                  | free            | free                      | trivial     |

## Shortlist

### PostHog Cloud

- **Coverage**: visitor traffic + product events in one tool
- **Cookieless**: yes, with `persistence: "memory"`
- **Ad-tech lineage**: none; product-analytics company, not ad-tech
- **Pseudonymous linkage**: yes, `identify(pseudonym)` is the intended API
- **Anonymous events**: yes
- **Raw queries**: yes, arbitrary string properties
- **Cost**: free tier covers 1M events/mo and 5k recordings/mo; product analytics alone stays free comfortably through Year 1 traffic
- **Hosting**: managed (US or EU region)
- **Retention**: 1 year on free tier, 7 years on paid
- **Geography**: US region available
- **Maintenance**: SDK is heavy; defaults must be locked down at init (autocapture, replay, surveys, heatmaps all default-on); a sloppy upgrade can re-enable non-goal features

**Case for**: only candidate that covers both traffic and events at $0 within our volume; flexible event schema; first-party SDKs for both JS and Python.

**Case against**: large surface area for a small team; product is culturally adjacent to growth/marketing tooling we don't want; lock-down config has to be maintained as the SDK evolves.

### Plausible Cloud

- **Coverage**: visitor traffic + custom events with funnel analysis (2–8 linear steps)
- **Cookieless**: yes, by design
- **Ad-tech lineage**: none
- **Pseudonymous linkage**: yes via custom event properties — attach a pseudonym field to each event and filter/group by it
- **Anonymous events**: yes
- **Raw queries**: custom event properties are supported but the UI is geared toward low-cardinality dimensions; raw search-query storage works as event payload
- **Funnels / retention**: funnels yes; retention and cohorts not on the roadmap (per [GH discussion #364](https://github.com/plausible/analytics/discussions/364))
- **Cost**: ~$9/mo for 10k pv, ~$19/mo for 100k pv, ~$59/mo for 1M pv → **breaks the $10 ceiling well before Year 1**
- **Hosting**: managed (EU)
- **Retention**: 5+ years
- **Geography**: EU only
- **Maintenance**: minimal; tiny script, simple dashboard

**Case for**: the reference privacy-first traffic tool; now covers the product-analytics middle ground (custom events, funnels, per-user properties); near-zero maintenance.

**Case against**: price scales past the ceiling; no retention/cohort analysis means questions like "what % of last month's first-time editors came back" can't be answered in-tool.

### Pirsch

- **Coverage**: visitor traffic + custom events; funnel analysis on the Plus tier
- **Cookieless**: yes
- **Ad-tech lineage**: none
- **Pseudonymous linkage**: custom event metadata supported as key/value pairs; the docs are ambiguous about arbitrary string properties vs numeric metrics — would need to verify before committing
- **Anonymous events**: yes
- **Raw queries**: custom event properties supported
- **Funnels / retention**: funnels yes (Plus only); retention not advertised
- **Cost**: Standard $6/mo (no funnels) for 100k pv; Plus $12/mo (with funnels) — **Plus exceeds the $10 ceiling on day one**, Standard fits but doesn't cover product analytics
- **Hosting**: managed (EU/Germany)
- **Retention**: indefinite on paid plans
- **Geography**: EU only
- **Maintenance**: minimal

**Case for**: cheaper than Plausible on the traffic-only Standard tier; same privacy posture.

**Case against**: the tier with funnels ($12/mo) is over the ceiling from day one; ambiguity about whether custom string properties are first-class makes pseudonym-keyed analysis a verify-before-committing risk; no retention/cohorts.

### Umami Cloud

- **Coverage**: visitor traffic + custom events + funnels + retention + cohort breakdowns — the most product-analytics-capable of the privacy-first set
- **Cookieless**: yes
- **Ad-tech lineage**: none
- **Pseudonymous linkage**: yes via custom event properties (`data-umami-event-*` or JS API), filterable/groupable in the Properties tab
- **Anonymous events**: yes
- **Raw queries**: custom event data supported as typed properties (strings/numbers/booleans)
- **Funnels / retention**: both yes; cohort breakdowns advertised as core features. Tier gating for these features on the Hobby plan not yet verified
- **Session replay**: yes since v3.1.0, but as a _separately-loaded_ `recorder.js` script — must be deliberately added to the page (see [docs](https://docs.umami.is/docs/replays)). Not in the main tracker, not toggled by an SDK flag
- **Auto-collection on by default**: the main tracker auto-collects pageviews (including screen dimensions — a fingerprinting concern flagged in [AnalyticsArchitecture.md](AnalyticsArchitecture.md#privacy-enforcement)). Disabled with `data-auto-track="false"` on the script tag (see [tracker functions](https://docs.umami.is/docs/tracker-functions)). Real but smaller surface than PostHog's autocapture
- **Cost**: Hobby tier $0/mo (100K events/mo, 3 websites, 6-month retention, community support); Pro $20/mo (1M events/mo) → free covers launch; Pro is over the $10 ceiling but bounded
- **Hosting**: managed (US)
- **Retention**: 6 months on Hobby, longer on Pro
- **Geography**: US-hosted
- **Maintenance**: minimal

**Case for**: Hobby tier covers ~80K pageviews/mo + product events for free; US-hosted (matches the stated geography preference); covers the same product-analytics surface area as PostHog for our use cases (funnels + retention + custom properties); main tracker doesn't ship the features we don't want — only replay is available, and only as a deliberately-added second script.

**Case against**: Pro tier at $20/mo doubles the cost ceiling at Year 1 scale; 6-month free-tier retention is shorter than PostHog's 1 year; funnel/retention/cohort tier gating on Hobby still needs verification.

### GoatCounter

- **Coverage**: visitor traffic only; minimal custom event support
- **Cookieless**: yes
- **Ad-tech lineage**: none; explicitly anti-ad-tech, single-developer project
- **Pseudonymous linkage**: no
- **Anonymous events**: limited
- **Raw queries**: not really — designed for pageview counts
- **Cost**: **free for non-commercial use**; donations welcomed
- **Hosting**: managed (EU); also open-source if we ever wanted to self-host
- **Retention**: indefinite
- **Geography**: EU only
- **Maintenance**: trivial

**Case for**: aligns most closely with the [non-goals](Analytics.md#non-goals) — there is literally no engagement-addiction surface area; free; values-aligned.

**Case against**: doesn't cover product analytics at all; would need a second system for events; future-of-project risk (single maintainer).

## Dismissed

- **Cloudflare Web Analytics** — Cloudflare is vetoed at the project level (see [media hosting decision](../../../README.md)). Free and otherwise a strong fit.
- **Fathom Analytics** — same shape as Plausible; entry price ~$15/mo, above the ceiling from day one.
- **Matomo Cloud** — covers both traffic and events but starts at ~$23/mo; over the ceiling.
- **Mixpanel** — generous free tier (~1M events/mo) but the product is built for growth/marketing teams; cultural mismatch with the [non-goals](Analytics.md#non-goals), and account linkage assumes real user identity.
- **Amplitude** — same shape as Mixpanel.
- **Vercel / Netlify Analytics** — tied to platforms we don't deploy on (we're on Railway).
- **Self-hosted Plausible / Umami / PostHog / Matomo** — fails the [managed-service constraint](Analytics.md#operational); operational burden falls on a volunteer team.
- **DIY: events table in Postgres + dashboards in Django admin or Metabase** — we are not writing our own analytics system. On paper it has real attractions: maximum privacy (product event payloads never leave our infrastructure), values alignment (no third-party SDK to lock down across upgrades), and an events table that's queryable with the SQL and Django ORM skills the team already uses daily. In practice the mental model isn't simpler than a hosted vendor, it's strictly larger: design the events schema, build a capture endpoint with auth and rate limiting, derive pseudonyms, write middleware, pick and stand up a dashboarding tool (Metabase Cloud, Django admin views, or custom), build each chart from scratch, manage retention, watch table growth and indexes. PostHog's mental model is "call `capture()`, look at charts." DIY's is everything above, forever. For a small volunteer team that contradiction with the [low-maintenance constraint](Analytics.md#operational) is decisive.

## Recommendation: narrowly Umami over PostHog

PostHog and Umami are the only two real contenders — both cover traffic and product events, both have funnels and retention, both are cookieless, both have US-hosted options, both have free tiers that fit at launch. The others are dominated: Plausible and Pirsch lack retention and break the cost ceiling; GoatCounter is traffic-only.

This is a closer call than the headline implies. The honest tradeoff:

### Where Umami wins for this project

- **Narrower main-SDK surface.** Both vendors auto-collect on default config and require explicit lock-down — Umami's main tracker auto-collects pageviews (including screen dimensions, a fingerprinting concern); PostHog autocaptures every click, form submit, and input change with element selectors on top of pageviews. The asymmetry that survives the lock-down: surveys, heatmaps, and feature flags are PostHog features that Umami simply doesn't have. Session replay is in both, but Umami's lives in a separately-loaded `recorder.js` (opt-in by script inclusion) while PostHog's is in the main SDK gated by an opt-out flag.
- **Cultural fit.** PostHog is built for growth/marketing/product teams that want funnels, replays, and experimentation. Umami is built for developers and small operators who want privacy-first analytics without the surveillance machinery. The latter matches what this project actually is.
- **Simpler mental model.** Smaller product, smaller docs, smaller SDK surface.

### Where PostHog wins

- **Cost at Year 1 scale.** Free up to 1M events/mo. Umami's free tier is 100K events/mo; Pro is $20/mo for 1M events. At our Year 1 projection (~400K pv/mo + product events) we'd be on Umami's Pro tier, $10 over the ceiling. PostHog stays free.
- **Free-tier retention.** PostHog free is 1 year; Umami Hobby is 6 months. For indefinite retention either way you're paying.
- **Maturity.** Bigger ecosystem, more documentation, more battle-tested SDKs.
- **Richer UI.** Funnel-builder, retention curves, session paths are more polished.

### Why Umami narrowly wins

The two durable Umami arguments — narrower SDK surface and cultural fit — are about _what the vendor is for_, which doesn't change with configuration. PostHog's cost advantage is real but bounded: Umami Pro at $20/mo is a $10/mo overrun, not an existential cost. The retention gap (6 months free vs 1 year free) matters less because [Analytics.md](Analytics.md#retention) calls for indefinite retention anyway — both require a paid tier for that.

If the $20/mo Umami Pro tier is unacceptable, the right response is to amend the ceiling in [Analytics.md](Analytics.md#operational), not to pick PostHog to defend a $10 number. That said, PostHog with the lock-down init config is a perfectly defensible alternative — not one we'd be embarrassed by.

### Caveats before committing

1. **Verify Umami Hobby's tier gating for funnels, retention, and cohorts** — the pricing line shows Hobby's event/website/retention limits but not which analysis features are gated to Pro. Worth confirming before assuming Hobby is enough at launch.
2. **Accept the $20/mo Pro cost as a Year 1 reality**, or amend the [cost ceiling in Analytics.md](Analytics.md#operational) to reflect it. PostHog stays free at the same scale; if the cost ceiling is hard, PostHog with the lock-down init config is the alternative.
