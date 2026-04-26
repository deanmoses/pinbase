import {
  saveSimpleTaxonomyClaims,
  type SimpleTaxonomySectionPatchBody,
} from '$lib/components/editors/save-claims-shared';

export const saveTechnologyGenerationClaims = (
  slug: string,
  body: SimpleTaxonomySectionPatchBody,
) => saveSimpleTaxonomyClaims('/api/technology-generations/{slug}/claims/', slug, body);
