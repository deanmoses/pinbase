import type { PageServerLoad } from './$types';
import { loadSources } from '$lib/provenance-loaders';

export const load: PageServerLoad = (event) =>
	loadSources(event, 'technology-generation', event.params.slug);
