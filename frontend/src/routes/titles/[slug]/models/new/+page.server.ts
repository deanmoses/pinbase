import { error } from '@sveltejs/kit';
import { createServerClient } from '$lib/api/server';
import { requireCapability } from '$lib/require-capability.server';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, url, request }) => {
  await requireCapability({ fetch, url, request, activity: 'catalog.create' });

  // Load the parent title so the heading renders the real name ("Pokémon"
  // rather than the ASCII slug "pokemon"). We fetch directly here rather
  // than inheriting from the parent `[slug]/+layout.server.ts` because this
  // page escapes the parent layout via `+page@.svelte` — SvelteKit does not
  // inherit parent-layout data through a layout reset.
  const apiClient = createServerClient(fetch, url, request);
  const { data, response } = await apiClient.GET('/api/pages/title/{public_id}', {
    params: { path: { public_id: params.slug } },
  });
  if (!data) {
    if (response?.status === 404) throw error(404, 'Title not found');
    throw error(response.status || 500, 'Failed to load title');
  }
  return { title: { name: data.name, slug: data.slug } };
};
