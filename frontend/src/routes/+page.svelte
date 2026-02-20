<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';
	import { SITE_NAME } from '$lib/constants';
	import { normalizeText } from '$lib/util';

	const models = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/models/all/');
		return data ?? [];
	}, []);
</script>

<svelte:head>
	<title>{SITE_NAME}</title>
	<link rel="preload" as="fetch" href="/api/models/all/" crossorigin="anonymous" />
</svelte:head>

<FilterableGrid
	items={models.data}
	loading={models.loading}
	error={models.error}
	filterFn={(item, q) =>
		normalizeText(item.name).includes(q) ||
		(item.manufacturer_name ? normalizeText(item.manufacturer_name).includes(q) : false)}
	placeholder="Search machines..."
	entityName="machine"
>
	{#snippet children(model)}
		<MachineCard
			slug={model.slug}
			name={model.name}
			thumbnailUrl={model.thumbnail_url}
			manufacturerName={model.manufacturer_name}
			year={model.year}
			machineType={model.machine_type}
		/>
	{/snippet}
</FilterableGrid>
