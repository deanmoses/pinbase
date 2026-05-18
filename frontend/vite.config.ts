import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { sentrySvelteKit } from '@sentry/sveltekit';

// Mirror the Railway-injected commit SHA into the `PUBLIC_` namespace so the
// browser bundle gets the same release tag SvelteKit's server and the
// sourcemap upload below use. Single source of truth → the SHA Sentry stamps
// on browser events, the SHA tagged on the uploaded sourcemap bundle, and
// the SHA the SSR bundle reports are guaranteed equal by construction.
// ??= leaves an explicitly-set value (e.g. local override) alone.
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
