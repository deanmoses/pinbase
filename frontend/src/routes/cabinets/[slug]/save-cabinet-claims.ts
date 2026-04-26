import {
  saveSimpleTaxonomyClaims,
  type SimpleTaxonomySectionPatchBody,
} from '$lib/components/editors/save-claims-shared';

export const saveCabinetClaims = (slug: string, body: SimpleTaxonomySectionPatchBody) =>
  saveSimpleTaxonomyClaims('/api/cabinets/{slug}/claims/', slug, body);
