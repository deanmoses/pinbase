import { error } from '@sveltejs/kit';
import client from '$lib/api/client';
import { requireCapability } from '$lib/require-capability';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params, url }) => {
  await requireCapability({ fetch, url, activity: 'catalog.create' });

  // Load the parent title so the heading renders the real name ("Pokémon"
  // rather than the ASCII slug "pokemon"). We fetch directly here rather
  // than inheriting from the parent `[slug]/+layout.server.ts` because this
  // page escapes the parent layout via `+page@.svelte` — SvelteKit does not
  // inherit parent-layout data through a layout reset.
  const { data, response } = await client.GET('/api/pages/title/{public_id}', {
    fetch,
    params: { path: { public_id: params.slug } },
  });
  if (!data) {
    if (response?.status === 404) throw error(404, 'Title not found');
    throw error(response.status || 500, 'Failed to load title');
  }
  return { title: { name: data.name, slug: data.slug } };
};
