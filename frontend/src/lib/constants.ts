export const SITE_NAME = 'Flipcommons';

/**
 * Long form used in browser tab titles and the home page <title>. Body copy,
 * nav, and og:site_name use SITE_NAME instead.
 */
export const SITE_TITLE = 'Flipcommons Pinball Encyclopedia';

/**
 * Breakpoint (in rem) where the layout switches from single-column (mobile)
 * to two-column (desktop). CSS media queries can't use JS constants, so
 * TwoColumnLayout.svelte and layout files duplicate this as `52rem` —
 * search for "LAYOUT_BREAKPOINT" to find all copies.
 */
export const LAYOUT_BREAKPOINT = 52;

/** Build a browser tab title like "Manufacturers — Flipcommons Pinball Encyclopedia". */
export const pageTitle = (name: string) => `${name} — ${SITE_TITLE}`;
