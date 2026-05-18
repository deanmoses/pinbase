import { sequence } from '@sveltejs/kit/hooks';
import * as Sentry from '@sentry/sveltekit';
import { handleServerError } from '$lib/sentry/handle-error';

// Sentry.init lives in instrumentation.server.ts (load-order-safe site).
// sentryHandle() provides per-request scope isolation so user data from
// request N doesn't leak into request N+1, and attaches request context
// to events. Required even though we're not tracing.
export const handle = sequence(Sentry.sentryHandle());

// We pass `handleServerError` explicitly rather than letting Sentry's
// defaultErrorHandler take over — see lib/sentry/handle-error.ts.
export const handleError = Sentry.handleErrorWithSentry(handleServerError);
