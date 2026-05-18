import { requireCapability } from '$lib/require-capability.server';
import type { LayoutServerLoad } from './$types';

export const ssr = false;

export const load: LayoutServerLoad = async ({ fetch, url, request }) => {
  await requireCapability({ fetch, url, request, activity: 'catalog.edit' });
};
