<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import AwardCard from '$lib/components/AwardCard.svelte';
	import { pageTitle } from '$lib/constants';

	const awards = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/awards/all/');
		return data ?? [];
	}, []);
</script>

<svelte:head>
	<title>{pageTitle('Awards')}</title>
	<link rel="preload" as="fetch" href="/api/awards/all/" crossorigin="anonymous" />
</svelte:head>

<FilterableGrid
	items={awards.data}
	loading={awards.loading}
	error={awards.error}
	filterFields={(item) => [item.name]}
	placeholder="Search awards..."
	entityName="award"
>
	{#snippet children(award)}
		<AwardCard slug={award.slug} name={award.name} recipientCount={award.recipient_count} />
	{/snippet}
</FilterableGrid>
