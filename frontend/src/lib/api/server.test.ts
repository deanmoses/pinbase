import { beforeEach, describe, expect, it, vi } from 'vitest';

// $env/dynamic/private is virtual under Vite/SvelteKit. We mock the
// module up-front so we can drive INTERNAL_API_BASE_URL per test.
const env: { INTERNAL_API_BASE_URL?: string } = {};
vi.mock('$env/dynamic/private', () => ({ env }));

const { createServerClient } = await import('./server');

beforeEach(() => {
  delete env.INTERNAL_API_BASE_URL;
});

describe('createServerClient — base URL selection', () => {
  // This is the gate that would have caught #420: a regression that
  // reverted to `url.origin` for SSR base URL would re-introduce the
  // bug (public origin unreachable from inside the container).
  it('uses INTERNAL_API_BASE_URL when set, NOT url.origin', async () => {
    env.INTERNAL_API_BASE_URL = 'http://127.0.0.1:8000';
    const fetch = vi
      .fn()
      .mockResolvedValue(new Response('{}', { headers: { 'Content-Type': 'application/json' } }));
    const url = new URL('https://flipcommons.org/series/new');
    const request = new Request(url);

    const client = createServerClient(fetch, url, request);
    await client.GET('/api/auth/me/');

    const req = fetch.mock.calls[0]?.[0] as Request;
    expect(req.url.startsWith('http://127.0.0.1:8000/')).toBe(true);
    expect(req.url.startsWith('https://flipcommons.org/')).toBe(false);
  });

  it('falls back to url.origin when INTERNAL_API_BASE_URL is unset (dev posture)', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(new Response('{}', { headers: { 'Content-Type': 'application/json' } }));
    const url = new URL('http://localhost:5173/series/new');
    const request = new Request(url);

    const client = createServerClient(fetch, url, request);
    await client.GET('/api/auth/me/');

    const req = fetch.mock.calls[0]?.[0] as Request;
    expect(req.url.startsWith('http://localhost:5173/')).toBe(true);
  });

  it('falls back to url.origin when INTERNAL_API_BASE_URL is blank/whitespace', async () => {
    env.INTERNAL_API_BASE_URL = '   ';
    const fetch = vi
      .fn()
      .mockResolvedValue(new Response('{}', { headers: { 'Content-Type': 'application/json' } }));
    const url = new URL('http://localhost:5173/series/new');
    const request = new Request(url);

    const client = createServerClient(fetch, url, request);
    await client.GET('/api/auth/me/');

    const req = fetch.mock.calls[0]?.[0] as Request;
    expect(req.url.startsWith('http://localhost:5173/')).toBe(true);
  });
});
