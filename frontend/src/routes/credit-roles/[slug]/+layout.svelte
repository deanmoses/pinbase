<script lang="ts">
  import SimpleTaxonomyDetailLayout from '$lib/components/SimpleTaxonomyDetailLayout.svelte';
  import { saveCreditRoleClaims } from './save-credit-role-claims';

  let { data, children } = $props();
  let profile = $derived(data.profile);
</script>

<SimpleTaxonomyDetailLayout
  {profile}
  parentLabel="Credit Roles"
  basePath="/credit-roles"
  saveClaims={saveCreditRoleClaims}
  deleteHref={`/credit-roles/${profile.slug}/delete`}
>
  {@render children()}
</SimpleTaxonomyDetailLayout>
