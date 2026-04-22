import { invalidateAll } from '$app/navigation';
import client from '$lib/api/client';
import type { components } from '$lib/api/schema';
import { parseApiError, type SaveResult } from '$lib/components/editors/save-claims-shared';

type RewardTypeClaimsBody = components['schemas']['ClaimPatchSchema'];

type RewardTypeSectionPatchBody = Partial<
  Pick<RewardTypeClaimsBody, 'fields' | 'note' | 'citation'>
>;

export async function saveRewardTypeClaims(
  slug: string,
  body: RewardTypeSectionPatchBody,
): Promise<SaveResult> {
  const { data, error } = await client.PATCH('/api/reward-types/{slug}/claims/', {
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
