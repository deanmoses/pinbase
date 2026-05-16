# Analytics Rollout Plan

Also see:

- [Analytics.md](Analytics.md)
- [AnalyticsArchitecture.md](AnalyticsArchitecture.md)
- [AnalyticsBackendPlan.md](AnalyticsBackendPlan.md)
- [AnalyticsFrontendPlan.md](AnalyticsFrontendPlan.md)
- [AnalyticsEventTaxonomy.md](AnalyticsEventTaxonomy.md)

This doc is the orchestration view: phase ordering, dependencies between backend and frontend, what "done" looks like. Implementation detail lives in the child plans.

## Sequencing: backend first

The backend ships before the frontend, in that order.

**Why:**

- The pseudonym is the keystone. It's derived server-side and arrives in the page payload; the frontend just consumes it. Build the keystone first.
- `account_registered` is a great first event — server-only by necessity (fires inside the signup transaction), low-volume, easy to verify the pseudonym round-trips correctly without volume noise.
- The privacy lockdown is testable in isolation (`disable_geoip`, no PII, IP stripped at ingest) before any client volume hits PostHog.
- Smaller blast radius. One Django app, one middleware, a handful of `analytics.capture()` calls. No SSR/CSR concerns, no Svelte lifecycle, no bundle weight.
- The site is pre-launch. There's no traffic to measure yet; the first useful signal is conversion to signup, which is server-side.

**What backend-first does not give us:**

- Pageviews, search, journey reconstruction, traffic sources, bounce rates — none of it. Those land with the frontend.
- Don't let "we have analytics now" creep into the team's mental model after the backend ships. It's "we have the attribution mechanism now." Journey data starts when the frontend lands.

## Phase order

| #   | Phase                                                      | Doc                                                                                |
| --- | ---------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 1   | Backend skeleton — modules, lint pin, adapters, middleware | [AnalyticsBackendPlan.md](AnalyticsBackendPlan.md#phase-1-skeleton)                |
| 2   | `account_registered` end-to-end                            | [AnalyticsBackendPlan.md](AnalyticsBackendPlan.md#phase-2-account_registered)      |
| 3   | `edit_saved` — proves middleware-cached pseudonym          | [AnalyticsBackendPlan.md](AnalyticsBackendPlan.md#phase-3-edit_saved)              |
| 4   | `photo_uploaded`, `moderation_action`                      | [AnalyticsBackendPlan.md](AnalyticsBackendPlan.md#phase-4-remaining-server-events) |
| 5   | Frontend skeleton — modules, locked init config, lint pin  | [AnalyticsFrontendPlan.md](AnalyticsFrontendPlan.md#phase-1-skeleton)              |
| 6   | Pageviews via `afterNavigate`                              | [AnalyticsFrontendPlan.md](AnalyticsFrontendPlan.md#phase-2-pageviews)             |
| 7   | `identify()` on auth hydration, `reset()` on logout        | [AnalyticsFrontendPlan.md](AnalyticsFrontendPlan.md#phase-3-identify)              |
| 8   | Client events — search, machine page, edit lifecycle       | [AnalyticsFrontendPlan.md](AnalyticsFrontendPlan.md#phase-4-client-events)         |

## Handoff: backend → frontend

There is one load-bearing dependency between the two halves: **the frontend's `identify(pseudonym)` reads the pseudonym from the page payload, which the backend must supply.**

Concretely:

- Backend phase 2 adds `pseudonym` to the authenticated user's page payload (alongside the user object).
- Frontend phase 3 consumes that field in the root layout.

Until backend phase 2 lands, the frontend would have to stub `identify()` or call it with a placeholder. So phase 5 (frontend skeleton) is the earliest the frontend can usefully start; phase 7 (`identify`) cannot land before backend phase 2.

Everything else is independent: lint pins, test harnesses, event registries, the init lockdown, the abstraction interface. The two halves share contracts (defined in [AnalyticsArchitecture.md](AnalyticsArchitecture.md)) but do not share code.

## "Done" definition

Rollout is complete when:

- Every event in [AnalyticsEventTaxonomy.md](AnalyticsEventTaxonomy.md) is emitted from the side specified in [AnalyticsArchitecture.md § Where Events Originate](AnalyticsArchitecture.md#where-events-originate).
- PostHog receives no PII, no IP, no fingerprinting-grade properties (verified by inspecting a real event payload, not just by reading the init config).
- Joining the PostHog dataset to the `User` table requires both the database and `ANALYTICS_PSEUDONYM_KEY` — there is no FK or table that bridges them.
- Lint pins prevent `posthog-js` / `posthog` imports outside the adapter modules.
- One integration test on each side asserts the locked-down init config; weakening any option fails the test.

After that, this doc and the two child plans can be deleted. The architecture doc remains.
