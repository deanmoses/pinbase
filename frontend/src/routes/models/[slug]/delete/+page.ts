import { resolve } from '$app/paths';
import { loadDeletePreview } from '$lib/delete-preview-loader';
import type { components } from '$lib/api/schema';
import type { PageLoad } from './$types';

export type DeletePreview = components['schemas']['ModelDeletePreviewSchema'];

export const load: PageLoad = ({ fetch, params }) =>
  loadDeletePreview<DeletePreview>({
    fetch,
    slug: params.slug,
    apiPath: 'models',
    notFoundRedirect: resolve('/'),
  });
