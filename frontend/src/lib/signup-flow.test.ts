import { describe, expect, it } from 'vitest';
import { classifySignupSubmit } from './signup-flow';

describe('classifySignupSubmit', () => {
  it('returns success with redirect_url when data is present', () => {
    expect(classifySignupSubmit({ redirect_url: '/dashboard' }, null)).toEqual({
      kind: 'success',
      redirect_url: '/dashboard',
    });
  });

  it('classifies username_taken', () => {
    expect(
      classifySignupSubmit(undefined, {
        detail: { kind: 'username_taken', message: 'Username is taken.' },
      }),
    ).toEqual({ kind: 'username_taken' });
  });

  it('classifies username_rejected and carries the reason', () => {
    expect(
      classifySignupSubmit(undefined, {
        detail: { kind: 'username_rejected', message: 'rejected', reason: 'reserved' },
      }),
    ).toEqual({ kind: 'username_rejected', reason: 'reserved' });
  });

  it('classifies pending_invalid', () => {
    expect(
      classifySignupSubmit(undefined, {
        detail: { kind: 'pending_invalid', message: 'expired' },
      }),
    ).toEqual({ kind: 'pending_invalid' });
  });

  it('classifies rate_limit as rate_limited', () => {
    expect(
      classifySignupSubmit(undefined, {
        detail: { kind: 'rate_limit', message: 'slow down', bucket: 'x', retry_after: 60 },
      }),
    ).toEqual({ kind: 'rate_limited' });
  });

  it('returns unknown_error when the kind is unrecognized', () => {
    expect(classifySignupSubmit(undefined, { detail: { kind: 'something_new' } })).toEqual({
      kind: 'unknown_error',
    });
  });

  it('returns unknown_error when detail is missing', () => {
    expect(classifySignupSubmit(undefined, {})).toEqual({ kind: 'unknown_error' });
  });

  it('returns unknown_error when the body is null (non-JSON 4xx)', () => {
    expect(classifySignupSubmit(undefined, null)).toEqual({ kind: 'unknown_error' });
  });
});
