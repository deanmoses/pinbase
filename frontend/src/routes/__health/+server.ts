import { json } from '@sveltejs/kit';
import { createServerClient } from '$lib/api/server';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch, url, request }) => {
  const client = createServerClient(fetch, url, request);
  const { data, response } = await client.GET('/api/health');

  if (!data || response.status !== 200) {
    return json({ status: 'error' }, { status: response.status || 500 });
  }

  return json(data);
};
