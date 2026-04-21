import type { PageServerLoad } from './$types';
import { loadEditHistory } from '$lib/provenance-loaders';

export const load: PageServerLoad = (event) => loadEditHistory(event, 'system', event.params.slug);
