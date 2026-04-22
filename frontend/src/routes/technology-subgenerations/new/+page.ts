import { error, redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, url }) => {
  const authRes = await fetch('/api/auth/me/');
  if (authRes.ok) {
    const authData = (await authRes.json()) as { is_authenticated?: boolean };
    if (!authData.is_authenticated) {
      throw redirect(302, resolve('/login'));
    }
  }

  const parentSlug = url.searchParams.get('parent');
  if (!parentSlug) {
    throw redirect(302, resolve('/technology-generations'));
  }

  // Parent's display name is fetched via the parent list endpoint — the
  // list is tiny and already preloaded on navigation from the parent
  // detail page. A dedicated detail GET isn't worth adding for this.
  const listRes = await fetch('/api/technology-generations/');
  if (!listRes.ok) {
    throw error(listRes.status, 'Failed to load technology generations.');
  }
  const parents = (await listRes.json()) as { slug: string; name: string }[];
  const parent = parents.find((p) => p.slug === parentSlug);
  if (!parent) {
    throw redirect(302, resolve('/technology-generations'));
  }

  return {
    initialName: url.searchParams.get('name') ?? '',
    parentSlug: parent.slug,
    parentName: parent.name,
  };
};
