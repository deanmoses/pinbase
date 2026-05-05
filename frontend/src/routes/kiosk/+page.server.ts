import { createServerClient } from '$lib/api/server';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url, cookies }) => {
  if (cookies.get('mode') !== 'kiosk') return { kioskConfig: null };

  const rawId = cookies.get('kioskConfigId');
  const id = rawId ? Number(rawId) : NaN;
  if (!Number.isInteger(id) || id <= 0) return { kioskConfig: null };

  const client = createServerClient(fetch, url);
  const { data, response } = await client.GET('/api/pages/kiosk/{config_id}/', {
    params: { path: { config_id: id } },
  });
  // The page endpoint declares only 200 in OpenAPI, so openapi-fetch's typed
  // `error` slot is never populated for a 404. Use response.status instead.
  return { kioskConfig: response.status === 404 ? null : (data ?? null) };
};
