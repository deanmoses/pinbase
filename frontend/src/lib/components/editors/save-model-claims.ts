/**
 * Shared save helper for section editors that PATCH model claims.
 *
 * Each section editor builds a body with changed fields and/or
 * relationship data, then calls this function. It handles the API call,
 * error formatting, and page data invalidation.
 */

import { invalidateAll } from '$app/navigation';
import client from '$lib/api/client';
import type { components } from '$lib/api/schema';

type ModelClaimsBody = components['schemas']['ModelClaimPatchSchema'];

/**
 * Body keys that section editors may include in a PATCH.
 * `fields` and `note` default to `{}` and `''` respectively;
 * callers only supply keys they need.
 */
export type SectionPatchBody = Partial<
	Pick<
		ModelClaimsBody,
		| 'fields'
		| 'themes'
		| 'tags'
		| 'reward_types'
		| 'gameplay_features'
		| 'credits'
		| 'abbreviations'
		| 'note'
		| 'citation'
	>
>;

/** Metadata that the modal passes through to an editor's save(). */
export type SaveMeta = {
	note?: string;
	citation?: components['schemas']['EditCitationInput'];
};

export type FieldErrors = Record<string, string>;

export type SaveResult = { ok: true } | { ok: false; error: string; fieldErrors: FieldErrors };

type ParsedError = { message: string; fieldErrors: FieldErrors };

/**
 * Parse a backend error response into a human-readable message and
 * per-field error map.
 *
 * Handles three response shapes:
 * 1. Structured validation: `{ detail: { message, field_errors, form_errors } }`
 * 2. Legacy string: `{ detail: "message" }`
 * 3. Pydantic array: `{ detail: [{ loc, msg }] }`
 */
export function parseApiError(error: unknown): ParsedError {
	if (typeof error === 'object' && error !== null && 'detail' in error) {
		const { detail } = error as { detail: unknown };

		// New structured format from StructuredValidationError
		if (
			typeof detail === 'object' &&
			detail !== null &&
			'message' in detail &&
			'field_errors' in detail
		) {
			const d = detail as {
				message: string;
				field_errors: Record<string, string>;
				form_errors: string[];
			};
			const fieldErrors = d.field_errors ?? {};
			const formErrors = d.form_errors ?? [];

			// Build a message that is self-sufficient — makes sense even
			// without inline field-error display.  Consumers that show
			// inline errors can substitute a shorter prompt if they want.
			const parts = [...formErrors, ...Object.entries(fieldErrors).map(([k, v]) => `${k}: ${v}`)];
			const message = parts.length > 0 ? parts.join(' ') : d.message;

			return { message, fieldErrors };
		}

		// Legacy: plain string detail
		if (typeof detail === 'string') return { message: detail, fieldErrors: {} };

		// Pydantic validation: [{ loc: [...], msg: "..." }, ...]
		if (Array.isArray(detail)) {
			const fieldErrors: FieldErrors = {};
			const messages: string[] = [];
			for (const e of detail) {
				const loc = Array.isArray(e.loc) ? String(e.loc[e.loc.length - 1]) : '';
				const msg: string = e.msg ?? String(e);
				if (loc) {
					fieldErrors[loc] = msg;
					messages.push(`${loc}: ${msg}`);
				} else {
					messages.push(msg);
				}
			}
			return { message: messages.join('; '), fieldErrors };
		}
	}

	if (typeof error === 'string') return { message: error, fieldErrors: {} };
	return { message: JSON.stringify(error), fieldErrors: {} };
}

/**
 * PATCH model claims and invalidate page data.
 * Returns `{ ok: true }` on success, or `{ ok: false, error, fieldErrors }` on failure.
 */
export async function saveModelClaims(slug: string, body: SectionPatchBody): Promise<SaveResult> {
	const { error } = await client.PATCH('/api/models/{slug}/claims/', {
		params: { path: { slug } },
		body: { fields: {}, note: '', ...body }
	});

	if (error) {
		const parsed = parseApiError(error);
		return { ok: false, error: parsed.message, fieldErrors: parsed.fieldErrors };
	}

	await invalidateAll();
	return { ok: true };
}
