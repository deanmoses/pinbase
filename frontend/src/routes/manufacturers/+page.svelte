<script lang="ts">
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import ManufacturerCard from '$lib/components/ManufacturerCard.svelte';
	import { normalizeText } from '$lib/util';

	let { data } = $props();
</script>

<FilterableGrid
	items={data.manufacturers}
	filterFn={(item, q) =>
		normalizeText(item.name).includes(q) ||
		(item.trade_name ? normalizeText(item.trade_name).includes(q) : false)}
	title="Manufacturers — The Flip Pinball DB"
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
