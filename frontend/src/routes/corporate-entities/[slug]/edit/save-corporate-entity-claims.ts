import { invalidateAll } from '$app/navigation';
import client from '$lib/api/client';
import type { components } from '$lib/api/schema';
import {
  parseApiError,
  type FieldErrors,
  type SaveMeta,
  type SaveResult,
} from '$lib/components/editors/save-claims-shared';

export type { FieldErrors, SaveMeta, SaveResult };

type CorporateEntityClaimsBody = components['schemas']['CorporateEntityClaimPatchSchema'];

type CorporateEntitySectionPatchBody = Partial<
  Pick<CorporateEntityClaimsBody, 'fields' | 'aliases' | 'note' | 'citation'>
>;

export async function saveCorporateEntityClaims(
  slug: string,
  body: CorporateEntitySectionPatchBody,
): Promise<SaveResult> {
  const { data, error } = await client.PATCH('/api/corporate-entities/{slug}/claims/', {
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
