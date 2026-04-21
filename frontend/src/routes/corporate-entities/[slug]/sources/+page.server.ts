import type { PageServerLoad } from './$types';
import { loadSources } from '$lib/provenance-loaders';

export const load: PageServerLoad = (event) =>
	loadSources(event, 'corporate-entity', event.params.slug);
