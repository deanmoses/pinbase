import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { sentrySvelteKit } from '@sentry/sveltekit';

// Mirror Railway's commit SHA into the PUBLIC_ namespace for the duration
// of this build, so any consumer using `$env/static/public` (e.g. inlined
// release tags) gets the same value the sourcemap upload below uses.
// hooks.client.ts intentionally reads `$env/dynamic/public` — that's a
// runtime lookup against the Node SSR process, not this build process,
// so the matching mirror for the browser/SSR runtime lives in
// scripts/start-production. ??= leaves an explicitly-set value alone.
process.env.PUBLIC_RAILWAY_GIT_COMMIT_SHA ??= process.env.RAILWAY_GIT_COMMIT_SHA;

export default defineConfig({
  plugins: [
    // sentrySvelteKit MUST come before sveltekit(), per Sentry docs.
    sentrySvelteKit({
      // Explicit upload gate: only attempt upload when all three secrets
      // are present (local dev, CI, no-secrets builds skip cleanly).
      // Makes the no-op behavior explicit instead of relying on plugin
      // internals to silently no-op when SENTRY_AUTH_TOKEN is missing.
      autoUploadSourceMaps:
        !!process.env.SENTRY_AUTH_TOKEN && !!process.env.SENTRY_ORG && !!process.env.SENTRY_PROJECT,
      telemetry: false,
      org: process.env.SENTRY_ORG,
      project: process.env.SENTRY_PROJECT,
      authToken: process.env.SENTRY_AUTH_TOKEN,
      release: { name: process.env.RAILWAY_GIT_COMMIT_SHA, inject: true },
      sourcemaps: {
        // Plugin doesn't delete maps by default. Delete after upload so
        // they don't ship to browsers.
        filesToDeleteAfterUpload: ['./.svelte-kit/**/*.map', './build/**/*.map'],
      },
    }),
    sveltekit(),
  ],
  server: {
    proxy: {
      '/api/': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/admin': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/media/': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/static/': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
