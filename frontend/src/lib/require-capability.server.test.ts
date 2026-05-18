import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const GET = vi.fn();
const createServerClient = vi.fn(() => ({ GET }));

vi.mock('$lib/api/server', () => ({ createServerClient }));

const { requireCapability } = await import('./require-capability.server');

function ok<T>(data: T, status = 200) {
  return { data, error: undefined, response: new Response(null, { status }) };
}

const fetchStub = (() => undefined) as unknown as typeof globalThis.fetch;
const url = new URL('http://localhost/titles/new');
const request = new Request('http://localhost/titles/new');

beforeEach(() => {
  GET.mockReset();
  createServerClient.mockClear();
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('requireCapability', () => {
  // #420: the gate must forward the incoming `request` to createServerClient
  // so the user's Cookie header reaches Django over the SSR-cross-origin call.
  // Dropping `request` re-introduces the silent anonymous-/me/ regression.
  it('forwards (fetch, url, request) to createServerClient', async () => {
    GET.mockResolvedValueOnce(
      ok({ is_authenticated: true, capabilities: { 'catalog.create': true } }),
    );

    await requireCapability({ fetch: fetchStub, url, request, activity: 'catalog.create' });

    expect(createServerClient).toHaveBeenCalledWith(fetchStub, url, request);
  });

  it('returns without throwing when the capability is granted', async () => {
    GET.mockResolvedValueOnce(
      ok({ is_authenticated: true, capabilities: { 'catalog.create': true } }),
    );

    await expect(
      requireCapability({ fetch: fetchStub, url, request, activity: 'catalog.create' }),
    ).resolves.toBeUndefined();
  });

  it('redirects authenticated-but-uncapable users to /verify-email', async () => {
    GET.mockResolvedValueOnce(
      ok({ is_authenticated: true, capabilities: { 'catalog.create': false } }),
    );

    await expect(
      requireCapability({ fetch: fetchStub, url, request, activity: 'catalog.create' }),
    ).rejects.toMatchObject({ status: 302, location: '/verify-email' });
  });

  it('redirects authenticated users with the capability key missing to /verify-email', async () => {
    GET.mockResolvedValueOnce(ok({ is_authenticated: true, capabilities: {} }));

    await expect(
      requireCapability({ fetch: fetchStub, url, request, activity: 'catalog.create' }),
    ).rejects.toMatchObject({ status: 302, location: '/verify-email' });
  });

  it('redirects anonymous users to /login (via shared auth helper)', async () => {
    GET.mockResolvedValueOnce(ok({ is_authenticated: false, capabilities: {} }));

    await expect(
      requireCapability({ fetch: fetchStub, url, request, activity: 'catalog.create' }),
    ).rejects.toMatchObject({ status: 302, location: '/login' });
  });
});
