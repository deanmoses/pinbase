import type { HandleClientError, HandleServerError } from '@sveltejs/kit';

// SvelteKit's `handleError` hook is called for every unexpected error
// during a request, including the SvelteKitError(404) thrown by prerender's
// link-discovery crawl over `/api/*` preload hints. We pass these handlers
// to Sentry.handleErrorWithSentry(...) so Sentry's defaultErrorHandler
// (which dumps a full stack for every error, 4xx included) is never used.
//
// 4xx: log a single line at info level. A 4xx is an expected request
//      outcome (the server correctly said "not here" / "not allowed"),
//      not a server fault, so it should not surface as severity=error in
//      log aggregators. Stacks are pure noise — Sentry already filters
//      these out of captureException.
// 5xx: log the line plus the stack at error level. Sentry has the
//      structured event; the stack in stderr gives operators immediate
//      context to grep Sentry by.

export const handleServerError: HandleServerError = ({ error, status, event }) => {
  const code = status ?? 500;
  const line = `[${code}] ${event.request.method} ${event.url.pathname}`;
  if (code >= 400 && code < 500) {
    console.info(line);
    return;
  }
  const stack = error instanceof Error ? error.stack : String(error);
  console.error(`\x1b[1;31m${line}\x1b[0m\n${stack}`);
};

export const handleClientError: HandleClientError = ({ error, status, message }) => {
  const code = status ?? 500;
  const line = `[${code}] ${message}`;
  if (code >= 400 && code < 500) {
    console.info(line);
    return;
  }
  const stack = error instanceof Error ? error.stack : String(error);
  console.error(`${line}\n${stack}`);
};
