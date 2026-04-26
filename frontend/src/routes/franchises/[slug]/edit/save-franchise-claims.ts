import {
  saveSimpleTaxonomyClaims,
  type SimpleTaxonomySectionPatchBody,
} from '$lib/components/editors/save-claims-shared';

export const saveFranchiseClaims = (slug: string, body: SimpleTaxonomySectionPatchBody) =>
  saveSimpleTaxonomyClaims('/api/franchises/{slug}/claims/', slug, body);
