import { beforeEach, describe, expect, it } from 'vitest';
import {
  clearKioskCookies,
  getKioskConfigIdFromCookie,
  getKioskIdleSecondsFromCookie,
  isKioskCookieSet,
  setKioskCookies,
} from './config';

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

  it('isKioskCookieSet returns false when not set', () => {
    expect(isKioskCookieSet()).toBe(false);
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
