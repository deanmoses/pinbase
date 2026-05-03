<script lang="ts">
  import { auth } from '$lib/auth.svelte';
  import { MEDIA_CATEGORIES } from '$lib/api/catalog-meta';
  import MediaEditor from '$lib/components/editors/MediaEditor.svelte';
  import MediaGrid from '$lib/components/media/MediaGrid.svelte';

  let { data } = $props();
  let profile = $derived(data.profile);
</script>

{#if auth.isAuthenticated}
  <MediaEditor entityType="gameplay-feature" slug={profile.slug} media={profile.uploaded_media} />
{:else}
  <MediaGrid
    media={profile.uploaded_media}
    categories={[...MEDIA_CATEGORIES['gameplay-feature']]}
    canEdit={false}
  />
{/if}
