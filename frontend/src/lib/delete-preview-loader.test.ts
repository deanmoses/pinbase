import { describe, expect, it, vi } from 'vitest';
import { loadDeletePreview } from './delete-preview-loader';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function authedFetch(previewResponse: Response): typeof globalThis.fetch {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    if (url.endsWith('/api/auth/me/')) {
      return jsonResponse({ is_authenticated: true });
    }
    return previewResponse;
  }) as unknown as typeof globalThis.fetch;
}

describe('loadDeletePreview', () => {
  it('returns the preview body and slug on success', async () => {
    const preview = { name: 'Theme', changeset_count: 3 };
    const result = await loadDeletePreview<typeof preview>({
      fetch: authedFetch(jsonResponse(preview)),
      slug: 'cosmic',
      apiPath: 'themes',
      notFoundRedirect: '/themes',
    });

    expect(result).toEqual({ preview, slug: 'cosmic' });
  });

  it('redirects anonymous users to /login', async () => {
    const fetch = vi.fn(async () =>
      jsonResponse({ is_authenticated: false }),
    ) as unknown as typeof globalThis.fetch;

    await expect(
      loadDeletePreview({
        fetch,
        slug: 'cosmic',
        apiPath: 'themes',
        notFoundRedirect: '/themes',
      }),
    ).rejects.toMatchObject({ status: 302, location: '/login' });
  });

  it('redirects to the fallback URL on 404', async () => {
    await expect(
      loadDeletePreview({
        fetch: authedFetch(new Response(null, { status: 404 })),
        slug: 'missing',
        apiPath: 'themes',
        notFoundRedirect: '/themes',
      }),
    ).rejects.toMatchObject({ status: 302, location: '/themes' });
  });

  it('throws on other non-OK responses', async () => {
    await expect(
      loadDeletePreview({
        fetch: authedFetch(new Response(null, { status: 500 })),
        slug: 'cosmic',
        apiPath: 'themes',
        notFoundRedirect: '/themes',
      }),
    ).rejects.toThrow(/500/);
  });
});
