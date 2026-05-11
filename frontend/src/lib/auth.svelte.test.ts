// @vitest-environment jsdom
// jsdom is required so the auth store's `typeof window !== 'undefined'`
// guard runs the module-init `registerOnPolicyDenied(...)` registration —
// the behavior the first two tests pin.
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { GET, POST, registerOnPolicyDenied } = vi.hoisted(() => ({
  GET: vi.fn(),
  POST: vi.fn(),
  registerOnPolicyDenied: vi.fn(),
}));

vi.mock('$lib/api/client', () => ({
  default: { GET, POST },
  registerOnPolicyDenied,
}));

import { auth } from './auth.svelte';

describe('auth store', () => {
  beforeEach(() => {
    GET.mockReset();
    POST.mockReset();
    auth._resetForTest();
  });

  it('registers a 403-as-invalidation callback at module init', () => {
    // The auth store wires `auth.refresh()` into the client's policy-
    // denied hook at import time. If this assertion ever fails, the
    // browser-side 403 invalidation is silently disabled.
    expect(registerOnPolicyDenied).toHaveBeenCalledTimes(1);
    expect(registerOnPolicyDenied).toHaveBeenCalledWith(expect.any(Function));
  });

  it('the registered callback triggers auth.refresh()', async () => {
    const cb = registerOnPolicyDenied.mock.calls[0]?.[0] as () => void;
    expect(cb).toBeDefined();

    const callsBefore = GET.mock.calls.length;
    GET.mockResolvedValueOnce({
      data: { is_authenticated: true, capabilities: {} },
    });
    cb();
    await new Promise((r) => setTimeout(r, 0));
    expect(GET.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  describe('can()', () => {
    it('returns true only when the capability is literally true', async () => {
      GET.mockResolvedValueOnce({
        data: {
          is_authenticated: true,
          capabilities: { 'catalog.edit': true, 'kiosk.edit': false },
        },
      });
      await auth.refresh();

      expect(auth.can('catalog.edit')).toBe(true);
      expect(auth.can('kiosk.edit')).toBe(false);
    });

    it('default-denies missing keys', async () => {
      GET.mockResolvedValueOnce({
        data: { is_authenticated: true, capabilities: { 'catalog.edit': true } },
      });
      await auth.refresh();
      // `kiosk.edit` not present in the response — must default to false.
      expect(auth.can('kiosk.edit')).toBe(false);
    });
  });

  describe('refresh()', () => {
    it('re-fetches /me/ even when the store is already loaded', async () => {
      // First call populates the store and flips `loaded` to true.
      GET.mockResolvedValueOnce({
        data: { is_authenticated: true, capabilities: { 'catalog.edit': true } },
      });
      await auth.refresh();
      expect(auth.can('catalog.edit')).toBe(true);
      expect(auth.loaded).toBe(true);

      // Second call must still hit /me/ (unlike `load()`, which gates
      // on `loaded`) and replace the capability map.
      const beforeRefreshCalls = GET.mock.calls.length;
      GET.mockResolvedValueOnce({
        data: { is_authenticated: true, capabilities: { 'catalog.edit': false } },
      });
      await auth.refresh();

      expect(GET.mock.calls.length).toBeGreaterThan(beforeRefreshCalls);
      expect(auth.can('catalog.edit')).toBe(false);
    });

    it('de-dupes concurrent calls', async () => {
      let resolveGet: (v: { data: unknown }) => void = () => {};
      const pending = new Promise<{ data: unknown }>((r) => {
        resolveGet = r;
      });
      GET.mockReturnValueOnce(pending);

      const a = auth.refresh();
      const b = auth.refresh();
      const c = auth.refresh();

      // Only one network call until the in-flight promise resolves.
      expect(GET).toHaveBeenCalledTimes(1);

      resolveGet({
        data: { is_authenticated: true, capabilities: { 'catalog.edit': true } },
      });
      await Promise.all([a, b, c]);

      expect(GET).toHaveBeenCalledTimes(1);
    });
  });
});
