import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { loadAuthenticatedMe } from './load-me.server';

const GET = vi.fn();
const client = { GET } as unknown as Parameters<typeof loadAuthenticatedMe>[0];

function ok<T>(data: T, status = 200) {
  return { data, error: undefined, response: new Response(null, { status }) };
}

beforeEach(() => {
  GET.mockReset();
  // Quiet expected error logs from fail-closed paths.
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('loadAuthenticatedMe', () => {
  it('returns the parsed Me on success', async () => {
    GET.mockResolvedValueOnce(ok({ is_authenticated: true, capabilities: { 'x.y': true } }));
    const me = await loadAuthenticatedMe(client, 'test');
    expect(me.is_authenticated).toBe(true);
    expect(me.capabilities?.['x.y']).toBe(true);
  });

  it('redirects anonymous users to /login', async () => {
    GET.mockResolvedValueOnce(ok({ is_authenticated: false, capabilities: {} }));
    await expect(loadAuthenticatedMe(client, 'test')).rejects.toMatchObject({
      status: 302,
      location: '/login',
    });
  });

  // #420: the literal failure mode from the Sentry trace — DNS resolution
  // against the public origin fails from inside the container. Must surface
  // as a system error, not get silently swallowed.
  it('throws 503 when the /me/ fetch rejects (network failure)', async () => {
    GET.mockRejectedValueOnce(new Error('getaddrinfo ENOTFOUND flipcommons.org'));
    await expect(loadAuthenticatedMe(client, 'test')).rejects.toMatchObject({ status: 503 });
  });

  it('throws with the upstream status when /me/ returns non-2xx with no data', async () => {
    GET.mockResolvedValueOnce({
      data: undefined,
      error: { detail: 'nope' },
      response: new Response(null, { status: 502 }),
    });
    await expect(loadAuthenticatedMe(client, 'test')).rejects.toMatchObject({ status: 502 });
  });

  // openapi-fetch does not runtime-validate the generated schema. A 200
  // with a body that's missing is_authenticated (or has a non-boolean
  // value) is an upstream schema fault — must surface as a system error,
  // not get reinterpreted as anonymous and redirect to /login.
  it('throws 500 when /me/ body is missing is_authenticated', async () => {
    GET.mockResolvedValueOnce(ok({ capabilities: {} } as unknown as { is_authenticated: boolean }));
    await expect(loadAuthenticatedMe(client, 'test')).rejects.toMatchObject({ status: 500 });
  });

  it('throws 500 when /me/ body has non-boolean is_authenticated', async () => {
    GET.mockResolvedValueOnce(
      ok({ is_authenticated: 'true' } as unknown as { is_authenticated: boolean }),
    );
    await expect(loadAuthenticatedMe(client, 'test')).rejects.toMatchObject({ status: 500 });
  });

  // SvelteKit's error() requires 400..599; a sub-400 status with no body
  // (rare but possible) must be normalized rather than throwing the wrong
  // exception out of error() itself.
  it('normalizes sub-400 status with no data to 500', async () => {
    GET.mockResolvedValueOnce({
      data: undefined,
      error: undefined,
      response: new Response(null, { status: 204 }),
    });
    await expect(loadAuthenticatedMe(client, 'test')).rejects.toMatchObject({ status: 500 });
  });
});
