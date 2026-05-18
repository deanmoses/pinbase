import { error, redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { createServerClient } from '$lib/api/server';
import { requireCapability } from '$lib/require-capability.server';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url, request }) => {
  await requireCapability({ fetch, url, request, activity: 'catalog.create' });

  const parentSlug = url.searchParams.get('parent');
  if (!parentSlug) {
    throw redirect(302, resolve('/technology-generations'));
  }

  // Parent's display name comes from the parent list endpoint — the list
  // is tiny and already preloaded on navigation from the parent detail
  // page. A dedicated detail GET isn't worth adding for this.
  const client = createServerClient(fetch, url, request);
  const { data, response } = await client.GET('/api/technology-generations/');
  if (!data) {
    throw error(response.status || 500, 'Failed to load technology generations.');
  }
  const parent = data.find((p) => p.slug === parentSlug);
  if (!parent) {
    throw redirect(302, resolve('/technology-generations'));
  }

  return {
    initialName: url.searchParams.get('name') ?? '',
    parentSlug: parent.slug,
    parentName: parent.name,
  };
};
