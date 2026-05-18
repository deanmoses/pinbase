// Shared "don't capture" list for SSR + browser Sentry inits.
//
// See docs/Observability.md for the capture policy. Strings match Sentry's
// `ignoreErrors` semantics: each entry is matched against the error message
// and type — strings are substring matches, regexes are tested directly.
//
// Generic network-failure strings (`Failed to fetch`, `Load failed`,
// `NetworkError when attempting to fetch resource`) are deliberately NOT
// here — they can mask real production breakage (API down, CORS misconfig,
// HTML returned to a fetch). Add later only if they dominate the noise floor.
export const IGNORE_ERRORS: (string | RegExp)[] = [
  // ResizeObserver — browsers fire this when a callback dirties layout;
  // harmless and impossible to fix from app code.
  'ResizeObserver loop limit exceeded',
  'ResizeObserver loop completed with undelivered notifications',

  // Non-Error throws (e.g. `throw "string"`) — Sentry wraps these and the
  // resulting events have no stack of any use.
  'Non-Error promise rejection captured',

  // Navigation/fetch aborts — expected when the user navigates away mid-request.
  'AbortError',
  'The operation was aborted',

  // Post-deploy stale-bundle navigations — the old SPA tries to load a chunk
  // that no longer exists on the server. Surface via Application Health, not
  // exception alerts.
  'ChunkLoadError',
  /Loading chunk \d+ failed/,
];
