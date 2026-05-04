<script lang="ts">
  import { untrack } from 'svelte';
  import type { UploadedMediaSchema } from '$lib/api/schema';
  import MediaCard from './MediaCard.svelte';
  import MediaLightbox from './MediaLightbox.svelte';

  type UploadedMedia = UploadedMediaSchema;

  const BATCH_SIZE = 100;

  let {
    media,
    categories = [],
    canEdit = false,
    highlightUuids = [],
    initialCategory = null,
    ondelete,
    onsetprimary,
    oncategorychange,
  }: {
    media: UploadedMedia[];
    categories?: string[];
    canEdit?: boolean;
    highlightUuids?: string[];
    initialCategory?: string | null;
    ondelete?: (assetUuid: string) => void;
    onsetprimary?: (assetUuid: string) => void;
    oncategorychange?: (assetUuid: string, category: string) => void;
  } = $props();

  // svelte-ignore state_referenced_locally
  let activeCategory = $state<string | null>(initialCategory);

  let filteredMedia = $derived(
    activeCategory ? media.filter((m) => m.category === activeCategory) : media,
  );

  let visibleCount = $state(BATCH_SIZE);
  let visibleMedia = $derived(filteredMedia.slice(0, visibleCount));
  let hasMore = $derived(visibleCount < filteredMedia.length);

  // Reset visible count when filter changes
  $effect(() => {
    void activeCategory;
    visibleCount = BATCH_SIZE;
  });

  // Infinite scroll sentinel
  let sentinel: HTMLDivElement | undefined = $state();

  $effect(() => {
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          visibleCount += BATCH_SIZE;
        }
      },
      { rootMargin: '200px' },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  });

  // Category counts — single pass over the array, derived so it recalculates only when media changes
  let categoryCounts = $derived(
    media.reduce<Record<string, number>>((acc, m) => {
      if (m.category) acc[m.category] = (acc[m.category] ?? 0) + 1;
      return acc;
    }, {}),
  );

  let gridEl: HTMLDivElement | undefined = $state();
  let highlightSet = $derived(new Set(highlightUuids));

  // One-shot consumer: highlightUuids is a signal, not a reactive view.
  // Track only the array reference; untrack the body so unrelated
  // media/filter changes don't re-fire the scroll.
  let lastHighlight: string[] | null = null;
  $effect(() => {
    const uuids = highlightUuids;
    if (uuids === lastHighlight) return;
    lastHighlight = uuids;
    if (uuids.length === 0) return;
    untrack(() => {
      const idx = filteredMedia.findIndex((m) => uuids.includes(m.asset_uuid));
      if (idx === -1) return;
      if (idx >= visibleCount) {
        visibleCount = Math.ceil((idx + 1) / BATCH_SIZE) * BATCH_SIZE;
      }
      queueMicrotask(() => {
        const target = gridEl?.querySelector<HTMLElement>(`[data-asset-uuid="${uuids[0]}"]`);
        target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    });
  });

  // Lightbox state
  let lightboxIndex = $state<number | null>(null);

  function openLightbox(uuid: string) {
    lightboxIndex = filteredMedia.findIndex((m) => m.asset_uuid === uuid);
  }

  function closeLightbox() {
    lightboxIndex = null;
  }
</script>

<div class="media-grid-container">
  <div class="filters">
    <button
      class="filter-btn"
      class:active={activeCategory === null}
      onclick={() => (activeCategory = null)}
    >
      All ({media.length})
    </button>
    {#each categories as cat (cat)}
      <button
        class="filter-btn"
        class:active={activeCategory === cat}
        onclick={() => (activeCategory = cat)}
      >
        {cat} ({categoryCounts[cat] ?? 0})
      </button>
    {/each}
  </div>

  {#if filteredMedia.length === 0}
    <p class="empty">
      {#if activeCategory}
        No {activeCategory} images yet.
      {:else}
        No images yet.
      {/if}
    </p>
  {:else}
    <div class="grid" bind:this={gridEl}>
      {#each visibleMedia as asset (asset.asset_uuid)}
        <div
          class="card-slot"
          class:highlight={highlightSet.has(asset.asset_uuid)}
          data-asset-uuid={asset.asset_uuid}
        >
          <MediaCard
            {asset}
            {canEdit}
            {categories}
            {ondelete}
            {onsetprimary}
            {oncategorychange}
            onclick={openLightbox}
          />
        </div>
      {/each}
    </div>

    {#if hasMore}
      <div class="sentinel" bind:this={sentinel}></div>
    {/if}
  {/if}
</div>

{#if lightboxIndex !== null}
  <MediaLightbox media={filteredMedia} initialIndex={lightboxIndex} onclose={closeLightbox} />
{/if}

<style>
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: var(--size-2);
    margin-bottom: var(--size-4);
  }

  .filter-btn {
    background: none;
    border: 1px solid var(--color-border-soft);
    border-radius: var(--radius-2);
    padding: var(--size-1) var(--size-3);
    font-size: var(--font-size-1);
    color: var(--color-text-muted);
    cursor: pointer;
    transition:
      color 0.15s ease,
      border-color 0.15s ease;
  }

  .filter-btn:hover {
    color: var(--color-text);
    border-color: var(--color-border);
  }

  .filter-btn.active {
    color: var(--color-link);
    border-color: var(--color-link);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: var(--size-4);
  }

  .card-slot {
    border-radius: var(--radius-2);
  }

  .card-slot.highlight {
    animation: highlight-pulse 1.6s ease-out;
  }

  @keyframes highlight-pulse {
    0% {
      box-shadow: 0 0 0 0 var(--color-accent);
    }
    30% {
      box-shadow: 0 0 0 6px color-mix(in srgb, var(--color-accent) 35%, transparent);
    }
    100% {
      box-shadow: 0 0 0 0 transparent;
    }
  }

  .empty {
    text-align: center;
    color: var(--color-text-muted);
    font-size: var(--font-size-1);
    padding: var(--size-6) 0;
  }

  .sentinel {
    height: 1px;
  }
</style>
