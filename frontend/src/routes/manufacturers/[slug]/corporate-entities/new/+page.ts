import { error } from '@sveltejs/kit';
import client from '$lib/api/client';
import { requireCapability } from '$lib/require-capability';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params, url }) => {
  await requireCapability({ fetch, url, activity: 'catalog.create' });

  // Load the parent manufacturer directly — this page escapes the parent
  // layout via `+page@.svelte`, so parent-layout data is not inherited.
  const { data, response } = await client.GET('/api/pages/manufacturer/{public_id}', {
    fetch,
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
