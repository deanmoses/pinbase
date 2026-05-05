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

type Cookies = { get: (name: string) => string | undefined };

function makeEvent(cookieMap: Record<string, string>) {
  const cookies: Cookies = { get: (k) => cookieMap[k] };
  return {
    fetch: globalThis.fetch,
    url: new URL('http://localhost/kiosk'),
    cookies,
  };
}

describe('/kiosk/+page.server.ts load', () => {
  beforeEach(() => {
    GET.mockReset();
  });

  it('returns kioskConfig: null when mode cookie is not set', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result = await load(makeEvent({}) as any);
    expect(result).toEqual({ kioskConfig: null });
    expect(GET).not.toHaveBeenCalled();
  });

  it('returns kioskConfig: null when kioskConfigId cookie is missing or malformed', async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const r1 = await load(makeEvent({ mode: 'kiosk' }) as any);
    expect(r1).toEqual({ kioskConfig: null });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const r2 = await load(makeEvent({ mode: 'kiosk', kioskConfigId: 'nope' }) as any);
    expect(r2).toEqual({ kioskConfig: null });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const r3 = await load(makeEvent({ mode: 'kiosk', kioskConfigId: '-3' }) as any);
    expect(r3).toEqual({ kioskConfig: null });
    expect(GET).not.toHaveBeenCalled();
  });

  it('fetches the page model and returns it on 200', async () => {
    const pageModel = { id: 5, name: 'L', page_heading: '', idle_seconds: 60, items: [] };
    GET.mockResolvedValue({ data: pageModel, response: { status: 200 } });

    const result = await load(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      makeEvent({ mode: 'kiosk', kioskConfigId: '5' }) as any,
    );
    expect(GET).toHaveBeenCalledWith('/api/pages/kiosk/{config_id}/', {
      params: { path: { config_id: 5 } },
    });
    expect(result).toEqual({ kioskConfig: pageModel });
  });

  it('maps a 404 response to kioskConfig: null', async () => {
    GET.mockResolvedValue({ data: undefined, response: { status: 404 } });

    const result = await load(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      makeEvent({ mode: 'kiosk', kioskConfigId: '99' }) as any,
    );
    expect(result).toEqual({ kioskConfig: null });
  });
});
