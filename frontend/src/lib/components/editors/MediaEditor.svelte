<script lang="ts">
  import { invalidateAll } from '$app/navigation';
  import { detachMedia, setCategory, setPrimary } from '$lib/api/media-api';
  import { MEDIA_CATEGORIES } from '$lib/api/catalog-meta';
  import type { UploadedMediaSchema } from '$lib/api/schema';
  import MediaUploadZone from '$lib/components/media/MediaUploadZone.svelte';
  import MediaGrid from '$lib/components/media/MediaGrid.svelte';
  import { toast } from '$lib/toast/toast.svelte';

  type UploadedMedia = UploadedMediaSchema;
  type MediaEntityKey = keyof typeof MEDIA_CATEGORIES;

  let {
    entityType,
    slug,
    media,
  }: {
    entityType: MediaEntityKey;
    slug: string;
    media: UploadedMedia[];
  } = $props();

  const categories = $derived(MEDIA_CATEGORIES[entityType]);

  let actionError = $state('');

  async function handleUploaded() {
    actionError = '';
    await invalidateAll();
  }

  async function refreshAfterWrite() {
    try {
      await invalidateAll();
    } catch {
      // Best-effort refresh; the write already succeeded and the next
      // navigation will pick up the new state.
    }
  }

  async function handleDelete(assetUuid: string) {
    actionError = '';
    try {
      await detachMedia(entityType, slug, assetUuid);
    } catch (err) {
      actionError = err instanceof Error ? err.message : 'Failed to remove image.';
      return;
    }
    toast.success('Image removed.');
    await refreshAfterWrite();
  }

  async function handleSetPrimary(assetUuid: string) {
    actionError = '';
    try {
      await setPrimary(entityType, slug, assetUuid);
    } catch (err) {
      actionError = err instanceof Error ? err.message : 'Failed to set primary image.';
      return;
    }
    toast.success('Set as primary image.');
    await refreshAfterWrite();
  }

  async function handleCategoryChange(assetUuid: string, category: string) {
    actionError = '';
    const previous = media.find((m) => m.asset_uuid === assetUuid)?.category ?? 'none';
    try {
      await setCategory(entityType, slug, assetUuid, category);
    } catch (err) {
      actionError = err instanceof Error ? err.message : 'Failed to change image category.';
      return;
    }
    toast.success(`Image category changed from ${previous} to ${category}.`);
    await refreshAfterWrite();
  }
</script>

<div class="media-editor">
  {#if actionError}
    <p class="action-error">{actionError}</p>
  {/if}

  <MediaUploadZone {entityType} {slug} onuploaded={handleUploaded} />

  {#if media.length > 0}
    <div class="media-grid-section">
      <MediaGrid
        {media}
        categories={[...categories]}
        canEdit={true}
        ondelete={handleDelete}
        onsetprimary={handleSetPrimary}
        oncategorychange={handleCategoryChange}
      />
    </div>
  {/if}
</div>

<style>
  .media-editor {
    display: flex;
    flex-direction: column;
    gap: var(--size-4);
  }

  .action-error {
    color: var(--color-error);
    font-size: var(--font-size-1);
    margin: 0;
  }

  .media-grid-section {
    border-top: 1px solid var(--color-border-soft);
    padding-top: var(--size-4);
  }
</style>
