import { requireCapability } from '$lib/require-capability';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
  await requireCapability({ fetch, url, activity: 'observability.debug' });
  if (url.searchParams.has('throw')) {
    throw new Error('sentry_test: SSR load throw');
  }
};
