<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import PersonCard from '$lib/components/PersonCard.svelte';
	import { pageTitle } from '$lib/constants';
	import { normalizeText } from '$lib/util';

	const people = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/people/all/');
		return data ?? [];
	}, []);
</script>

<svelte:head>
	<title>{pageTitle('People')}</title>
	<link rel="preload" as="fetch" href="/api/people/all/" crossorigin="anonymous" />
</svelte:head>

<FilterableGrid
	items={people.data}
	loading={people.loading}
	error={people.error}
	filterFn={(item, q) => normalizeText(item.name).includes(q)}
	placeholder="Search people..."
	entityName="person"
	entityNamePlural="people"
>
	{#snippet children(person)}
		<PersonCard
			slug={person.slug}
			name={person.name}
			thumbnailUrl={person.thumbnail_url}
			creditCount={person.credit_count}
		/>
	{/snippet}
</FilterableGrid>
