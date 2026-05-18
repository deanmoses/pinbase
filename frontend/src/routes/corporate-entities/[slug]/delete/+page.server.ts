import { resolve } from '$app/paths';
import { loadDeletePreview } from '$lib/delete-preview-loader.server';
import type { PageServerLoad } from './$types';

// The preview already carries `parent` because the CE registrar was wired
// with parent_field="manufacturer" — no separate detail fetch needed.
export const load: PageServerLoad = ({ fetch, params, url, request }) =>
  loadDeletePreview({
    fetch,
    url,
    request,
    public_id: params.slug,
    entity: 'corporate-entities',
    notFoundRedirect: resolve('/corporate-entities'),
  });
