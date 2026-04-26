import {
  saveSimpleTaxonomyClaims,
  type SimpleTaxonomySectionPatchBody,
} from '$lib/components/editors/save-claims-shared';

export const saveTechnologySubgenerationClaims = (
  slug: string,
  body: SimpleTaxonomySectionPatchBody,
) => saveSimpleTaxonomyClaims('/api/technology-subgenerations/{slug}/claims/', slug, body);
