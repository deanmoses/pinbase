<script lang="ts">
	import ListPage from '$lib/components/ListPage.svelte';
	import CardGrid from '$lib/components/CardGrid.svelte';
	import GroupCard from '$lib/components/GroupCard.svelte';
	import { PAGE_SIZES } from '$lib/api/pagination';

	let { data } = $props();
</script>

<ListPage
	title="Groups"
	count={data.result.count}
	pageSize={PAGE_SIZES.groups}
	entityName="group"
	search
>
	<CardGrid>
		{#each data.result.items as group (group.slug)}
			<GroupCard
				slug={group.slug}
				name={group.name}
				thumbnailUrl={group.thumbnail_url}
				shortname={group.shortname}
				machineCount={group.machine_count}
			/>
		{/each}
	</CardGrid>
</ListPage>
