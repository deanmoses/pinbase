/**
 * Client shim for the Title delete + undo flow.
 *
 * Kept separate from the Svelte page so it can be unit-tested without the
 * DOM, mirroring title-create.ts / model-create.ts.
 */

import client from '$lib/api/client';
import { parseApiError } from '$lib/components/editors/save-claims-shared';
import type { components } from '$lib/api/schema';
import type { EditCitationSelection } from '$lib/edit-citation';
import { buildEditCitationRequest } from '$lib/edit-citation';

export type DeletePreview = components['schemas']['TitleDeletePreviewSchema'];
export type DeleteResponse = components['schemas']['TitleDeleteResponseSchema'];
export type BlockingReferrer = components['schemas']['BlockingReferrerSchema'];

export type DeleteOutcome =
	| { kind: 'ok'; data: DeleteResponse }
	| { kind: 'rate_limited'; retryAfterSeconds: number; message: string }
	| { kind: 'blocked'; blockedBy: BlockingReferrer[]; message: string }
	| { kind: 'form_error'; message: string };

export async function submitDelete(
	slug: string,
	opts: { note?: string; citation?: EditCitationSelection | null } = {}
): Promise<DeleteOutcome> {
	const { data, error, response } = await client.POST('/api/titles/{slug}/delete/', {
		params: { path: { slug } },
		body: {
			note: opts.note ?? '',
			citation: buildEditCitationRequest(opts.citation ?? null)
		}
	});

	if (response.status === 429) {
		const retryAfter = Number(response.headers.get('Retry-After') ?? '86400');
		const hours = Math.max(1, Math.round(retryAfter / 3600));
		return {
			kind: 'rate_limited',
			retryAfterSeconds: retryAfter,
			message: `You've reached the delete limit. Try again in about ${hours} hour${hours === 1 ? '' : 's'}.`
		};
	}

	if (response.status === 422) {
		// 422 from the delete endpoint is either a structured error (same
		// shape as other 422s) or a delete-specific block with blocked_by.
		const body = (await response
			.clone()
			.json()
			.catch(() => null)) as { blocked_by?: BlockingReferrer[]; detail?: unknown } | null;
		if (body && Array.isArray(body.blocked_by)) {
			return {
				kind: 'blocked',
				blockedBy: body.blocked_by,
				message:
					typeof body.detail === 'string'
						? body.detail
						: 'Cannot delete: active references would be left dangling.'
			};
		}
	}

	if (error || !data) {
		const parsed = parseApiError(error);
		return { kind: 'form_error', message: parsed.message || 'Could not delete record.' };
	}

	return { kind: 'ok', data };
}

export type UndoOutcome =
	| { kind: 'ok'; changesetId: number }
	| { kind: 'superseded'; message: string }
	| { kind: 'form_error'; message: string };

export async function submitUndoDelete(changesetId: number, note = ''): Promise<UndoOutcome> {
	const { data, error, response } = await client.POST('/api/edit-history/undo-changeset/', {
		body: { changeset_id: changesetId, note }
	});

	if (response.status === 422) {
		// The most common 422 from undo is "not the latest action anymore".
		return {
			kind: 'superseded',
			message: "This delete is no longer the latest action — can't undo automatically."
		};
	}

	if (error || !data) {
		const parsed = parseApiError(error);
		return { kind: 'form_error', message: parsed.message || 'Undo failed.' };
	}

	const cs = (data as { changeset_id?: number }).changeset_id;
	return { kind: 'ok', changesetId: cs ?? changesetId };
}
