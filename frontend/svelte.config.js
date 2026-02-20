import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	compilerOptions: {
		runes: true
	},
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: '200.html',
			precompress: false,
			strict: false
		}),
		prerender: {
			handleHttpError: ({ path, message }) => {
				// API endpoints are served by Django, not SvelteKit — ignore
				// them when the prerender crawler discovers <link rel="preload">
				// hints in prerendered pages.
				if (path.startsWith('/api/')) return;
				throw new Error(message);
			}
		}
	}
};

export default config;
