<script lang="ts">
  import { auth } from '$lib/auth.svelte';
  import { MEDIA_CATEGORIES } from '$lib/api/catalog-meta';
  import MediaEditor from '$lib/components/editors/MediaEditor.svelte';
  import MediaGrid from '$lib/components/media/MediaGrid.svelte';

  let { data } = $props();
  let mfr = $derived(data.manufacturer);
</script>

{#if auth.isAuthenticated}
  <MediaEditor entityType="manufacturer" slug={mfr.slug} media={mfr.uploaded_media} />
{:else}
  <MediaGrid
    media={mfr.uploaded_media}
    categories={[...MEDIA_CATEGORIES.manufacturer]}
    canEdit={false}
  />
{/if}
