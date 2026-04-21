<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import TaxonomyListPage from '$lib/components/TaxonomyListPage.svelte';

	const loader = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/franchises/');
		return data ?? [];
	}, []);
</script>

{#snippet row(f: (typeof loader.data)[number])}
	<span class="franchise-name">{f.name}</span>
	{#if f.title_count}
		<span class="franchise-count">{f.title_count}</span>
	{/if}
{/snippet}

<TaxonomyListPage
	title="Franchises"
	subtitle="Licensed and original franchises featured in pinball."
	basePath="/franchises"
	items={loader.data}
	loading={loader.loading}
	error={loader.error}
	rowSnippet={row}
	rowStyle="justify-content: space-between; gap: var(--size-4)"
	createHref="/franchises/new"
/>

<style>
	.franchise-name {
		font-size: var(--font-size-2);
		font-weight: 500;
		color: inherit;
	}

	.franchise-count {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
		flex-shrink: 0;
	}
</style>
