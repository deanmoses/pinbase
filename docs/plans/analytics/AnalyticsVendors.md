# Analytics Vendor Research

Also see:

- [Analytics.md](Analytics.md)

## Status

**Selected: [PostHog Cloud](#posthog-cloud).** See [Recommendation: PostHog over Umami](#recommendation-posthog-over-umami) for the reasoning. This document records the candidates and the evaluation against the requirements in [Analytics.md](Analytics.md).

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
- **Multi-admin at the price point we'd actually pay** — multiple volunteers must each get their own login. Per [SmallTeam.md](../../SmallTeam.md#hosted-systems-must-be-multi-admin), this is a hard requirement, not a nice-to-have. Single-user-only vendors are disqualified at any tier we'd choose
- **Managed / hosted** — no self-hosting
- **Retention** — long retention without per-row fees
- **Geography** — ingest reachable from US/Virginia without painful latency
- **Maintenance fit** for a small volunteer team

## Comparison Matrix

| Vendor                        | Covers traffic | Covers events | Cookieless | Funnels        | Retention / cohorts | Cost at 2.5k pv | Cost at 400k pv           | Multi-admin at our tier           | Maintenance |
| ----------------------------- | -------------- | ------------- | ---------- | -------------- | ------------------- | --------------- | ------------------------- | --------------------------------- | ----------- |
| [PostHog](#posthog-cloud)     | ✅             | ✅            | ✅         | ✅             | ✅                  | free            | free (under 1M events/mo) | ✅ unlimited on free              | medium      |
| [Plausible](#plausible-cloud) | ✅             | ✅            | ✅         | ✅ (Business)  | ❌                  | ~$19/mo         | above ceiling             | ✅ 3 on Growth, 10 on Business    | low         |
| [Pirsch](#pirsch)             | ✅             | ✅            | ✅         | ✅ (Plus tier) | ❌                  | ~$12/mo         | above ceiling             | ✅ on paid tiers                  | low         |
| [Umami Cloud](#umami-cloud)   | ✅             | ✅            | ✅         | ✅             | ✅                  | free            | $20/mo (Pro)              | ❌ Hobby is single-user; Pro-only | low         |
| [GoatCounter](#goatcounter)   | ✅             | ❌            | ✅         | ❌             | ❌                  | free            | free                      | ✅ free; users in Settings        | trivial     |

## Shortlist

### PostHog Cloud

- **Coverage**: visitor traffic + product events in one tool
- **Cookieless**: yes, with `persistence: "memory"`
- **Ad-tech lineage**: none; product-analytics company, not ad-tech
- **Pseudonymous linkage**: yes, `identify(pseudonym)` is the intended API
- **Anonymous events**: yes
- **Raw queries**: yes, arbitrary string properties
- **Cost**: free tier covers 1M events/mo and 5k recordings/mo; product analytics alone stays free comfortably through Year 1 traffic
- **Multi-admin**: unlimited team members on the free tier (confirmed on [pricing page](https://posthog.com/pricing))
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
- **Pseudonymous linkage**: no for this project. Custom properties can segment events, but Plausible explicitly treats pseudonymous end-user identifiers as PII that must not be sent
- **Anonymous events**: yes
- **Raw queries**: custom event properties are supported but the UI is geared toward low-cardinality dimensions; raw search-query storage works as event payload
- **Funnels / retention**: funnels yes on Business; retention and cohorts not on the roadmap (per [GH discussion #364](https://github.com/plausible/analytics/discussions/364))
- **Cost**: Starter is ~$9/mo for 10k pv, but funnels and custom properties require Business starting at ~$19/mo → **breaks the $10 ceiling on day one if product analytics features are required**
- **Multi-admin**: yes — up to 3 members on Growth, 10 on Business (no free tier)
- **Hosting**: managed (EU)
- **Retention**: 3 years on Starter/Growth, 5 years on Business, 5+ years on Enterprise
- **Geography**: EU only
- **Maintenance**: minimal; tiny script, simple dashboard

**Case for**: the reference privacy-first traffic tool; now covers part of the product-analytics middle ground (custom events, funnels, custom properties); near-zero maintenance.

**Case against**: price starts past the ceiling once required product-analytics features are included; no pseudonymous user linkage under Plausible's PII rules; no retention/cohort analysis means questions like "what % of last month's first-time editors came back" can't be answered in-tool.

### Pirsch

- **Coverage**: visitor traffic + custom events; funnel analysis on the Plus tier
- **Cookieless**: yes
- **Ad-tech lineage**: none
- **Pseudonymous linkage**: custom event metadata supports key/value pairs. Values are strings in the JavaScript API, with documented limits
- **Anonymous events**: yes
- **Raw queries**: custom event properties supported
- **Funnels / retention**: funnels yes (Plus only); retention not advertised
- **Cost**: Standard starts at $6/mo for 10k pv; Plus starts at $12/mo with funnels — **Plus exceeds the $10 ceiling on day one**. Exact 400k pv pricing should be checked in the live pricing slider before committing
- **Multi-admin**: yes — team members supported on paid plans (no free tier)
- **Hosting**: managed (EU/Germany)
- **Retention**: indefinite on paid plans
- **Geography**: EU only
- **Maintenance**: minimal

**Case for**: cheaper than Plausible on the Standard tier; same privacy posture.

**Case against**: the tier with funnels ($12/mo) is over the ceiling from day one; metadata is string-only in the JavaScript API; no retention/cohorts.

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
- **Multi-admin**: ❌ **Hobby is single-user.** Teams is gated to the Pro plan (confirmed in the [Umami Cloud Teams docs](https://docs.umami.is/docs/cloud/teams): "Teams is available starting at the Pro plan"). To add a co-admin we'd have to pay $20/mo — and the only reason we'd pay $20/mo is to add a co-admin, since the event volume fits Hobby until Year 1
- **Hosting**: managed (US)
- **Retention**: 6 months on Hobby, longer on Pro
- **Geography**: US-hosted
- **Maintenance**: minimal

**Case for**: Hobby tier covers ~80K pageviews/mo + product events for free; US-hosted (matches the stated geography preference); covers the same product-analytics surface area as PostHog for our use cases (funnels + retention + custom properties); main tracker doesn't ship the features we don't want — only replay is available, and only as a deliberately-added second script.

**Case against**: **Hobby is single-user — fails the multi-admin requirement at the free tier**, and Pro at $20/mo is the only way to add a second volunteer. 6-month free-tier retention is shorter than PostHog's 1 year; funnel/retention/cohort tier gating on Hobby still needs verification.

### GoatCounter

- **Coverage**: visitor traffic only; minimal custom event support
- **Cookieless**: yes
- **Ad-tech lineage**: none; explicitly anti-ad-tech, single-developer project
- **Pseudonymous linkage**: no
- **Anonymous events**: limited
- **Raw queries**: not really — designed for pageview counts
- **Cost**: **free for reasonable public usage**, including personal websites and small-to-medium businesses; donations welcomed
- **Multi-admin**: yes on the free tier (multiple users via Settings → Users)
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

## Recommendation: PostHog over Umami

PostHog and Umami are the only two real contenders — both cover traffic and product events, both have funnels and retention, both are cookieless, both have US-hosted options, both have free tiers that fit at launch. The others are dominated: Plausible and Pirsch lack retention and break the cost ceiling; GoatCounter is traffic-only.

The deciding factor is **multi-admin at the price point we'd actually pay**. PostHog's free tier includes unlimited team members; Umami's Hobby tier is single-user, with Teams gated to the Pro plan at $20/mo. Per [SmallTeam.md](../../SmallTeam.md#hosted-systems-must-be-multi-admin) this is a hard requirement, so the comparison narrows to: PostHog free vs Umami Pro ($20/mo). For the same multi-admin posture, PostHog gives us strictly more (1M events/mo free, 1 year retention free) than Umami Pro does at $20/mo. Paying for the smaller package is hard to defend.

### Where Umami still wins for this project

- **Vendor self-conception.** Umami positions itself as privacy-first analytics for developers and small operators. PostHog positions itself as an all-in-one product OS — funnels, replays, experimentation, feature flags, surveys, growth loops. The latter is powerful but carries goals this project explicitly does not share. The difference isn't what each tool can do; it's what each tool nudges you toward.
- **Cleaner privacy story to explain publicly.** "We use privacy-focused analytics with auto-tracking off and explicit events only" is a one-sentence story. "We use a growth analytics suite but have disabled most of it" is a paragraph that invites scrutiny.
- **Narrower main-SDK surface.** Both vendors auto-collect on default config and require explicit lock-down — Umami's main tracker auto-collects pageviews (including screen dimensions, a fingerprinting concern); PostHog autocaptures every click, form submit, and input change with element selectors on top of pageviews. The asymmetry that survives the lock-down: surveys, heatmaps, and feature flags are PostHog features that Umami simply doesn't have. Session replay is in both, but Umami's lives in a separately-loaded `recorder.js` (opt-in by script inclusion) while PostHog's is in the main SDK gated by an opt-out flag.
- **Smaller blast radius for future maintainers.** A future contributor poking around Umami won't _discover_ a "turn on all the insights" path because surveys, heatmaps, feature flags, and experimentation aren't features. PostHog's dashboard actively invites that exploration. This is the durability argument: it survives any single maintainer's discipline.
- **Simpler to work with day-to-day.**
  - **Smaller API surface to learn.** Umami's tracker API is essentially `track()` and `identify()`. PostHog's JS SDK has dozens of methods and init options. Less to learn before a contributor can safely add an event.
  - **Smaller config-drift risk.** Both vendors require one-time hardening. PostHog's init has ~7 options whose defaults could shift across major SDK versions; Umami's has ~2. Fewer places a bad upgrade could re-enable something.
  - **Lower review burden.** A PR touching analytics in PostHog requires reviewers to know which of 12+ vendor capabilities are safe; the Umami equivalent is ~3. Reviewers build that intuition faster.
  - **UI shapes the questions asked.** PostHog's Lifecycle, Stickiness, and Paths tabs invite engagement-style questions; Umami's narrower UI limits drift toward metrics this project rejected. The dashboard isn't just a viewer; it's a prompt.
  - **Faster contributor onboarding.** A volunteer joining the project has much less to learn before safely adding an event in Umami than in PostHog. Matters for the small-team constraint.

_Caveat on all of the above: cultural fit is not a substitute for technical controls. With either vendor, the lock-down work in [Architecture.md](AnalyticsArchitecture.md#privacy-enforcement) is what actually enforces the privacy posture. The cultural arguments are about which vendor makes that work easier to defend over time, not which one is private by default._

### Where PostHog wins

- **Multi-admin on the free tier.** Unlimited team members at $0. Umami Hobby is single-user; Teams requires Pro at $20/mo. This is the disqualifier for Umami at the free tier we'd actually use.
- **Cost at Year 1 scale.** Free up to 1M events/mo. Umami's free tier is 100K events/mo; Pro is $20/mo for 1M events. At our Year 1 projection (~400K pv/mo + product events) we'd be on Umami's Pro tier anyway.
- **Free-tier retention.** PostHog free is 1 year; Umami Hobby is 6 months. For indefinite retention either way you're paying.
- **Maturity.** Bigger ecosystem, more documentation, more battle-tested SDKs.
- **Richer UI.** Funnel-builder, retention curves, session paths are more polished.

### Why PostHog wins overall

The durable Umami arguments — vendor self-conception, public-story simplicity, narrower SDK surface, blast radius — are real and don't disappear just because we picked the other vendor. They're the reason this is "PostHog with lock-down config," not "PostHog with defaults." But they're tradeoff arguments, and the multi-admin requirement isn't a tradeoff: per [SmallTeam.md](../../SmallTeam.md#hosted-systems-must-be-multi-admin), single-user hosted systems are disqualified.

Once multi-admin is the gating filter, the comparison stops being "PostHog free vs Umami Hobby free" and becomes "PostHog free vs Umami Pro at $20/mo." Umami Pro isn't unaffordable — [SmallTeam.md](../../SmallTeam.md#cheap) calls $20 "very expensive" but not out of the question — but we'd be paying $20/mo to get a strictly smaller package than PostHog gives us at $0 (100K vs 1M events/mo, 6mo vs 1yr retention, narrower SDK but at the cost of every durable advantage _also_ costing us $20). The lock-down work on PostHog is real but bounded; paying $20/mo indefinitely to avoid it is the larger cost.

### Caveats before committing

1. **Lock down the PostHog SDK init.** Autocapture, session replay, surveys, heatmaps, and feature flags all default-on. The hardening config and how to keep it stable across SDK upgrades belongs in [AnalyticsArchitecture.md](AnalyticsArchitecture.md#privacy-enforcement).
2. **Document the public privacy story.** Because PostHog is a growth-analytics suite by default, the public-facing explanation of what we do and don't collect needs to be specific (which features are off, what data leaves the browser) rather than relying on vendor reputation. The Umami "we use a privacy-first analytics tool" one-liner doesn't apply here.
3. **Treat the durable Umami arguments as a watchlist, not sunk cost.** If PostHog's defaults drift, if surveys/feature-flags creep into our usage, or if the small-team review burden becomes real, the case to revisit Umami Pro at $20/mo is open.
