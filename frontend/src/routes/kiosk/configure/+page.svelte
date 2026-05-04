<!--
  Kiosk configuration page. Staff use this to choose machines, edit hooks,
  reorder, and toggle kiosk mode. Every edit auto-saves to localStorage.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import client from '$lib/api/client';
  import {
    clearKioskCookie,
    DEFAULT_IDLE_SECONDS,
    DEFAULT_TITLE,
    HOOK_MAX_LENGTH,
    isKioskCookieSet,
    loadConfig,
    saveConfig,
    setKioskCookie,
    type KioskConfig,
    type KioskItem,
  } from '$lib/kiosk/config';
  import { normalizeText } from '$lib/utils';
  import { matchesQuery } from '$lib/facet-engine';
  import Button from '$lib/components/Button.svelte';
  import Page from '$lib/components/Page.svelte';
  import TwoColumnLayout from '$lib/components/TwoColumnLayout.svelte';
  import SidebarSection from '$lib/components/SidebarSection.svelte';
  import type { TitleListItemSchema } from '$lib/api/schema';

  let title = $state(DEFAULT_TITLE);
  let idleSeconds = $state(DEFAULT_IDLE_SECONDS);
  let items = $state<KioskItem[]>([]);
  let allTitles = $state<TitleListItemSchema[]>([]);
  let search = $state('');
  let kioskActive = $state(false);
  let loaded = $state(false);

  let configuredSlugs = $derived(new Set(items.map((i) => i.titleSlug)));

  let searchResults = $derived.by(() => {
    const q = normalizeText(search);
    if (!q) return [];
    return allTitles
      .filter((t) => !configuredSlugs.has(t.slug))
      .filter((t) => matchesQuery(t, q))
      .slice(0, 12);
  });

  let titleBySlug = $derived(new Map(allTitles.map((t) => [t.slug, t])));

  onMount(async () => {
    const existing = loadConfig();
    if (existing) {
      title = existing.title;
      idleSeconds = existing.idleSeconds;
      items = [...existing.items];
    }
    kioskActive = isKioskCookieSet();
    loaded = true;
    const res = await client.GET('/api/titles/all/');
    if (res.data) allTitles = res.data;
  });

  function buildConfig(): KioskConfig {
    return {
      title: title.trim(),
      idleSeconds: idleSeconds > 0 ? idleSeconds : DEFAULT_IDLE_SECONDS,
      items: items.map((i) => ({
        titleSlug: i.titleSlug,
        hook: i.hook.slice(0, HOOK_MAX_LENGTH),
      })),
    };
  }

  // Auto-save: any edit to title, idleSeconds, or items writes to localStorage.
  // The `loaded` gate prevents writes during the initial onMount setters.
  $effect(() => {
    if (!loaded) return;
    saveConfig(buildConfig());
  });

  function addTitle(slug: string) {
    items = [...items, { titleSlug: slug, hook: '' }];
    search = '';
  }

  function removeAt(index: number) {
    items = items.filter((_, i) => i !== index);
  }

  function moveUp(index: number) {
    if (index === 0) return;
    const next = [...items];
    [next[index - 1], next[index]] = [next[index], next[index - 1]];
    items = next;
  }

  function moveDown(index: number) {
    if (index === items.length - 1) return;
    const next = [...items];
    [next[index + 1], next[index]] = [next[index], next[index + 1]];
    items = next;
  }

  async function handleEnter() {
    setKioskCookie();
    await goto('/kiosk');
  }

  function handleExit() {
    clearKioskCookie();
    kioskActive = false;
  }
</script>

<svelte:head>
  <title>Configure Kiosk</title>
</svelte:head>

<Page width="extra-wide">
  <TwoColumnLayout>
    {#snippet main()}
      <header class="header header-mobile">
        {#if kioskActive}
          <Button type="button" variant="secondary" onclick={handleExit}>Exit Kiosk Mode</Button>
        {:else}
          <Button type="button" onclick={handleEnter}>Enter Kiosk Mode</Button>
        {/if}
      </header>

      <section class="settings">
        <label>
          <span>Title</span>
          <input type="text" bind:value={title} maxlength="60" />
        </label>
        <label>
          <span>Idle timeout (seconds)</span>
          <input type="number" min="10" max="3600" bind:value={idleSeconds} />
        </label>
      </section>

      <section class="machines">
        <label class="search">
          <span>Add a machine</span>
          <input
            type="search"
            placeholder="Search by name…"
            bind:value={search}
            autocomplete="off"
          />
        </label>

        {#if searchResults.length > 0}
          <ul class="results">
            {#each searchResults as t (t.slug)}
              <li>
                <button type="button" onclick={() => addTitle(t.slug)}>
                  <strong>{t.name}</strong>
                  <span class="result-meta">
                    {#if t.manufacturer}{t.manufacturer.name}{/if}
                    {#if t.year}· {t.year}{/if}
                  </span>
                </button>
              </li>
            {/each}
          </ul>
        {/if}

        <hr class="divider" />

        {#if items.length === 0}
          <p class="empty">No machines added yet.</p>
        {:else}
          <ol class="items">
            {#each items as item, i (item.titleSlug)}
              {@const t = titleBySlug.get(item.titleSlug)}
              <li class="item">
                <div class="item-header">
                  <span class="item-name">
                    {t?.name ?? item.titleSlug}
                    {#if t?.year}<span class="dim"> · {t.year}</span>{/if}
                    {#if t?.manufacturer}<span class="dim"> · {t.manufacturer.name}</span>{/if}
                  </span>
                  <div class="item-actions">
                    <button
                      type="button"
                      onclick={() => moveUp(i)}
                      disabled={i === 0}
                      aria-label="Move up">↑</button
                    >
                    <button
                      type="button"
                      onclick={() => moveDown(i)}
                      disabled={i === items.length - 1}
                      aria-label="Move down">↓</button
                    >
                    <button type="button" onclick={() => removeAt(i)} aria-label="Remove">✕</button>
                  </div>
                </div>
                <input
                  type="text"
                  placeholder="Hook (optional, e.g. 'First talking pinball machine')"
                  bind:value={item.hook}
                  maxlength={HOOK_MAX_LENGTH}
                />
              </li>
            {/each}
          </ol>
        {/if}
      </section>
    {/snippet}

    {#snippet sidebar()}
      <SidebarSection heading="Configure Kiosk">
        <p class="about">
          Kiosk mode turns the front door of this browser into a curated display of specific pinball
          machines — for use on an in-museum kiosk.
        </p>
        <p class="about">
          Pick the machines you want to feature, and set how long the browser sits idle before
          resetting to the kiosk home screen.
        </p>
        <p class="about">This configuration is specific to this browser on this machine.</p>
        <div class="sidebar-action">
          {#if kioskActive}
            <Button type="button" variant="secondary" onclick={handleExit}>Exit Kiosk Mode</Button>
          {:else}
            <Button type="button" onclick={handleEnter}>Enter Kiosk Mode</Button>
          {/if}
        </div>
      </SidebarSection>
    {/snippet}
  </TwoColumnLayout>
</Page>

<style>
  .header {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin-bottom: var(--size-5);
  }

  .about {
    font-size: var(--font-size-1);
    color: var(--color-text-muted);
    margin: 0 0 var(--size-2);
    line-height: 1.5;
  }

  .about:last-child {
    margin-bottom: 0;
  }

  .sidebar-action {
    margin-top: var(--size-3);
  }

  /* Keep in sync with LAYOUT_BREAKPOINT (52rem) — the breakpoint at which
     TwoColumnLayout reveals the sidebar. Above it, the sidebar's button is
     visible, so the in-main copy must hide. */
  @media (min-width: 52rem) {
    .header-mobile {
      display: none;
    }
  }

  .settings {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--size-4);
    margin-bottom: var(--size-5);
  }

  label {
    display: flex;
    flex-direction: column;
    gap: var(--size-1);
    font-size: var(--font-size-1);
  }

  label > span {
    color: var(--color-text-muted);
  }

  input[type='text'],
  input[type='search'],
  input[type='number'] {
    padding: var(--size-2) var(--size-3);
    border: 1px solid var(--color-border-soft);
    border-radius: var(--radius-2);
    font-size: var(--font-size-1);
  }

  .divider {
    margin: var(--size-5) 0 var(--size-3);
    border: none;
    border-top: 3px solid var(--color-border-soft);
  }

  .results {
    list-style: none;
    padding: 0;
    margin: var(--size-2) 0 0;
    border: 1px solid var(--color-border-soft);
    border-radius: var(--radius-2);
    max-height: 18rem;
    overflow-y: auto;
  }

  .results li {
    border-bottom: 1px solid var(--color-border-soft);
  }

  .results li:last-child {
    border-bottom: none;
  }

  .results button {
    width: 100%;
    text-align: left;
    background: transparent;
    border: none;
    padding: var(--size-2) var(--size-3);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: var(--size-1);
  }

  .results button:hover {
    background: var(--color-surface-muted, #f0f0f0);
  }

  .result-meta {
    font-size: var(--font-size-0);
    color: var(--color-text-muted);
  }

  .items {
    list-style: none;
    padding: 0;
    margin: var(--size-3) 0 0;
    display: flex;
    flex-direction: column;
    gap: var(--size-3);
  }

  .item {
    display: flex;
    flex-direction: column;
    gap: var(--size-2);
    padding: var(--size-3);
    border: 1px solid var(--color-border-soft);
    border-radius: var(--radius-2);
  }

  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--size-2);
  }

  .item-name {
    font-weight: 600;
  }

  .dim {
    color: var(--color-text-muted);
    font-weight: 400;
  }

  .item-actions {
    display: flex;
    gap: var(--size-1);
  }

  .item-actions button {
    background: transparent;
    border: 1px solid var(--color-border-soft);
    border-radius: var(--radius-2);
    padding: var(--size-1) var(--size-2);
    cursor: pointer;
    min-width: 2rem;
  }

  .item-actions button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .empty {
    color: var(--color-text-muted);
    font-style: italic;
    margin-top: var(--size-3);
  }
</style>
