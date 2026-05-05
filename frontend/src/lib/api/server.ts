/**
 * Server-side API client factory for SSR load functions.
 *
 * Resolves INTERNAL_API_BASE_URL (direct-to-Django in production) with a
 * fallback to the request origin (Vite proxy in dev). The incoming `request`
 * is required so the user's Cookie header is forwarded to Django: SvelteKit's
 * `event.fetch` only forwards cookies same-origin, and in production SSR
 * crosses origins to reach Django, so without this any auth-protected
 * endpoint would see an anonymous request.
 *
 * Usage in +page.server.ts / +layout.server.ts:
 *
 *   import { createServerClient } from '$lib/api/server';
 *
 *   export const load = async ({ fetch, url, request, params }) => {
 *       const client = createServerClient(fetch, url, request);
 *       ...
 *   };
 */
import { env } from '$env/dynamic/private';
import { createApiClient } from './client';

export function createServerClient(fetchImpl: typeof fetch, url: URL, request: Request) {
  const baseUrl = env.INTERNAL_API_BASE_URL?.trim() || url.origin;
  return createApiClient(fetchImpl, baseUrl, request);
}
