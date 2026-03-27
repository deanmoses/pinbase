import { describe, it, expect } from 'vitest';
import { formatYearRange } from './utils';

describe('formatYearRange', () => {
	it('returns range when both years present', () => {
		expect(formatYearRange(1927, 1983)).toBe('1927\u20131983');
	});

	it('returns open-ended range when only start', () => {
		expect(formatYearRange(1999, null)).toBe('1999\u2013present');
	});

	it('returns leading dash when only end', () => {
		expect(formatYearRange(null, 1950)).toBe('\u20131950');
	});

	it('returns null when neither year present', () => {
		expect(formatYearRange(null, null)).toBeNull();
		expect(formatYearRange(undefined, undefined)).toBeNull();
	});
});
