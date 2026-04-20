<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import TaxonomyListPage from '$lib/components/TaxonomyListPage.svelte';

	const loader = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/display-types/');
		return data ?? [];
	}, []);
</script>

<TaxonomyListPage
	title="Display Types"
	subtitle="Score display technologies used in pinball machines."
	basePath="/display-types"
	items={loader.data}
	loading={loader.loading}
	error={loader.error}
	createHref="/display-types/new"
/>
