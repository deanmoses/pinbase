<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import TaxonomyListPage from '$lib/components/TaxonomyListPage.svelte';

	const loader = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/tags/');
		return data ?? [];
	}, []);
</script>

<TaxonomyListPage
	title="Tags"
	subtitle="Descriptive tags applied to pinball machines."
	basePath="/tags"
	items={loader.data}
	loading={loader.loading}
	error={loader.error}
/>
