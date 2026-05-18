import * as Sentry from '@sentry/sveltekit';
import { env } from '$env/dynamic/public';
import { handleClientError } from '$lib/sentry/handle-error';
import { IGNORE_ERRORS } from '$lib/sentry/ignore-errors';

// `$env/dynamic/public` (not `static`) so importing this module doesn't
// fail at build time when the PUBLIC_ vars are unset — the runtime DSN
// guard is the master switch.
if (env.PUBLIC_SENTRY_DSN) {
  Sentry.init({
    dsn: env.PUBLIC_SENTRY_DSN,
    environment: 'production',
    release: env.PUBLIC_RAILWAY_GIT_COMMIT_SHA,
    tracesSampleRate: 0,
    sendDefaultPii: false,
    // replayIntegration and feedbackIntegration are deliberately NOT added —
    // see docs/Observability.md § Privacy.
    ignoreErrors: IGNORE_ERRORS,
  });
}

// We pass `handleClientError` explicitly rather than letting Sentry's
// defaultErrorHandler take over — see lib/sentry/handle-error.ts.
export const handleError = Sentry.handleErrorWithSentry(handleClientError);
