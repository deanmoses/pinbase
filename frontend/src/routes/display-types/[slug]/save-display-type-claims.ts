import {
  saveSimpleTaxonomyClaims,
  type SimpleTaxonomySectionPatchBody,
} from '$lib/components/editors/save-claims-shared';

export const saveDisplayTypeClaims = (slug: string, body: SimpleTaxonomySectionPatchBody) =>
  saveSimpleTaxonomyClaims('/api/display-types/{slug}/claims/', slug, body);
