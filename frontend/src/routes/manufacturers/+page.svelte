<script lang="ts">
	import { onMount } from 'svelte';
	import client from '$lib/api/client';
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import ManufacturerCard from '$lib/components/ManufacturerCard.svelte';
	import { pageTitle } from '$lib/constants';
	import { normalizeText } from '$lib/util';

	async function fetchManufacturers() {
		const { data } = await client.GET('/api/manufacturers/all/');
		return data ?? [];
	}

	type Manufacturers = Awaited<ReturnType<typeof fetchManufacturers>>;
	let manufacturers = $state<Manufacturers>([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			manufacturers = await fetchManufacturers();
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>{pageTitle('Manufacturers')}</title>
	<link rel="preload" as="fetch" href="/api/manufacturers/all/" crossorigin="anonymous" />
</svelte:head>

<FilterableGrid
	items={manufacturers}
	{loading}
	filterFn={(item, q) =>
		normalizeText(item.name).includes(q) ||
		(item.trade_name ? normalizeText(item.trade_name).includes(q) : false)}
	placeholder="Search manufacturers..."
	entityName="manufacturer"
>
	{#snippet children(mfr)}
		<ManufacturerCard
			slug={mfr.slug}
			name={mfr.name}
			thumbnailUrl={mfr.thumbnail_url}
			tradeName={mfr.trade_name}
			modelCount={mfr.model_count}
		/>
	{/snippet}
</FilterableGrid>
