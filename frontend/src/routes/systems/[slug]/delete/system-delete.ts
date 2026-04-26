import { createDeleteSubmitter } from '$lib/delete-flow';
import type { components } from '$lib/api/schema';

export type DeleteResponse = components['schemas']['DeleteResponseSchema'];

export const submitDelete = createDeleteSubmitter<DeleteResponse>('/api/systems/{slug}/delete/');
