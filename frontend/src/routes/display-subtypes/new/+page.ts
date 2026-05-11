import { error, redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import { requireCapability } from '$lib/require-capability';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, url }) => {
  await requireCapability({ fetch, url, activity: 'catalog.create' });

  const parentSlug = url.searchParams.get('parent');
  if (!parentSlug) {
    throw redirect(302, resolve('/display-types'));
  }

  const listRes = await fetch('/api/display-types/');
  if (!listRes.ok) {
    throw error(listRes.status, 'Failed to load display types.');
  }
  const parents = (await listRes.json()) as { slug: string; name: string }[];
  const parent = parents.find((p) => p.slug === parentSlug);
  if (!parent) {
    throw redirect(302, resolve('/display-types'));
  }

  return {
    initialName: url.searchParams.get('name') ?? '',
    parentSlug: parent.slug,
    parentName: parent.name,
  };
};
