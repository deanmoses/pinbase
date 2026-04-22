<script lang="ts">
  import SimpleTaxonomyDetailLayout from '$lib/components/SimpleTaxonomyDetailLayout.svelte';
  import { saveDisplayTypeClaims } from './save-display-type-claims';

  let { data, children } = $props();
  let profile = $derived(data.profile);
</script>

<SimpleTaxonomyDetailLayout
  {profile}
  parentLabel="Display Types"
  basePath="/display-types"
  saveClaims={saveDisplayTypeClaims}
  deleteHref={`/display-types/${profile.slug}/delete`}
  createChild={{
    href: `/display-subtypes/new?parent=${profile.slug}`,
    label: 'subtype',
  }}
>
  {@render children()}
</SimpleTaxonomyDetailLayout>
