import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { NARROW_BREAKPOINT, WIDE_BREAKPOINT } from './src/lib/breakpoints.js';

// Inject @custom-media declarations into every component <style> block so
// postcss-custom-media (which sees each block in isolation) can resolve
// `(--breakpoint-*)` references. Kept on a single line so error line
// numbers in component <style> blocks aren't shifted by the injection.
const SHARED_CUSTOM_MEDIA =
  `@custom-media --breakpoint-narrow (max-width: ${NARROW_BREAKPOINT}rem);` +
  ` @custom-media --breakpoint-wide (min-width: ${WIDE_BREAKPOINT}rem); `;

const injectCustomMedia = {
  name: 'inject-custom-media',
  style: ({ content }) => ({ code: SHARED_CUSTOM_MEDIA + content }),
};

/** @type {import('@sveltejs/kit').Config} */
const config = {
  compilerOptions: {
    runes: true,
  },
  preprocess: [injectCustomMedia, vitePreprocess()],
  kit: {
    adapter: adapter(),
    version: {
      name: process.env.RAILWAY_GIT_COMMIT_SHA || 'dev',
      // Only poll when a real SHA is stamped (production builds). In dev the
      // version stays 'dev' forever, so polling would just be noise.
      pollInterval: process.env.RAILWAY_GIT_COMMIT_SHA ? 60 * 60 * 1000 : 0,
    },
    prerender: {
      origin: process.env.SITE_ORIGIN || 'http://localhost:5173',
      handleHttpError: ({ path, message }) => {
        // API endpoints are served by Django, not SvelteKit — ignore
        // them when the prerender crawler discovers <link rel="preload">
        // hints in prerendered pages.
        if (path.startsWith('/api/')) return;
        throw new Error(message);
      },
    },
  },
};

export default config;
