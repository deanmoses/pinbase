import { error, redirect } from '@sveltejs/kit';
import { createServerClient } from '$lib/api/server';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url, request }) => {
  const client = createServerClient(fetch, url, request);
  const { data, response } = await client.GET('/api/auth/signup/pending/');

  if (!data) {
    if (response?.status === 401) throw redirect(302, '/login?next=/signup');
    throw error(response?.status || 500, 'Failed to load signup page');
  }

  return { pending: data };
};
