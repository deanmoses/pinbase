import { beforeEach, describe, expect, it, vi } from 'vitest';

const GET = vi.fn();

vi.mock('$lib/api/client', () => ({
  createApiClient: () => ({ GET }),
}));

const { requireCapability } = await import('./require-capability');

function ok<T>(data: T, status = 200) {
  return { data, error: undefined, response: new Response(null, { status }) };
}

const fetchStub = (() => undefined) as unknown as typeof globalThis.fetch;
const url = new URL('http://localhost/titles/new');

beforeEach(() => {
  GET.mockReset();
});

describe('requireCapability', () => {
  it('returns without throwing when the capability is granted', async () => {
    GET.mockResolvedValueOnce(
      ok({ is_authenticated: true, capabilities: { 'catalog.create': true } }),
    );

    await expect(
      requireCapability({ fetch: fetchStub, url, activity: 'catalog.create' }),
    ).resolves.toBeUndefined();
  });

  it('redirects authenticated-but-uncapable users to /verify-email', async () => {
    GET.mockResolvedValueOnce(
      ok({ is_authenticated: true, capabilities: { 'catalog.create': false } }),
    );

    await expect(
      requireCapability({ fetch: fetchStub, url, activity: 'catalog.create' }),
    ).rejects.toMatchObject({ status: 302, location: '/verify-email' });
  });

  it('redirects authenticated users with the capability key missing to /verify-email', async () => {
    GET.mockResolvedValueOnce(ok({ is_authenticated: true, capabilities: {} }));

    await expect(
      requireCapability({ fetch: fetchStub, url, activity: 'catalog.create' }),
    ).rejects.toMatchObject({ status: 302, location: '/verify-email' });
  });

  it('redirects anonymous users to /login', async () => {
    GET.mockResolvedValueOnce(ok({ is_authenticated: false, capabilities: {} }));

    await expect(
      requireCapability({ fetch: fetchStub, url, activity: 'catalog.create' }),
    ).rejects.toMatchObject({ status: 302, location: '/login' });
  });

  it('fails open when /api/auth/me/ itself errors', async () => {
    // A transient /me/ failure should not boot an already-logged-in
    // editor to /login. The backend will reject any unauthorized submit.
    GET.mockResolvedValueOnce({
      data: undefined,
      error: { detail: 'nope' },
      response: new Response(null, { status: 500 }),
    });

    await expect(
      requireCapability({ fetch: fetchStub, url, activity: 'catalog.create' }),
    ).resolves.toBeUndefined();
  });
});
