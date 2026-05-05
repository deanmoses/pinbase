import { beforeEach, describe, expect, it, vi } from 'vitest';

const { GET, createServerClient } = vi.hoisted(() => {
  const get = vi.fn();
  return {
    GET: get,
    createServerClient: vi.fn(() => ({ GET: get })),
  };
});

vi.mock('$lib/api/server', () => ({ createServerClient }));

import { load } from './+page.server';

function makeEvent(cookieMap: Record<string, string> = {}) {
  const url = new URL('http://localhost/kiosk/edit');
  const request = new Request(url, { headers: { cookie: 'sessionid=abc' } });
  return {
    fetch: globalThis.fetch,
    url,
    request,
    cookies: { get: (k: string) => cookieMap[k] },
  };
}

describe('/kiosk/edit/+page.server.ts load', () => {
  beforeEach(() => {
    GET.mockReset();
    createServerClient.mockClear();
  });

  it('forwards request to createServerClient so SSR sees the user session', async () => {
    GET.mockResolvedValue({ data: [], response: { status: 200 } });
    const event = makeEvent();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await load(event as any);
    expect(createServerClient).toHaveBeenCalledWith(event.fetch, event.url, event.request);
  });
});
