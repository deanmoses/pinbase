import { resolve } from '$app/paths';

/** Wrapper around resolve() that accepts a plain string (for dynamic URLs). */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const resolveHref = (url: string) => resolve(url as any);

/** Format a year_start / year_end pair as a human-readable range. */
export function formatYearRange(yearStart?: number | null, yearEnd?: number | null): string | null {
	if (yearStart && yearEnd) return `${yearStart}\u2013${yearEnd}`;
	if (yearStart) return `${yearStart}\u2013present`;
	if (yearEnd) return `\u2013${yearEnd}`;
	return null;
}
