import { requireCapability } from '$lib/require-capability';
import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async ({ fetch, url }) => {
  await requireCapability({ fetch, url, activity: 'catalog.edit' });
};
