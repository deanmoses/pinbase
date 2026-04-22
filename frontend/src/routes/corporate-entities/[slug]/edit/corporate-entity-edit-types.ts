import type { components } from '$lib/api/schema';

export type CorporateEntityEditView = Pick<
  components['schemas']['CorporateEntityDetailSchema'],
  'name' | 'slug' | 'description' | 'year_start' | 'year_end' | 'aliases'
>;
