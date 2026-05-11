import { redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { createApiClient } from '$lib/api/client';
import type { Activity } from '$lib/api/schema';

interface RequireCapabilityOptions {
  fetch: typeof fetch;
  // Page URL from the load event. openapi-fetch constructs
  // `new Request(url, ...)` internally, and Node's Request rejects
  // relative URLs during SSR; passing `url.origin` as the client's
  // baseUrl makes the path resolve on both SSR and CSR.
  url: URL;
  activity: Activity;
}

// Redirect anonymous users to `/login` and authenticated-but-uncapable
// users to `/verify-email` before they fill out a form they cannot submit.
// The SPA auth gate is UX-only — the backend remains the source of truth.
export async function requireCapability({
  fetch,
  url,
  activity,
}: RequireCapabilityOptions): Promise<void> {
  const client = createApiClient(fetch, url.origin);
  const { data } = await client.GET('/api/auth/me/');
  // Fail-open if /api/auth/me/ itself errors: the SPA auth gate is UX-only,
  // and the backend will reject the actual submission anyway. Booting an
  // already-logged-in editor to /login on a transient /me/ blip would be
  // worse UX than letting them through to a real submit-time error.
  if (!data) return;
  if (!data.is_authenticated) {
    throw redirect(302, resolve('/login'));
  }
  if (data.capabilities?.[activity] !== true) {
    throw redirect(302, resolve('/verify-email'));
  }
}
