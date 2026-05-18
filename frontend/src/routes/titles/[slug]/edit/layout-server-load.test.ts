import { describe, expect, it, vi } from 'vitest';

const requireCapability = vi.fn();

vi.mock('$lib/require-capability.server', () => ({
  requireCapability: (...args: unknown[]) => requireCapability(...args),
}));

const { load } = await import('./+layout.server');

describe('titles/[slug]/edit +layout.server load', () => {
  it('gates the route through requireCapability with catalog.edit', async () => {
    const fetchStub = (() => undefined) as unknown as typeof globalThis.fetch;
    const url = new URL('http://localhost/titles/foo/edit');
    const request = new Request(url);
    requireCapability.mockResolvedValueOnce(undefined);

    // The LayoutServerLoad event has many fields the helper doesn't use;
    // cast through unknown rather than stubbing the whole SvelteKit shape.
    await load({ fetch: fetchStub, url, request } as unknown as Parameters<typeof load>[0]);

    expect(requireCapability).toHaveBeenCalledWith({
      fetch: fetchStub,
      url,
      request,
      activity: 'catalog.edit',
    });
  });
});
