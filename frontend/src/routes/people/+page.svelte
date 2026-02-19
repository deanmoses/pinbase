<script lang="ts">
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import PersonCard from '$lib/components/PersonCard.svelte';
	import { normalizeText } from '$lib/util';

	let { data } = $props();
</script>

<svelte:head>
	<title>People — The Flip Pinball DB</title>
</svelte:head>

<FilterableGrid
	items={data.people}
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
