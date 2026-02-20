<script lang="ts">
	import { onMount } from 'svelte';
	import client from '$lib/api/client';
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';
	import { SITE_NAME } from '$lib/constants';
	import { normalizeText } from '$lib/util';

	async function fetchModels() {
		const { data } = await client.GET('/api/models/all/');
		return data ?? [];
	}

	type Models = Awaited<ReturnType<typeof fetchModels>>;
	let models = $state<Models>([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			models = await fetchModels();
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>{SITE_NAME}</title>
	<link rel="preload" as="fetch" href="/api/models/all/" crossorigin="anonymous" />
</svelte:head>

<FilterableGrid
	items={models}
	{loading}
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
