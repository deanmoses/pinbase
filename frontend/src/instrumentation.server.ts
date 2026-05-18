// Load-order-safe init site for the SvelteKit server SDK. SvelteKit loads
// this file (when `kit.experimental.instrumentation.server` is on) before
// any other server import, which is required by the OpenTelemetry-powered
// server SDK in @sentry/sveltekit >= 10.8.0.
//
// Do NOT move Sentry.init() into hooks.server.ts — it's no longer load-order-safe.
import * as Sentry from '@sentry/sveltekit';
import { env as publicEnv } from '$env/dynamic/public';
import { env as privateEnv } from '$env/dynamic/private';
import { IGNORE_ERRORS } from '$lib/sentry/ignore-errors';

// SSR is part of the frontend, so its events go to the `flipcommons-frontend`
// Sentry project (same as the browser) — NOT the backend project that the
// Django process uses. We deliberately read PUBLIC_SENTRY_DSN here even
// though we're on the server; `PUBLIC_` vars are readable server-side, and
// using the same DSN as the browser is what keeps SSR and browser events
// in the same project.
if (publicEnv.PUBLIC_SENTRY_DSN) {
  Sentry.init({
    dsn: publicEnv.PUBLIC_SENTRY_DSN,
    environment: 'production',
    release: privateEnv.RAILWAY_GIT_COMMIT_SHA,
    tracesSampleRate: 0,
    sendDefaultPii: false,
    // JS-server SDK extracts up to 10KB of request body by default. The
    // architecture doc's "SDK never extracts the request body" claim
    // depends on this option being set — equivalent to the backend's
    // max_request_body_size="never".
    integrations: [Sentry.httpIntegration({ maxIncomingRequestBodySize: 'none' })],
    ignoreErrors: IGNORE_ERRORS,
  });
}
