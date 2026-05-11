import { requireCapability } from '$lib/require-capability';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, url }) => {
  await requireCapability({ fetch, url, activity: 'catalog.create' });

  return {
    initialName: url.searchParams.get('name') ?? '',
  };
};
