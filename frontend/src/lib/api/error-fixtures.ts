/**
 * Test fixtures for structured API error bodies. Use these instead of
 * hand-writing literal `kind`-bearing objects in tests so that any future
 * discriminator or shape change is absorbed in one place.
 */

import type {
  PolicyDeniedBodySchema,
  RateLimitErrorBodySchema,
  ValidationErrorBodySchema,
} from './schema';

export function validationErrorBody(args: {
  message: string;
  field_errors?: Record<string, string>;
  form_errors?: string[];
}): ValidationErrorBodySchema {
  return {
    kind: 'validation_error',
    message: args.message,
    field_errors: args.field_errors ?? {},
    form_errors: args.form_errors ?? [],
  };
}

export function rateLimitErrorBody(args: {
  message?: string;
  bucket: string;
  retry_after: number;
}): RateLimitErrorBodySchema {
  return {
    kind: 'rate_limit',
    message: args.message ?? 'Rate limit exceeded.',
    bucket: args.bucket,
    retry_after: args.retry_after,
  };
}

export function policyDeniedBody(args: {
  message?: string;
  code: string;
  context?: Record<string, unknown>;
}): PolicyDeniedBodySchema {
  return {
    kind: 'policy_denied',
    message: args.message ?? 'You cannot perform that action.',
    code: args.code,
    context: args.context ?? {},
  };
}
