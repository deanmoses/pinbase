/**
 * Signup submit-result classification.
 *
 * Pure function over the openapi-fetch result shape: takes the success body
 * (or undefined) and the parsed error body (or null) and returns a typed
 * outcome. Lives outside the Svelte handler so the branch table is exercised
 * by pure-TS tests with no mocks and no DOM. The handler owns the HTTP call,
 * the response.json() awaiting, and the network-error catch.
 */

import type { SignupSubmitResponseSchema, UsernameRejectedErrorBodySchema } from '$lib/api/schema';

export type SignupSubmitOutcome =
  | { kind: 'success'; redirect_url: string }
  | { kind: 'username_taken' }
  | {
      kind: 'username_rejected';
      reason: UsernameRejectedErrorBodySchema['reason'];
    }
  | { kind: 'pending_invalid' }
  | { kind: 'rate_limited' }
  | { kind: 'unknown_error' };

// Minimal shape we read off the 4xx body. The OpenAPI schema guarantees more,
// but the runtime input is unknown JSON so we narrow defensively.
interface StructuredErrorBody {
  detail?: { kind?: string; reason?: string };
}

export function classifySignupSubmit(
  data: SignupSubmitResponseSchema | undefined,
  errorBody: unknown,
): SignupSubmitOutcome {
  if (data) return { kind: 'success', redirect_url: data.redirect_url };
  const detail = (errorBody as StructuredErrorBody | null)?.detail;
  switch (detail?.kind) {
    case 'username_rejected':
      return {
        kind: 'username_rejected',
        reason: detail.reason as UsernameRejectedErrorBodySchema['reason'],
      };
    case 'username_taken':
      return { kind: 'username_taken' };
    case 'pending_invalid':
      return { kind: 'pending_invalid' };
    case 'rate_limit':
      return { kind: 'rate_limited' };
    default:
      return { kind: 'unknown_error' };
  }
}
