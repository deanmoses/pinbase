import type { PageServerLoad } from './$types';
import { loadSources } from '$lib/provenance-loaders';

export const load: PageServerLoad = (event) =>
	loadSources(event, 'technology-subgeneration', event.params.slug);
