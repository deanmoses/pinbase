<script lang="ts">
	import ListPage from '$lib/components/ListPage.svelte';
	import CardGrid from '$lib/components/CardGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';
	import { PAGE_SIZES } from '$lib/api/pagination';

	let { data } = $props();
</script>

<ListPage
	title="Models"
	count={data.result.count}
	pageSize={PAGE_SIZES.models}
	entityName="model"
	search
>
	<CardGrid>
		{#each data.result.items as model (model.slug)}
			<MachineCard
				slug={model.slug}
				name={model.name}
				thumbnailUrl={model.thumbnail_url}
				manufacturerName={model.manufacturer_name}
				year={model.year}
				machineType={model.machine_type}
				ipdbRating={model.ipdb_rating}
				pinsideRating={model.pinside_rating}
			/>
		{/each}
	</CardGrid>
</ListPage>
