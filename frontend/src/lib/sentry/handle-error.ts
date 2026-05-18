import type { HandleClientError, HandleServerError } from '@sveltejs/kit';

// SvelteKit's `handleError` hook is called for every unexpected error
// during a request, including the SvelteKitError(404) thrown by prerender's
// link-discovery crawl over `/api/*` preload hints. We pass these handlers
// to Sentry.handleErrorWithSentry(...) so Sentry's defaultErrorHandler
// (which dumps a full stack for every error, 4xx included) is never used.
//
// 4xx: log a single line. Stacks are pure noise — these are expected paths
//      (prerender link probes, browser 404s, etc.) that Sentry already
//      filters out of captureException.
// 5xx: log the line plus the stack. Sentry has the structured event; the
//      stack in stderr/console gives operators immediate context to grep
//      Sentry by.
//
// Stylistically tracks SvelteKit's own format_server_error
// (kit/src/runtime/server/utils.js) so the build log feels unchanged
// from the no-Sentry baseline.

function formatLine(status: number | undefined, method: string, pathname: string): string {
  const code = status ?? 500;
  return `\x1b[1;31m[${code}] ${method} ${pathname}\x1b[0m`;
}

export const handleServerError: HandleServerError = ({ error, status, event }) => {
  const code = status ?? 500;
  const line = formatLine(code, event.request.method, event.url.pathname);
  if (code >= 400 && code < 500) {
    console.error(line);
    return;
  }
  const stack = error instanceof Error ? error.stack : String(error);
  console.error(`${line}\n${stack}`);
};

export const handleClientError: HandleClientError = ({ error, status, message }) => {
  const code = status ?? 500;
  if (code >= 400 && code < 500) {
    console.error(`[${code}] ${message}`);
    return;
  }
  const stack = error instanceof Error ? error.stack : String(error);
  console.error(`[${code}] ${message}\n${stack}`);
};
