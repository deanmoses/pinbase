import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { isSameDay, formatTime, smartDate, formatDate } from './dates';

// ── isSameDay ───────────────────────────────────────────────────

describe('isSameDay', () => {
  it('returns true for same date at different times', () => {
    const a = new Date(2025, 5, 15, 9, 0);
    const b = new Date(2025, 5, 15, 21, 45);
    expect(isSameDay(a, b)).toBe(true);
  });

  it('returns false for different days in same month', () => {
    const a = new Date(2025, 5, 15, 12, 0);
    const b = new Date(2025, 5, 16, 12, 0);
    expect(isSameDay(a, b)).toBe(false);
  });

  it('returns false for same day in different months', () => {
    const a = new Date(2025, 5, 15, 12, 0);
    const b = new Date(2025, 6, 15, 12, 0);
    expect(isSameDay(a, b)).toBe(false);
  });

  it('returns false for same month/day in different years', () => {
    const a = new Date(2025, 5, 15, 12, 0);
    const b = new Date(2026, 5, 15, 12, 0);
    expect(isSameDay(a, b)).toBe(false);
  });

  it('handles midnight boundary (11:59 PM vs 12:00 AM next day)', () => {
    const a = new Date(2025, 5, 15, 23, 59);
    const b = new Date(2025, 5, 16, 0, 0);
    expect(isSameDay(a, b)).toBe(false);
  });
});

// ── formatTime ──────────────────────────────────────────────────

describe('formatTime', () => {
  it('returns a lowercase string', () => {
    const result = formatTime(new Date(2025, 5, 15, 14, 30));
    expect(result).toBe(result.toLowerCase());
  });

  it('includes minutes when they are non-zero', () => {
    const result = formatTime(new Date(2025, 5, 15, 14, 30));
    expect(result).toMatch(/30/);
  });

  it('omits minutes when they are zero', () => {
    const result = formatTime(new Date(2025, 5, 15, 14, 0));
    // Should not contain :00 — the Intl formatter omits minutes
    expect(result).not.toMatch(/:00/);
  });
});

// ── smartDate ───────────────────────────────────────────────────

describe('smartDate', () => {
  // Fixed "now": Wednesday, June 18, 2025 at 3:00 PM
  const NOW = new Date(2025, 5, 18, 15, 0);

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows just the time for same day', () => {
    const result = smartDate(new Date(2025, 5, 18, 9, 30).toISOString());
    // Should contain the time digits but no day/date prefix
    expect(result).toMatch(/9/);
    expect(result).toMatch(/30/);
    expect(result).not.toMatch(/yesterday/i);
  });

  it('shows a relative label (not a date) for yesterday', () => {
    const result = smartDate(new Date(2025, 5, 17, 10, 0).toISOString());
    // Should NOT contain a month name, day number, or year — just a
    // locale-relative label ("Yesterday", "hier", "gestern", …) + time.
    expect(result).not.toMatch(/2025/);
    expect(result).not.toMatch(/17/);
    expect(result.length).toBeGreaterThan(0);
  });

  it('shows weekday abbreviation within 7 days', () => {
    // Saturday June 14 — 4 days before NOW (Wed June 18)
    const result = smartDate(new Date(2025, 5, 14, 10, 0).toISOString());
    expect(result).not.toMatch(/yesterday/i);
    expect(result.length).toBeGreaterThan(0);
    // Should not include year or month — just weekday + time
    expect(result).not.toMatch(/2025/);
    expect(result).not.toMatch(/jun/i);
  });

  it('shows month and day for same year beyond 7 days', () => {
    // March 10, 2025 — same year, more than 7 days ago
    const result = smartDate(new Date(2025, 2, 10, 14, 0).toISOString());
    // Should contain day number and not the year
    expect(result).toMatch(/10/);
    expect(result).not.toMatch(/2025/);
  });

  it('shows month, day, and year for different year', () => {
    const result = smartDate(new Date(2024, 11, 25, 9, 0).toISOString());
    // Should contain the year and the day
    expect(result).toMatch(/2024/);
    expect(result).toMatch(/25/);
  });

  it('returns empty string for empty input', () => {
    expect(smartDate('')).toBe('');
  });

  it('uses calendar days for the 7-day boundary, not elapsed time', () => {
    // June 12 at 11pm — 6 calendar days before NOW (June 18 3pm),
    // but more than 6*24h elapsed. Should still show weekday, not month+day.
    const result = smartDate(new Date(2025, 5, 12, 23, 0).toISOString());
    expect(result).not.toMatch(/jun/i);
    expect(result).not.toMatch(/2025/);
  });

  it('shows month+day at exactly 7 calendar days ago', () => {
    // June 11 — exactly 7 calendar days before June 18
    const result = smartDate(new Date(2025, 5, 11, 10, 0).toISOString());
    expect(result).toMatch(/11/);
    expect(result).not.toMatch(/2025/);
  });

  it('falls through to absolute date for future dates', () => {
    // July 20, 2025 — over a month in the future, same year
    const result = smartDate(new Date(2025, 6, 20, 14, 0).toISOString());
    expect(result).toMatch(/20/);
    expect(result).not.toMatch(/2025/);
  });

  it('falls through to full date for future dates in a different year', () => {
    const result = smartDate(new Date(2026, 0, 15, 10, 0).toISOString());
    expect(result).toMatch(/2026/);
    expect(result).toMatch(/15/);
  });
});

// ── formatDate ──────────────────────────────────────────────────

describe('formatDate', () => {
  it('includes day and year', () => {
    const result = formatDate(new Date(2024, 2, 10).toISOString());
    expect(result).toMatch(/10/);
    expect(result).toMatch(/2024/);
  });

  it('does not include a time component', () => {
    const result = formatDate(new Date(2024, 2, 10, 14, 30).toISOString());
    // Should not contain hour/minute indicators
    expect(result).not.toMatch(/[AP]M/i);
    expect(result).not.toMatch(/14/);
    expect(result).not.toMatch(/30/);
  });

  it('returns empty string for empty input', () => {
    expect(formatDate('')).toBe('');
  });
});
