<script lang="ts">
  import type { Snippet } from 'svelte';
  import Page from '$lib/components/Page.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import StatusMessage from '$lib/components/StatusMessage.svelte';
  import type { Crumb } from '$lib/components/Breadcrumb.svelte';
  import TwoColumnLayout from '$lib/components/TwoColumnLayout.svelte';
  import CardGrid from '$lib/components/grid/CardGrid.svelte';
  import SkeletonCard from '$lib/components/cards/SkeletonCard.svelte';
  import ManufacturerCardGrid from '$lib/components/ManufacturerCardGrid.svelte';

  const SKELETON_INDICES = Array.from({ length: 8 }, (_, i) => i);

  let {
    loading,
    error,
    heading,
    subtitle,
    crumbs,
    manufacturers,
    sidebar: sidebarContent,
  }: {
    loading: boolean;
    error: boolean;
    heading: string;
    subtitle: string;
    crumbs: Crumb[];
    manufacturers: {
      name: string;
      slug: string;
      model_count: number;
      thumbnail_url?: string | null;
    }[];
    sidebar: Snippet;
  } = $props();
</script>

<Page width="extra-wide">
  {#if loading}
    <PageHeader
      title="Loading..."
      breadcrumbs={crumbs}
      --page-header-mb="var(--size-5)"
      --page-header-title-mb="var(--size-2)"
    />
    <CardGrid>
      {#each SKELETON_INDICES as i (i)}
        <SkeletonCard />
      {/each}
    </CardGrid>
  {:else if error}
    <PageHeader
      title="Not found"
      breadcrumbs={crumbs}
      --page-header-mb="var(--size-5)"
      --page-header-title-mb="var(--size-2)"
    />
    <StatusMessage variant="error">Failed to load location.</StatusMessage>
  {:else}
    <PageHeader
      title={heading}
      {subtitle}
      breadcrumbs={crumbs}
      --page-header-mb="var(--size-5)"
      --page-header-title-mb="var(--size-2)"
    />

    <TwoColumnLayout>
      {#snippet main()}
        <ManufacturerCardGrid {manufacturers} showCount={false} />
      {/snippet}

      {#snippet sidebar()}
        {@render sidebarContent()}
      {/snippet}
    </TwoColumnLayout>
  {/if}
</Page>
