import type { PageServerLoad } from './$types';
import { loadSources } from '$lib/provenance-loaders';

export const load: PageServerLoad = (event) => loadSources(event, 'game-format', event.params.slug);
