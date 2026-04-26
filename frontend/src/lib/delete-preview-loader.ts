import { redirect } from '@sveltejs/kit';
import { resolve } from '$app/paths';

export interface DeletePreviewLoadOptions {
  fetch: typeof fetch;
  slug: string;
  apiPath: string;
  notFoundRedirect: string;
}

export async function loadDeletePreview<T>({
  fetch,
  slug,
  apiPath,
  notFoundRedirect,
}: DeletePreviewLoadOptions): Promise<{ preview: T; slug: string }> {
  // Fail-open if /api/auth/me/ itself errors: the SPA auth gate is UX-only,
  // and the backend will reject the actual delete submission anyway.
  const authRes = await fetch('/api/auth/me/');
  if (authRes.ok) {
    const data = (await authRes.json()) as { is_authenticated?: boolean };
    if (!data.is_authenticated) {
      throw redirect(302, resolve('/login'));
    }
  }

  const res = await fetch(`/api/${apiPath}/${slug}/delete-preview/`);
  if (res.status === 404) {
    throw redirect(302, notFoundRedirect);
  }
  if (!res.ok) {
    throw new Error(`Failed to load delete preview (${res.status})`);
  }

  const preview = (await res.json()) as T;
  return { preview, slug };
}
