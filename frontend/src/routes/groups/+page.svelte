<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import GroupCard from '$lib/components/GroupCard.svelte';
	import { pageTitle } from '$lib/constants';

	const groups = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/groups/all/');
		return data ?? [];
	}, []);
</script>

<svelte:head>
	<title>{pageTitle('Groups')}</title>
	<link rel="preload" as="fetch" href="/api/groups/all/" crossorigin="anonymous" />
</svelte:head>

<FilterableGrid
	items={groups.data}
	loading={groups.loading}
	error={groups.error}
	filterFields={(item) => [item.name, item.short_name]}
	placeholder="Search groups..."
	entityName="group"
>
	{#snippet children(group)}
		<GroupCard
			slug={group.slug}
			name={group.name}
			thumbnailUrl={group.thumbnail_url}
			short_name={group.short_name}
			machineCount={group.machine_count}
		/>
	{/snippet}
</FilterableGrid>
