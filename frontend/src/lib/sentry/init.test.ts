import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Mock @sentry/sveltekit so the init code runs against spies instead of
// boot a real SDK. httpIntegration is exercised directly by the SSR test
// to pin the request-body suppression contract.
vi.mock('@sentry/sveltekit', () => ({
  init: vi.fn(),
  httpIntegration: vi.fn((opts) => ({ name: 'Http', options: opts })),
  handleErrorWithSentry: vi.fn(() => vi.fn()),
  sentryHandle: vi.fn(() => vi.fn()),
}));

// Default mocks for both env surfaces; each test overrides via vi.doMock.
vi.mock('$env/dynamic/private', () => ({ env: {} }));
vi.mock('$env/dynamic/public', () => ({ env: {} }));

describe('SSR Sentry init (instrumentation.server.ts)', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.doUnmock('$env/dynamic/private');
    vi.doUnmock('$env/dynamic/public');
  });

  it('does not call Sentry.init when PUBLIC_SENTRY_DSN is unset', async () => {
    vi.doMock('$env/dynamic/public', () => ({ env: {} }));
    vi.doMock('$env/dynamic/private', () => ({ env: {} }));
    const Sentry = await import('@sentry/sveltekit');
    await import('../../instrumentation.server');
    expect(Sentry.init).not.toHaveBeenCalled();
  });

  it('routes SSR events to the frontend DSN (PUBLIC_SENTRY_DSN), not the backend DSN', async () => {
    // Critical invariant: SSR is frontend code; its events must go to
    // flipcommons-frontend (PUBLIC_SENTRY_DSN), NOT flipcommons-backend
    // (SENTRY_DSN). Mocking both env surfaces with different values catches
    // any refactor that wires the wrong one.
    vi.doMock('$env/dynamic/public', () => ({
      env: { PUBLIC_SENTRY_DSN: 'https://frontend-project@sentry.example/2' },
    }));
    vi.doMock('$env/dynamic/private', () => ({
      env: {
        SENTRY_DSN: 'https://backend-project@sentry.example/1',
        RAILWAY_GIT_COMMIT_SHA: 'abc123',
      },
    }));
    const Sentry = await import('@sentry/sveltekit');
    await import('../../instrumentation.server');

    expect(Sentry.init).toHaveBeenCalledTimes(1);
    const initArgs = vi.mocked(Sentry.init).mock.calls[0][0]!;
    expect(initArgs.dsn).toBe('https://frontend-project@sentry.example/2');
    expect(initArgs.sendDefaultPii).toBe(false);
    expect(initArgs.tracesSampleRate).toBe(0);
    expect(initArgs.release).toBe('abc123');

    // Pins the request-body suppression contract — a refactor that drops
    // the option fails this test.
    expect(Sentry.httpIntegration).toHaveBeenCalledWith({ maxIncomingRequestBodySize: 'none' });
    expect(initArgs.integrations).toEqual([
      expect.objectContaining({ options: { maxIncomingRequestBodySize: 'none' } }),
    ]);
  });
});

describe('Browser Sentry init (hooks.client.ts)', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it('does not call Sentry.init when PUBLIC_SENTRY_DSN is empty', async () => {
    vi.doMock('$env/dynamic/public', () => ({ env: {} }));
    const Sentry = await import('@sentry/sveltekit');
    await import('../../hooks.client');
    expect(Sentry.init).not.toHaveBeenCalled();
  });

  it('calls Sentry.init when PUBLIC_SENTRY_DSN is set', async () => {
    vi.doMock('$env/dynamic/public', () => ({
      env: {
        PUBLIC_SENTRY_DSN: 'https://example@sentry.example/2',
        PUBLIC_RAILWAY_GIT_COMMIT_SHA: 'def456',
      },
    }));
    const Sentry = await import('@sentry/sveltekit');
    await import('../../hooks.client');

    expect(Sentry.init).toHaveBeenCalledTimes(1);
    const initArgs = vi.mocked(Sentry.init).mock.calls[0][0]!;
    expect(initArgs.dsn).toBe('https://example@sentry.example/2');
    expect(initArgs.release).toBe('def456');
    expect(initArgs.sendDefaultPii).toBe(false);
    expect(initArgs.tracesSampleRate).toBe(0);
    // No replay or feedback integrations.
    expect(initArgs.integrations).toBeUndefined();
  });
});
