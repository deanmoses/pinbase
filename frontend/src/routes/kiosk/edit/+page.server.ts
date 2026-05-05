import { error } from '@sveltejs/kit';
import { createServerClient } from '$lib/api/server';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url, cookies }) => {
  const client = createServerClient(fetch, url);
  const { data, response } = await client.GET('/api/kiosk/configs/');
  if (!data) throw error(response?.status || 500, 'Failed to load kiosks');

  const rawId = cookies.get('kioskConfigId');
  const parsed = rawId ? Number(rawId) : NaN;
  const activeId = Number.isInteger(parsed) && parsed > 0 ? parsed : null;

  return { configs: data, activeId };
};
