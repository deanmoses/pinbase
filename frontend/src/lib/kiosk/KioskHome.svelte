<!--
  Kiosk visitor grid. Rendered at /kiosk when this device has selected a
  kiosk config. The page model is preloaded by /kiosk/+page.server.ts; this
  component only renders.
-->
<script lang="ts">
  import { resolveHref } from '$lib/utils';
  import type { KioskPageSchema } from '$lib/api/schema';

  let { config }: { config: KioskPageSchema } = $props();
</script>

<svelte:head>
  <title>{config.page_heading || 'Kiosk'}</title>
</svelte:head>

<div class="kiosk">
  {#if config.page_heading}
    <h1 class="title">{config.page_heading}</h1>
  {/if}
  <div class="grid">
    {#each config.items as item (item.title.slug)}
      <a class="card" href={resolveHref(`/titles/${item.title.slug}`)}>
        <div class="card-media">
          {#if item.title.thumbnail_url}
            <img src={item.title.thumbnail_url} alt="" class="card-img" loading="lazy" />
          {:else}
            <div class="card-img placeholder"></div>
          {/if}
          <div class="card-overlay">
            <h2 class="card-name">{item.title.name}</h2>
            <div class="card-meta">
              {#if item.title.manufacturer}<span>{item.title.manufacturer.name}</span>{/if}
              {#if item.title.year}<span>{item.title.year}</span>{/if}
            </div>
          </div>
        </div>
        {#if item.hook}
          <p class="card-hook">{item.hook}</p>
        {/if}
      </a>
    {/each}
  </div>
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
    box-shadow: var(--shadow-popover);
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
    inset: auto 0 0;
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
</style>
