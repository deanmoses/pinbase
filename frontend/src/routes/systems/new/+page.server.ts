import { requireCapability } from '$lib/require-capability.server';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url, request }) => {
  await requireCapability({ fetch, url, request, activity: 'catalog.create' });

  return {
    initialName: url.searchParams.get('name') ?? '',
  };
};
