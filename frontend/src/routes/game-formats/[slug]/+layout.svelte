<script lang="ts">
  import SimpleTaxonomyDetailLayout from '$lib/components/SimpleTaxonomyDetailLayout.svelte';
  import { saveGameFormatClaims } from './save-game-format-claims';

  let { data, children } = $props();
  let profile = $derived(data.profile);
</script>

<SimpleTaxonomyDetailLayout
  {profile}
  parentLabel="Game Formats"
  basePath="/game-formats"
  saveClaims={saveGameFormatClaims}
  deleteHref={`/game-formats/${profile.slug}/delete`}
>
  {@render children()}
</SimpleTaxonomyDetailLayout>
