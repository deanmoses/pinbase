<script lang="ts">
	import type { Snippet } from 'svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
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
		sidebar: sidebarContent
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

<article>
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
		<p class="status error">Failed to load location.</p>
	{:else}
		<PageHeader
			title={heading}
			breadcrumbs={crumbs}
			--page-header-mb="var(--size-5)"
			--page-header-title-mb="var(--size-2)"
		>
			<p class="subtitle">{subtitle}</p>
		</PageHeader>

		<TwoColumnLayout>
			{#snippet main()}
				<ManufacturerCardGrid {manufacturers} showCount={false} />
			{/snippet}

			{#snippet sidebar()}
				{@render sidebarContent()}
			{/snippet}
		</TwoColumnLayout>
	{/if}
</article>

<style>
	.subtitle {
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
	}

	.status.error {
		color: var(--color-error);
		text-align: center;
		padding: var(--size-8) 0;
	}
</style>
