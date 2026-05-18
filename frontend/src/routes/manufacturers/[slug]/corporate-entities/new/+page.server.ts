import { error } from '@sveltejs/kit';
import { createServerClient } from '$lib/api/server';
import { requireCapability } from '$lib/require-capability.server';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, url, request }) => {
  await requireCapability({ fetch, url, request, activity: 'catalog.create' });

  // Load the parent manufacturer directly — this page escapes the parent
  // layout via `+page@.svelte`, so parent-layout data is not inherited.
  const apiClient = createServerClient(fetch, url, request);
  const { data, response } = await apiClient.GET('/api/pages/manufacturer/{public_id}', {
    params: { path: { public_id: params.slug } },
  });
  if (!data) {
    if (response?.status === 404) throw error(404, 'Manufacturer not found');
    throw error(response.status || 500, 'Failed to load manufacturer');
  }

  return {
    manufacturer: { name: data.name, slug: data.slug },
    initialName: url.searchParams.get('name') ?? '',
  };
};
