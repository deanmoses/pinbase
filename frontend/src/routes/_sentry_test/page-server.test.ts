import { beforeEach, describe, expect, it, vi } from 'vitest';

const requireCapability = vi.fn();

vi.mock('$lib/require-capability', () => ({
  requireCapability: (...args: unknown[]) => requireCapability(...args),
}));

const { load } = await import('./+page.server');

function makeEvent(url: URL) {
  const fetchStub = (() => undefined) as unknown as typeof globalThis.fetch;
  return { fetch: fetchStub, url };
}

describe('_sentry_test +page.server.ts load', () => {
  beforeEach(() => {
    requireCapability.mockReset();
  });

  it('gates the route through requireCapability with observability.debug', async () => {
    requireCapability.mockResolvedValueOnce(undefined);
    const event = makeEvent(new URL('http://localhost/_sentry_test'));

    await load(event as unknown as Parameters<typeof load>[0]);

    expect(requireCapability).toHaveBeenCalledWith({
      fetch: event.fetch,
      url: event.url,
      activity: 'observability.debug',
    });
  });

  it('returns without throwing for an authorized request with no ?throw', async () => {
    requireCapability.mockResolvedValueOnce(undefined);
    const event = makeEvent(new URL('http://localhost/_sentry_test'));

    await expect(load(event as unknown as Parameters<typeof load>[0])).resolves.toBeUndefined();
  });

  it('throws for an authorized request with a ?throw key (any value)', async () => {
    requireCapability.mockResolvedValueOnce(undefined);
    const event = makeEvent(new URL('http://localhost/_sentry_test?throw'));

    await expect(load(event as unknown as Parameters<typeof load>[0])).rejects.toThrow(
      'sentry_test: SSR load throw',
    );
  });
});
