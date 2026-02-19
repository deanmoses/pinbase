<script lang="ts">
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';
	import { SITE_NAME } from '$lib/constants';
	import { normalizeText } from '$lib/util';

	let { data } = $props();
</script>

<svelte:head>
	<title>{SITE_NAME}</title>
</svelte:head>

<FilterableGrid
	items={data.models}
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
