import {
  saveSimpleTaxonomyClaims,
  type SaveMeta,
  type SimpleTaxonomySectionPatchBody,
} from '$lib/components/editors/save-claims-shared';

export type { SaveMeta };

export const saveSystemClaims = (slug: string, body: SimpleTaxonomySectionPatchBody) =>
  saveSimpleTaxonomyClaims('/api/systems/{slug}/claims/', slug, body);
