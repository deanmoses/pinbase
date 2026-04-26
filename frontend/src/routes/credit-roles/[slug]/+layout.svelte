<script lang="ts">
  import SimpleTaxonomyDetailLayout from '$lib/components/SimpleTaxonomyDetailLayout.svelte';

  let { data, children } = $props();
  let profile = $derived(data.profile);
</script>

<SimpleTaxonomyDetailLayout
  {profile}
  parentLabel="Credit Roles"
  basePath="/credit-roles"
  claimsPath={'/api/credit-roles/{slug}/claims/'}
  deleteHref={`/credit-roles/${profile.slug}/delete`}
>
  {@render children()}
</SimpleTaxonomyDetailLayout>
