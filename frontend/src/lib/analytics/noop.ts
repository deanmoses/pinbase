// No-op adapter — used in dev builds, when PUBLIC_POSTHOG_KEY is empty, and
// (eventually) when a user opts out. Vitest currently selects this branch
// too; the `RecordingAnalytics` test fixture described in AnalyticsArchitecture.md
// will replace that role when the typed-events frontend plan adds the first
// `analytics.*` call sites.

import type { Analytics } from './index';

export const noopAdapter: Analytics = {
  pageview() {},
  capture() {},
  identify() {},
  reset() {},
};
