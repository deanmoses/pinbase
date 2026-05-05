import { beforeEach, describe, expect, it, vi } from 'vitest';

const { GET, createServerClient } = vi.hoisted(() => {
  const get = vi.fn();
  return {
    GET: get,
    createServerClient: vi.fn(() => ({ GET: get })),
  };
});

vi.mock('$lib/api/server', () => ({ createServerClient }));
vi.mock('$app/paths', () => ({ resolve: (p: string) => p }));

import { load } from './+layout.server';

function makeEvent() {
  const url = new URL('http://localhost/kiosk/edit');
  const request = new Request(url, { headers: { cookie: 'sessionid=abc' } });
  return {
    fetch: globalThis.fetch,
    url,
    request,
  };
}

async function expectRedirectTo(target: string) {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await load(makeEvent() as any);
    throw new Error('expected redirect, got nothing thrown');
  } catch (e) {
    // SvelteKit's `redirect` helper throws an object with status + location.
    expect((e as { status: number }).status).toBe(302);
    expect((e as { location: string }).location).toBe(target);
  }
}

describe('/kiosk/edit auth gate', () => {
  beforeEach(() => {
    GET.mockReset();
    createServerClient.mockClear();
  });

  it('forwards the incoming request to createServerClient (cookie plumbing)', async () => {
    GET.mockResolvedValue({ data: { is_authenticated: true, is_superuser: true } });
    const event = makeEvent();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await load(event as any);
    expect(createServerClient).toHaveBeenCalledWith(event.fetch, event.url, event.request);
  });

  it('redirects anon to /login', async () => {
    GET.mockResolvedValue({ data: { is_authenticated: false } });
    await expectRedirectTo('/login');
  });

  it('redirects when /api/auth/me/ errors (fail-closed)', async () => {
    GET.mockResolvedValue({ data: undefined });
    await expectRedirectTo('/login');
  });

  it('redirects authed non-superuser to /', async () => {
    GET.mockResolvedValue({ data: { is_authenticated: true, is_superuser: false } });
    await expectRedirectTo('/');
  });

  it('lets superuser through', async () => {
    GET.mockResolvedValue({ data: { is_authenticated: true, is_superuser: true } });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await expect(load(makeEvent() as any)).resolves.toEqual({});
  });
});
