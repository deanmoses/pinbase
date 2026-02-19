<script lang="ts">
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import GroupCard from '$lib/components/GroupCard.svelte';
	import { normalizeText } from '$lib/util';

	let { data } = $props();
</script>

<FilterableGrid
	items={data.groups}
	filterFn={(item, q) =>
		normalizeText(item.name).includes(q) ||
		(item.shortname ? normalizeText(item.shortname).includes(q) : false)}
	title="Groups — The Flip Pinball DB"
	placeholder="Search groups..."
	entityName="group"
>
	{#snippet children(group)}
		<GroupCard
			slug={group.slug}
			name={group.name}
			thumbnailUrl={group.thumbnail_url}
			shortname={group.shortname}
			machineCount={group.machine_count}
		/>
	{/snippet}
</FilterableGrid>
