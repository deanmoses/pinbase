<script lang="ts">
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';
	import { normalizeText } from '$lib/util';

	let { data } = $props();
</script>

<FilterableGrid
	items={data.models}
	filterFn={(item, q) =>
		normalizeText(item.name).includes(q) ||
		(item.manufacturer_name ? normalizeText(item.manufacturer_name).includes(q) : false)}
	title="The Flip Pinball DB — Every pinball machine ever made"
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
