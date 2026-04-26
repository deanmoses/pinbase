import {
  saveSimpleTaxonomyClaims,
  type SimpleTaxonomySectionPatchBody,
} from '$lib/components/editors/save-claims-shared';

export const saveRewardTypeClaims = (slug: string, body: SimpleTaxonomySectionPatchBody) =>
  saveSimpleTaxonomyClaims('/api/reward-types/{slug}/claims/', slug, body);
