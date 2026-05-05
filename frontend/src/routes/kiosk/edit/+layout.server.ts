import { redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { createServerClient } from '$lib/api/server';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ fetch, url }) => {
  const client = createServerClient(fetch, url);
  const { data } = await client.GET('/api/auth/me/');

  if (!data?.is_authenticated) throw redirect(302, resolve('/login'));
  if (!data.is_superuser) throw redirect(302, resolve('/'));

  return {};
};
