import { invalidateAll } from '$app/navigation';
import client from '$lib/api/client';
import type { components } from '$lib/api/schema';
import {
  parseApiError,
  type SaveMeta,
  type SaveResult,
} from '$lib/components/editors/save-claims-shared';

export type { SaveMeta };

type FranchiseClaimsBody = components['schemas']['ClaimPatchSchema'];

type FranchiseSectionPatchBody = Partial<Pick<FranchiseClaimsBody, 'fields' | 'note' | 'citation'>>;

export async function saveFranchiseClaims(
  slug: string,
  body: FranchiseSectionPatchBody,
): Promise<SaveResult> {
  const { data, error } = await client.PATCH('/api/franchises/{slug}/claims/', {
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
