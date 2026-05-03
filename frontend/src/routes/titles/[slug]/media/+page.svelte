<script lang="ts">
  import { auth } from '$lib/auth.svelte';
  import { MEDIA_CATEGORIES } from '$lib/api/catalog-meta';
  import MediaEditor from '$lib/components/editors/MediaEditor.svelte';
  import MediaGrid from '$lib/components/media/MediaGrid.svelte';

  let { data } = $props();
  let md = $derived(data.title.model_detail);
</script>

{#if md}
  {#if auth.isAuthenticated}
    <MediaEditor entityType="model" slug={md.slug} media={md.uploaded_media} />
  {:else}
    <MediaGrid media={md.uploaded_media} categories={[...MEDIA_CATEGORIES.model]} canEdit={false} />
  {/if}
{/if}
