// Load-order-safe init site for the SvelteKit server SDK. SvelteKit loads
// this file (when `kit.experimental.instrumentation.server` is on) before
// any other server import, which is required by the OpenTelemetry-powered
// server SDK in @sentry/sveltekit >= 10.8.0.
//
// Do NOT move Sentry.init() into hooks.server.ts — it's no longer load-order-safe.
//
// Read DSN/release from process.env DIRECTLY, not via `$env/dynamic/*`.
// SvelteKit's env shim is not yet initialized at this point in the load
// order — `publicEnv.PUBLIC_SENTRY_DSN` and `privateEnv.RAILWAY_GIT_COMMIT_SHA`
// both resolve to `undefined` here, even when the underlying env vars are
// set on the process. We confirmed this empirically: the same code reading
// from `$env/dynamic/*` skipped Sentry.init silently in production (SSR
// errors never reached Sentry); switching to process.env fixed it. Browser
// init (hooks.client.ts) is exempt because it runs after the SvelteKit
// runtime is fully bootstrapped and the shim works there.
//
// SSR is part of the frontend, so its events go to the `flipcommons-frontend`
// Sentry project — NOT the backend project the Django process uses. PUBLIC_
// vars are readable server-side via process.env just like private ones.
import * as Sentry from '@sentry/sveltekit';
import { IGNORE_ERRORS } from '$lib/sentry/ignore-errors';

const dsn = process.env.PUBLIC_SENTRY_DSN;
const release = process.env.RAILWAY_GIT_COMMIT_SHA;

if (dsn) {
  Sentry.init({
    dsn,
    environment: 'production',
    release,
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
