import type { PageServerLoad } from './$types';
import { loadSources } from '$lib/provenance-loaders';

export const load: PageServerLoad = (event) => loadSources(event, 'reward-type', event.params.slug);
