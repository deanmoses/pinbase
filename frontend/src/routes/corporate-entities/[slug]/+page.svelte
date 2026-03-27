<script lang="ts">
	import SearchableGrid from '$lib/components/grid/SearchableGrid.svelte';
	import TitleCard from '$lib/components/cards/TitleCard.svelte';

	let { data } = $props();
	let ce = $derived(data.corporateEntity);
</script>

{#if ce.titles.length === 0}
	<p class="empty">No titles listed for this corporate entity.</p>
{:else}
	<SearchableGrid
		items={ce.titles}
		filterFields={(item) => [item.name]}
		placeholder="Search titles..."
		entityName="title"
	>
		{#snippet children(title)}
			<TitleCard
				slug={title.slug}
				name={title.name}
				thumbnailUrl={title.thumbnail_url}
				year={title.year}
			/>
		{/snippet}
	</SearchableGrid>
{/if}

<style>
	.empty {
		color: var(--color-text-muted);
		font-size: var(--font-size-2);
		padding: var(--size-8) 0;
		text-align: center;
	}
</style>
