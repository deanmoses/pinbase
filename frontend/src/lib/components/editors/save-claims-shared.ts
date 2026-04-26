/**
 * Shared types and helpers used by claims save flows.
 */

import { invalidateAll } from '$app/navigation';
import client from '$lib/api/client';
import type { components, paths } from '$lib/api/schema';

/** Metadata that the modal passes through to an editor's save(). */
export type SaveMeta = {
  note?: string;
  citation?: components['schemas']['EditCitationInput'];
};

export type FieldErrors = Record<string, string>;

export type SaveResult =
  | { ok: true; updatedSlug?: string }
  | { ok: false; error: string; fieldErrors: FieldErrors };

type ClaimsBody = components['schemas']['ClaimPatchSchema'];

export type SimpleTaxonomySectionPatchBody = Partial<
  Pick<ClaimsBody, 'fields' | 'note' | 'citation'>
>;

/**
 * Any OpenAPI path whose PATCH operation accepts the flat `ClaimPatchSchema`
 * body and identifies the resource by `slug`. Derived from the schema, so new
 * simple-taxonomy endpoints qualify automatically; hierarchical and
 * entity-specific endpoints (which use richer body schemas) do not.
 */
export type SimpleTaxonomyClaimsPath = {
  [K in keyof paths]: paths[K] extends {
    patch: {
      parameters: { path: { slug: string } };
      requestBody: { content: { 'application/json': ClaimsBody } };
    };
  }
    ? K
    : never;
}[keyof paths];

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

      const parts = [...formErrors, ...Object.entries(fieldErrors).map(([k, v]) => `${k}: ${v}`)];
      const message = parts.length > 0 ? parts.join(' ') : d.message;

      return { message, fieldErrors };
    }

    if (typeof detail === 'string') return { message: detail, fieldErrors: {} };

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
 * Save handler for any simple-taxonomy claims endpoint. Callers supply the
 * literal API path so the typed openapi-fetch client can validate it; the body
 * is the flat `ClaimPatchSchema` shape (`fields` / `note` / `citation`).
 */
export async function saveSimpleTaxonomyClaims(
  path: SimpleTaxonomyClaimsPath,
  slug: string,
  body: SimpleTaxonomySectionPatchBody,
): Promise<SaveResult> {
  const { data, error } = await client.PATCH(path, {
    params: { path: { slug } },
    body: { fields: {}, note: '', ...body },
  });

  if (error) {
    const parsed = parseApiError(error);
    return { ok: false, error: parsed.message, fieldErrors: parsed.fieldErrors };
  }

  await invalidateAll();
  return { ok: true, updatedSlug: data?.slug ?? slug };
}
