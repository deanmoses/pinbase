<script lang="ts">
	import ClientFilteredGrid from '$lib/components/grid/ClientFilteredGrid.svelte';
	import ManufacturerCard from '$lib/components/cards/ManufacturerCard.svelte';

	let {
		manufacturers
	}: {
		manufacturers: {
			name: string;
			slug: string;
			model_count: number;
			thumbnail_url?: string | null;
		}[];
	} = $props();
</script>

<ClientFilteredGrid items={manufacturers} entityName="manufacturer">
	{#snippet children(mfr)}
		<ManufacturerCard
			slug={mfr.slug}
			name={mfr.name}
			thumbnailUrl={mfr.thumbnail_url}
			modelCount={mfr.model_count}
		/>
	{/snippet}
</ClientFilteredGrid>
