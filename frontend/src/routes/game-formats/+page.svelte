<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import TaxonomyListPage from '$lib/components/TaxonomyListPage.svelte';

	const loader = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/game-formats/');
		return data ?? [];
	}, []);
</script>

<TaxonomyListPage
	title="Game Formats"
	subtitle="Different game play formats in pinball."
	basePath="/game-formats"
	items={loader.data}
	loading={loader.loading}
	error={loader.error}
	createHref="/game-formats/new"
/>
