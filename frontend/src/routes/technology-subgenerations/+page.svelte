<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import TaxonomyListPage from '$lib/components/TaxonomyListPage.svelte';

	const loader = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/technology-subgenerations/');
		return data ?? [];
	}, []);
</script>

<TaxonomyListPage
	title="Technology Subgenerations"
	subtitle="Subdivisions within major pinball technology eras."
	basePath="/technology-subgenerations"
	items={loader.data}
	loading={loader.loading}
	error={loader.error}
/>
