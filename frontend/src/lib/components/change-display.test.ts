import { describe, expect, it } from 'vitest';
import { formatValue, isDiffable, isUnchanged, simplifyClaimValue } from './change-display';

describe('formatValue', () => {
  it('returns em-dash for null', () => {
    expect(formatValue(null)).toBe('\u2014');
  });

  it('returns em-dash for undefined', () => {
    expect(formatValue(undefined)).toBe('\u2014');
  });

  it('returns em-dash for empty string', () => {
    expect(formatValue('')).toBe('\u2014');
  });

  it('returns short strings verbatim', () => {
    expect(formatValue('hello')).toBe('hello');
  });

  it('truncates strings longer than 120 characters', () => {
    const long = 'a'.repeat(150);
    const result = formatValue(long);
    expect(result).toBe('a'.repeat(120) + '...');
    expect(result.length).toBe(123);
  });

  it('preserves strings of exactly 120 characters', () => {
    const exact = 'b'.repeat(120);
    expect(formatValue(exact)).toBe(exact);
  });

  it('JSON-serializes non-string values', () => {
    expect(formatValue(42)).toBe('42');
    expect(formatValue(true)).toBe('true');
    expect(formatValue({ key: 'val' })).toBe('{"key":"val"}');
  });

  it('truncates long JSON-serialized values', () => {
    const obj = { data: 'x'.repeat(200) };
    const result = formatValue(obj);
    expect(result.length).toBe(123);
    expect(result.endsWith('...')).toBe(true);
  });
});

describe('isDiffable', () => {
  it('returns true when old_value is a long string', () => {
    const change = {
      field_name: 'description',
      claim_key: 'k',
      old_value: 'a'.repeat(81),
      new_value: 'short',
    };
    expect(isDiffable(change)).toBe(true);
  });

  it('returns true when new_value is a long string', () => {
    const change = {
      field_name: 'description',
      claim_key: 'k',
      old_value: 'short',
      new_value: 'b'.repeat(81),
    };
    expect(isDiffable(change)).toBe(true);
  });

  it('returns false when both strings are short', () => {
    const change = {
      field_name: 'name',
      claim_key: 'k',
      old_value: 'short old',
      new_value: 'short new',
    };
    expect(isDiffable(change)).toBe(false);
  });

  it('returns false when old_value is null', () => {
    const change = {
      field_name: 'name',
      claim_key: 'k',
      old_value: null,
      new_value: 'a'.repeat(100),
    };
    expect(isDiffable(change)).toBe(false);
  });

  it('returns false when new_value is a number', () => {
    const change = {
      field_name: 'year',
      claim_key: 'k',
      old_value: 'a'.repeat(100),
      new_value: 1990,
    };
    expect(isDiffable(change)).toBe(false);
  });

  it('returns false at exactly the 80-character boundary', () => {
    const change = {
      field_name: 'desc',
      claim_key: 'k',
      old_value: 'a'.repeat(80),
      new_value: 'b'.repeat(80),
    };
    expect(isDiffable(change)).toBe(false);
  });

  it('returns true when one string is exactly 81 characters', () => {
    const change = {
      field_name: 'desc',
      claim_key: 'k',
      old_value: 'a'.repeat(81),
      new_value: 'short',
    };
    expect(isDiffable(change)).toBe(true);
  });
});

describe('isUnchanged', () => {
  it('is true when scalar values are equal', () => {
    expect(
      isUnchanged({
        field_name: 'tech',
        claim_key: 'k',
        old_value: 'solid-state',
        new_value: 'solid-state',
      }),
    ).toBe(true);
  });

  it('is false when scalar values differ', () => {
    expect(
      isUnchanged({
        field_name: 'tech',
        claim_key: 'k',
        old_value: 'electromechanical',
        new_value: 'solid-state',
      }),
    ).toBe(false);
  });

  it('is false when only one side is null', () => {
    expect(
      isUnchanged({
        field_name: 'tech',
        claim_key: 'k',
        old_value: null,
        new_value: 'solid-state',
      }),
    ).toBe(false);
  });

  it('is true when both sides are null (nothing asserted)', () => {
    expect(
      isUnchanged({
        field_name: 'tech',
        claim_key: 'k',
        old_value: null,
        new_value: null,
      }),
    ).toBe(true);
  });

  it('is true when arrays have the same contents', () => {
    expect(
      isUnchanged({
        field_name: 'aliases',
        claim_key: 'k',
        old_value: ['a', 'b'],
        new_value: ['a', 'b'],
      }),
    ).toBe(true);
  });
});

describe('simplifyClaimValue', () => {
  it('extracts a positive abbreviation claim', () => {
    expect(simplifyClaimValue({ value: 'DW', exists: true })).toEqual({
      display: 'DW',
      exists: true,
    });
  });

  it('extracts a negative abbreviation claim', () => {
    expect(simplifyClaimValue({ value: 'DW', exists: false })).toEqual({
      display: 'DW',
      exists: false,
    });
  });

  it('extracts an alias-style single-key claim regardless of key name', () => {
    expect(simplifyClaimValue({ alias_value: 'Doctor Who', exists: true })).toEqual({
      display: 'Doctor Who',
      exists: true,
    });
  });

  it('returns null for credit-style multi-key claims', () => {
    expect(simplifyClaimValue({ person: 1, role: 2, exists: true })).toBeNull();
  });

  it('returns null for FK-pk integer values (not human-readable)', () => {
    expect(simplifyClaimValue({ theme: 1, exists: true })).toBeNull();
  });

  it('returns null when exists is missing', () => {
    expect(simplifyClaimValue({ value: 'DW' })).toBeNull();
  });

  it('returns null for bare scalars', () => {
    expect(simplifyClaimValue('solid-state')).toBeNull();
    expect(simplifyClaimValue(42)).toBeNull();
    expect(simplifyClaimValue(null)).toBeNull();
  });

  it('returns null for arrays', () => {
    expect(simplifyClaimValue(['a', 'b'])).toBeNull();
  });

  it('returns null for retraction-only dicts (just exists:false)', () => {
    expect(simplifyClaimValue({ exists: false })).toBeNull();
  });
});
