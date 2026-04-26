import type { components } from '$lib/api/schema';

type RichTextSchema = components['schemas']['RichTextSchema'];

/**
 * Structural superset of GameplayFeatureDetailSchema and ThemeDetailSchema —
 * the fields the hierarchical-taxonomy section editors consume.
 */
export type HierarchicalTaxonomyEditView = {
  name: string;
  slug: string;
  description: RichTextSchema;
  parents: { name: string; slug: string }[];
  aliases: string[];
};
