<script lang="ts">
  import client from '$lib/api/client';
  import { createAsyncLoader } from '$lib/async-loader.svelte';
  import Page from '$lib/components/Page.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import StatusMessage from '$lib/components/StatusMessage.svelte';
  import EditSectionMenu from '$lib/components/EditSectionMenu.svelte';
  import type { EditSectionMenuItem } from '$lib/components/edit-section-menu';
  import { auth } from '$lib/auth.svelte';
  import { resolveHref } from '$lib/utils';
  import { pageTitle } from '$lib/constants';

  const locations = createAsyncLoader(
    async () => {
      const { data } = await client.GET('/api/locations/');
      return data ?? { countries: [] };
    },
    { countries: [] },
  );

  $effect(() => {
    void auth.load();
  });

  const actionItems: EditSectionMenuItem[] = [
    { key: 'new', label: '+ New Country', href: resolveHref('/locations/new') },
  ];

  let showActionMenu = $derived(auth.isAuthenticated && !locations.loading && !locations.error);
</script>

<svelte:head>
  <title>{pageTitle('Locations')}</title>
  <link rel="preload" as="fetch" href="/api/locations/" crossorigin="anonymous" />
</svelte:head>

{#snippet actionsSnippet()}
  <EditSectionMenu items={actionItems} />
{/snippet}

<Page>
  <PageHeader
    title="Locations"
    subtitle="Browse pinball manufacturers by country, state, and city."
    actions={showActionMenu ? actionsSnippet : undefined}
  />

  {#if locations.loading}
    <StatusMessage variant="loading">Loading...</StatusMessage>
  {:else if locations.error}
    <StatusMessage variant="error">Failed to load locations.</StatusMessage>
  {:else if locations.data.countries.length === 0}
    <StatusMessage variant="empty">No locations found.</StatusMessage>
  {:else}
    <div class="countries">
      {#each locations.data.countries as country (country.location_path)}
        <section class="country-section">
          <h2>
            <a href={resolveHref(`/locations/${country.location_path}`)}>
              {country.name}
            </a>
            <span class="count">{country.manufacturer_count}</span>
          </h2>

          {#if country.children.length > 0}
            <ul class="child-list">
              {#each country.children as child (child.location_path)}
                <li>
                  <a href={resolveHref(`/locations/${child.location_path}`)} class="location-row">
                    <span class="location-name">{child.name}</span>
                    <span class="count">{child.manufacturer_count}</span>
                  </a>
                </li>
              {/each}
            </ul>
          {/if}
        </section>
      {/each}
    </div>
  {/if}
</Page>

<style>
  .country-section {
    margin-bottom: var(--size-6);
  }

  .country-section h2 {
    display: flex;
    align-items: baseline;
    gap: var(--size-2);
    font-size: var(--font-size-5);
    font-weight: 600;
    color: var(--color-text-primary);
    margin-bottom: var(--size-3);
    padding-bottom: var(--size-2);
    border-bottom: 2px solid var(--color-border-soft);
  }

  .country-section h2 a {
    color: inherit;
    text-decoration: none;
  }

  .country-section h2 a:hover {
    color: var(--color-accent);
  }

  .child-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .location-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding: var(--size-2) 0;
    border-bottom: 1px solid var(--color-border-soft);
    text-decoration: none;
    color: inherit;
  }

  .location-row:hover .location-name {
    color: var(--color-accent);
  }

  .location-name {
    font-size: var(--font-size-2);
    color: var(--color-text-primary);
    font-weight: 500;
  }

  .count {
    font-size: var(--font-size-0);
    color: var(--color-text-muted);
    font-weight: 400;
  }
</style>
