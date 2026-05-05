import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  clearConfig,
  clearKioskCookie,
  clearKioskCookies,
  DEFAULT_IDLE_SECONDS,
  DEFAULT_TITLE,
  getKioskConfigIdFromCookie,
  getKioskIdleSecondsFromCookie,
  isKioskCookieSet,
  loadConfig,
  saveConfig,
  setKioskCookie,
  setKioskCookies,
} from './config';

beforeAll(() => {
  // Node 22+ ships an experimental webstorage that lacks a usable in-memory
  // backing in vitest; swap in a Map-backed Storage for tests.
  const store = new Map<string, string>();
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => store.set(k, String(v)),
    removeItem: (k: string) => store.delete(k),
    clear: () => store.clear(),
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    get length() {
      return store.size;
    },
  } satisfies Storage);
});

describe('kiosk config (localStorage)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns null when nothing is stored', () => {
    expect(loadConfig()).toBeNull();
  });

  it('round-trips a saved config', () => {
    const config = {
      title: 'Test Title',
      idleSeconds: 60,
      items: [{ titleSlug: 'gorgar', hook: 'Talks' }],
    };
    saveConfig(config);
    expect(loadConfig()).toEqual(config);
  });

  it('clearConfig empties storage', () => {
    saveConfig({ title: 'x', idleSeconds: 30, items: [] });
    clearConfig();
    expect(loadConfig()).toBeNull();
  });

  it('falls back to defaults for malformed fields', () => {
    localStorage.setItem(
      'kioskConfig',
      JSON.stringify({ title: 123, idleSeconds: -5, items: 'nope' }),
    );
    expect(loadConfig()).toEqual({
      title: DEFAULT_TITLE,
      idleSeconds: DEFAULT_IDLE_SECONDS,
      items: [],
    });
  });

  it('drops malformed items but keeps valid ones', () => {
    localStorage.setItem(
      'kioskConfig',
      JSON.stringify({
        title: 'T',
        idleSeconds: 30,
        items: [
          { titleSlug: 'a', hook: 'h' },
          null,
          { titleSlug: 'b' },
          { titleSlug: 'c', hook: 'k' },
        ],
      }),
    );
    expect(loadConfig()?.items).toEqual([
      { titleSlug: 'a', hook: 'h' },
      { titleSlug: 'c', hook: 'k' },
    ]);
  });

  it('returns null on parse error', () => {
    localStorage.setItem('kioskConfig', '{not json');
    expect(loadConfig()).toBeNull();
  });
});

describe('kiosk cookie', () => {
  beforeEach(() => {
    clearKioskCookies();
  });

  it('setKioskCookie sets mode=kiosk', () => {
    setKioskCookie();
    expect(document.cookie).toContain('mode=kiosk');
    expect(isKioskCookieSet()).toBe(true);
  });

  it('clearKioskCookie removes the cookie', () => {
    setKioskCookie();
    clearKioskCookie();
    expect(isKioskCookieSet()).toBe(false);
  });

  it('isKioskCookieSet returns false when not set', () => {
    expect(isKioskCookieSet()).toBe(false);
  });
});

describe('kiosk cookies (mode + kioskConfigId + kioskIdleSeconds)', () => {
  beforeEach(() => {
    clearKioskCookies();
  });

  it('setKioskCookies sets all three cookies', () => {
    setKioskCookies(42, 90);
    expect(document.cookie).toContain('mode=kiosk');
    expect(document.cookie).toContain('kioskConfigId=42');
    expect(document.cookie).toContain('kioskIdleSeconds=90');
    expect(isKioskCookieSet()).toBe(true);
    expect(getKioskConfigIdFromCookie()).toBe(42);
    expect(getKioskIdleSecondsFromCookie()).toBe(90);
  });

  it('clearKioskCookies removes all three cookies', () => {
    setKioskCookies(7, 60);
    clearKioskCookies();
    expect(isKioskCookieSet()).toBe(false);
    expect(getKioskConfigIdFromCookie()).toBeNull();
    expect(getKioskIdleSecondsFromCookie()).toBeNull();
  });

  it('getKioskConfigIdFromCookie returns null when absent', () => {
    expect(getKioskConfigIdFromCookie()).toBeNull();
  });

  it('getKioskConfigIdFromCookie returns null for malformed values', () => {
    document.cookie = 'kioskConfigId=not-a-number; Path=/';
    expect(getKioskConfigIdFromCookie()).toBeNull();
    document.cookie = 'kioskConfigId=; Path=/; Max-Age=0';
    document.cookie = 'kioskConfigId=-3; Path=/';
    expect(getKioskConfigIdFromCookie()).toBeNull();
  });

  it('getKioskIdleSecondsFromCookie returns null when absent or malformed', () => {
    expect(getKioskIdleSecondsFromCookie()).toBeNull();
    document.cookie = 'kioskIdleSeconds=nope; Path=/';
    expect(getKioskIdleSecondsFromCookie()).toBeNull();
    document.cookie = 'kioskIdleSeconds=0; Path=/';
    expect(getKioskIdleSecondsFromCookie()).toBeNull();
  });
});
