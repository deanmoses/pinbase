<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import GameCard from '$lib/components/GameCard.svelte';
	import { pageTitle } from '$lib/constants';

	const games = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/games/all/');
		return data ?? [];
	}, []);
</script>

<svelte:head>
	<title>{pageTitle('Games')}</title>
	<link rel="preload" as="fetch" href="/api/games/all/" crossorigin="anonymous" />
</svelte:head>

<FilterableGrid
	items={games.data}
	loading={games.loading}
	error={games.error}
	filterFields={(item) => [item.name, item.short_name, item.manufacturer_name, item.year]}
	placeholder="Search games..."
	entityName="game"
>
	{#snippet children(game)}
		<GameCard
			slug={game.slug}
			name={game.name}
			thumbnailUrl={game.thumbnail_url}
			short_name={game.short_name}
			machineCount={game.machine_count}
		/>
	{/snippet}
</FilterableGrid>
