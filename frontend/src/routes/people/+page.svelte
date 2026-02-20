<script lang="ts">
	import { onMount } from 'svelte';
	import client from '$lib/api/client';
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import PersonCard from '$lib/components/PersonCard.svelte';
	import { pageTitle } from '$lib/constants';
	import { normalizeText } from '$lib/util';

	async function fetchPeople() {
		const { data } = await client.GET('/api/people/all/');
		return data ?? [];
	}

	type People = Awaited<ReturnType<typeof fetchPeople>>;
	let people = $state<People>([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			people = await fetchPeople();
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>{pageTitle('People')}</title>
	<link rel="preload" as="fetch" href="/api/people/all/" crossorigin="anonymous" />
</svelte:head>

<FilterableGrid
	items={people}
	{loading}
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
