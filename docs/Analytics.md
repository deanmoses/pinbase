# Analytics

We use **[PostHog](https://posthog.com)** for product analytics.

## Current surface area

Pageviews only. No typed events.

### Enabling & disabling analytics

Analytics can only be enabled in prod. Disabling analytics in prod means clearing `PUBLIC_POSTHOG_KEY` and redeploying — same pattern as `PUBLIC_SENTRY_DSN`.

`posthog-js` ships in every production bundle once any call site imports `$lib/analytics`, regardless of whether the key is set. The runtime guard is the master switch, not the bundle.

## Privacy posture (what's stored)

PostHog **does not store**: IPs, cookies, localStorage identity, autocaptured clicks/inputs, screen/viewport dimensions, UTM/click-id campaign params, search-engine keyword props, URL query strings.

PostHog **does store**: path-only pageviews, browser/OS user-agent fields it derives server-side, referrer origin+path (no query), session id (memory-scoped, dies on tab close).

For the project-wide privacy contract see [Privacy.md](Privacy.md).
