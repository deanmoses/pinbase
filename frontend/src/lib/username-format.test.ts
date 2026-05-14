import { describe, expect, it } from 'vitest';
import { checkUsernameFormat } from './username-format';

describe('checkUsernameFormat', () => {
  it('accepts a simple valid username', () => {
    expect(checkUsernameFormat('alice')).toBeNull();
  });

  it('accepts hyphenated usernames', () => {
    expect(checkUsernameFormat('al-ice')).toBeNull();
  });

  it('accepts digits', () => {
    expect(checkUsernameFormat('alice42')).toBeNull();
  });

  it('does NOT pre-check too-short — that is an in-progress state, not a mistake', () => {
    // The server still rejects too-short on submit; the page suppresses the
    // /check call below USERNAME_MIN_LEN so the user only sees the message
    // when they Continue.
    expect(checkUsernameFormat('al')).toBeNull();
  });

  it('rejects too long', () => {
    expect(checkUsernameFormat('a'.repeat(21))).toBe('too_long');
  });

  it('rejects uppercase', () => {
    expect(checkUsernameFormat('Alice')).toBe('bad_charset');
  });

  it('rejects underscore', () => {
    expect(checkUsernameFormat('al_ice')).toBe('bad_charset');
  });

  it('rejects leading hyphen', () => {
    expect(checkUsernameFormat('-alice')).toBe('leading_or_trailing_hyphen');
  });

  it('rejects trailing hyphen', () => {
    expect(checkUsernameFormat('alice-')).toBe('leading_or_trailing_hyphen');
  });

  it('rejects consecutive hyphens', () => {
    expect(checkUsernameFormat('al--ice')).toBe('consecutive_hyphens');
  });
});
