# Analytics Architecture

## Goals

The analytics system should:

- support both public traffic analytics and product analytics
- remain privacy-respectful
- avoid ad-tech ecosystems
- remain maintainable by a small team
- minimize operational burden
- support future public dashboards

## Recommended Stack

### Public Traffic Analytics

Recommended:

- Plausible
- Umami

Purpose:

- pageviews
- uniques
- referral sources
- search-engine traffic
- social traffic
- popular content
- aggregate discovery trends

Characteristics:

- lightweight
- privacy-respectful
- aggregate-focused
- minimal cookies
- no ad-tech integrations

### Product / Event Analytics

Recommended:

- PostHog Cloud

Purpose:

- editor workflow analysis
- abandoned edits
- upload funnels
- feature usage
- search UX
- contributor onboarding
- moderation workflows
- product usability

PostHog should be configured conservatively.

Recommended configuration:

- disable broad autocapture
- avoid aggressive session replay
- avoid capturing freeform text fields
- no advertising integrations
- no cross-site tracking
- explicit event instrumentation only

## Architectural Pattern

We should use an internal analytics abstraction layer.

Preferred:

```ts
analytics.track("edit_saved", {
  page_type: "machine",
  duration_seconds: 42,
});
```

Avoid:

```ts
posthog.capture(...)
```

throughout the codebase.

Benefits:

- vendor independence
- centralized governance
- easier testing
- easier migration
- consistent event naming
- centralized privacy controls

## Data Separation

Operational telemetry should remain separate from product analytics.

### Operational Telemetry

Examples:

- server logs
- performance metrics
- error tracking
- abuse detection
- security auditing

### Product Analytics

Examples:

- edit funnels
- search success
- contribution workflows
- discovery metrics

Retention policies and access controls may differ between systems.

## Public Dashboards

Public dashboards should eventually be built directly into the product rather than embedding vendor dashboards.

Potential public dashboard areas:

- contribution growth
- preservation coverage
- searches needing articles
- trending machines
- recently uploaded media
- documentation gaps
- active restoration areas

This reinforces the project’s public-interest and commons-oriented identity.
