import { resolve } from '$app/paths';
import { loadDeletePreview } from '$lib/delete-preview-loader';
import type { components } from '$lib/api/schema';
import type { PageLoad } from './$types';

export type DeletePreview = components['schemas']['TaxonomyDeletePreviewSchema'];

export const load: PageLoad = ({ fetch, params }) =>
  loadDeletePreview<DeletePreview>({
    fetch,
    slug: params.slug,
    apiPath: 'manufacturers',
    notFoundRedirect: resolve('/manufacturers'),
  });
