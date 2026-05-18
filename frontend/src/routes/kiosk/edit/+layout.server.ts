import { redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { createServerClient } from '$lib/api/server';
import { loadAuthenticatedMe } from '$lib/api/load-me.server';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ fetch, url, request }) => {
  const client = createServerClient(fetch, url, request);
  const me = await loadAuthenticatedMe(client, 'kiosk/edit gate');
  if (!me.capabilities?.['kiosk.edit']) throw redirect(302, resolve('/'));
  return {};
};
