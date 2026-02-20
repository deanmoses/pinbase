<script lang="ts">
	import { onMount } from 'svelte';
	import client from '$lib/api/client';
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import GroupCard from '$lib/components/GroupCard.svelte';
	import { pageTitle } from '$lib/constants';
	import { normalizeText } from '$lib/util';

	async function fetchGroups() {
		const { data } = await client.GET('/api/groups/all/');
		return data ?? [];
	}

	type Groups = Awaited<ReturnType<typeof fetchGroups>>;
	let groups = $state<Groups>([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			groups = await fetchGroups();
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>{pageTitle('Groups')}</title>
	<link rel="preload" as="fetch" href="/api/groups/all/" crossorigin="anonymous" />
</svelte:head>

<FilterableGrid
	items={groups}
	{loading}
	filterFn={(item, q) =>
		normalizeText(item.name).includes(q) ||
		(item.shortname ? normalizeText(item.shortname).includes(q) : false)}
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
