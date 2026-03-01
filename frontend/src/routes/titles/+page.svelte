<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import TitleCard from '$lib/components/TitleCard.svelte';
	import { pageTitle } from '$lib/constants';

	const titles = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/titles/all/');
		return data ?? [];
	}, []);
</script>

<svelte:head>
	<title>{pageTitle('Titles')}</title>
	<link rel="preload" as="fetch" href="/api/titles/all/" crossorigin="anonymous" />
</svelte:head>

<FilterableGrid
	items={titles.data}
	loading={titles.loading}
	error={titles.error}
	filterFields={(item) => [item.name, item.short_name, item.manufacturer_name, item.year]}
	placeholder="Search titles..."
	entityName="title"
>
	{#snippet children(title)}
		<TitleCard
			slug={title.slug}
			name={title.name}
			thumbnailUrl={title.thumbnail_url}
			short_name={title.short_name}
		/>
	{/snippet}
</FilterableGrid>
