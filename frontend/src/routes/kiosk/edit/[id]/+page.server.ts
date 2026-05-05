import { error } from '@sveltejs/kit';
import { createServerClient } from '$lib/api/server';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url, request, params }) => {
  const id = Number(params.id);
  if (!Number.isInteger(id) || id <= 0) throw error(404, 'Kiosk not found');

  const client = createServerClient(fetch, url, request);
  const { data, response } = await client.GET('/api/kiosk/configs/{config_id}/', {
    params: { path: { config_id: id } },
  });

  if (!data) {
    if (response?.status === 404) throw error(404, 'Kiosk not found');
    throw error(response?.status || 500, 'Failed to load kiosk');
  }

  return { config: data };
};
