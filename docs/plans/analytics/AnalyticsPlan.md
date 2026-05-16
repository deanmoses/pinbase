# Analytics Rollout Plan

Also see:

- [Analytics.md](Analytics.md)
- [AnalyticsArchitecture.md](AnalyticsArchitecture.md)
- [AnalyticsBackendPlan.md](AnalyticsBackendPlan.md)
- [AnalyticsFrontendPlan.md](AnalyticsFrontendPlan.md)

## Phases

- [AnalyticsBackendPlan.md](AnalyticsBackendPlan.md)
- [AnalyticsFrontendPlan.md](AnalyticsFrontendPlan.md)

Backend before frontend because the pseudonym is the keystone. It's derived server-side and arrives in the page payload; the frontend just consumes it. Build the keystone first.

## Definition of Done

Rollout is complete when:

- Every event in the typed registry (`events.ts` / `events.py`) is emitted from the side specified in [AnalyticsArchitecture.md § Where Events Originate](AnalyticsArchitecture.md#where-events-originate).
- PostHog receives no PII, no IP, no fingerprinting-grade properties (verified by inspecting a real event payload, not just by reading the init config).
- Joining the PostHog dataset to the `User` table requires both the database and `ANALYTICS_PSEUDONYM_KEY` — there is no FK or table that bridges them.
- Lint pins prevent `posthog-js` / `posthog` imports outside the adapter modules.
- One integration test on each side asserts the locked-down init config; weakening any option fails the test.
