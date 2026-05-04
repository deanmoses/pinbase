<!--
  Kiosk visitor grid. Rendered at `/` when the mode=kiosk cookie is set.
  Config lives in localStorage; title data is fetched from the API.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import client from '$lib/api/client';
  import { loadConfig, type KioskConfig } from './config';
  import { resolveHref } from '$lib/utils';
  import type { TitleListItemSchema } from '$lib/api/schema';

  let config = $state<KioskConfig | null>(null);
  let allTitles = $state<TitleListItemSchema[]>([]);
  let loaded = $state(false);

  type Card = {
    slug: string;
    name: string;
    manufacturer: string | null;
    year: number | null;
    thumbnailUrl: string | null;
    hook: string;
  };

  let cards = $derived.by((): Card[] => {
    if (!config) return [];
    const bySlug = new Map(allTitles.map((t) => [t.slug, t]));
    return config.items
      .map((item) => {
        const title = bySlug.get(item.titleSlug);
        if (!title) return null;
        return {
          slug: title.slug,
          name: title.name,
          manufacturer: title.manufacturer?.name ?? null,
          year: title.year ?? null,
          thumbnailUrl: title.thumbnail_url ?? null,
          hook: item.hook,
        };
      })
      .filter((c): c is Card => c !== null);
  });

  onMount(async () => {
    config = loadConfig();
    if (config && config.items.length > 0) {
      const res = await client.GET('/api/titles/all/');
      if (res.data) allTitles = res.data;
    }
    loaded = true;
  });
</script>

<svelte:head>
  <title>{config?.title || 'Kiosk'}</title>
</svelte:head>

<div class="kiosk">
  {#if !loaded}
    <div class="loading">Loading…</div>
  {:else if !config || config.items.length === 0}
    <div class="empty">
      <h1>Kiosk not configured</h1>
      <p>
        Set up the kiosk at
        <a href={resolve('/kiosk/configure')}>{resolve('/kiosk/configure')}</a>.
      </p>
    </div>
  {:else}
    {#if config.title}
      <h1 class="title">{config.title}</h1>
    {/if}
    <div class="grid">
      {#each cards as card (card.slug)}
        <a class="card" href={resolveHref(`/titles/${card.slug}`)}>
          <div class="card-media">
            {#if card.thumbnailUrl}
              <img src={card.thumbnailUrl} alt="" class="card-img" loading="lazy" />
            {:else}
              <div class="card-img placeholder"></div>
            {/if}
            <div class="card-overlay">
              <h2 class="card-name">{card.name}</h2>
              <div class="card-meta">
                {#if card.manufacturer}<span>{card.manufacturer}</span>{/if}
                {#if card.year}<span>{card.year}</span>{/if}
              </div>
            </div>
          </div>
          {#if card.hook}
            <p class="card-hook">{card.hook}</p>
          {/if}
        </a>
      {/each}
    </div>
  {/if}
</div>

<style>
  .kiosk {
    max-width: 90rem;
    margin: 0 auto;
    padding: var(--size-5) var(--size-4);
  }

  .title {
    font-size: var(--font-size-6);
    font-weight: 700;
    text-align: center;
    margin-bottom: var(--size-6);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(20rem, 1fr));
    gap: var(--size-5);
  }

  .card {
    display: flex;
    flex-direction: column;
    background: var(--color-surface);
    border: 1px solid var(--color-border-soft);
    border-radius: var(--radius-3);
    overflow: hidden;
    text-decoration: none;
    color: inherit;
    transition:
      transform 0.15s var(--ease-2),
      box-shadow 0.15s var(--ease-2);
  }

  .card:hover,
  .card:focus-visible {
    transform: scale(1.02);
    box-shadow: 0 4px 16px rgb(0 0 0 / 0.12);
  }

  .card-media {
    position: relative;
    width: 100%;
    height: 14rem;
    background: var(--color-surface-muted, #f0f0f0);
  }

  .card-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .card-img.placeholder {
    background: var(--color-surface-muted, #f0f0f0);
  }

  .card-overlay {
    position: absolute;
    inset: auto 0 0 0;
    padding: var(--size-5) var(--size-4) var(--size-3);
    background: linear-gradient(
      to top,
      rgb(0 0 0 / 0.85) 0%,
      rgb(0 0 0 / 0.55) 50%,
      rgb(0 0 0 / 0) 100%
    );
    color: #fff;
    display: flex;
    flex-direction: column;
    gap: var(--size-1);
  }

  .card-name {
    font-size: var(--font-size-4);
    font-weight: 700;
    margin: 0;
    line-height: 1.15;
    text-shadow: 0 1px 2px rgb(0 0 0 / 0.5);
  }

  .card-meta {
    display: flex;
    flex-wrap: wrap;
    font-size: var(--font-size-1);
    color: rgb(255 255 255 / 0.9);
    text-shadow: 0 1px 2px rgb(0 0 0 / 0.5);
  }

  .card-meta span:not(:last-child)::after {
    content: ' · ';
    white-space: pre;
  }

  .card-hook {
    padding: var(--size-3) var(--size-4) var(--size-4);
    font-size: var(--font-size-2);
    color: var(--color-text-primary);
    margin: 0;
    line-height: 1.4;
  }

  .empty,
  .loading {
    text-align: center;
    padding: var(--size-8) var(--size-4);
    color: var(--color-text-muted);
  }

  .empty h1 {
    font-size: var(--font-size-5);
    margin-bottom: var(--size-3);
  }
</style>
