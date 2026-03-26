<script lang="ts">
	import ClientFilteredGrid from '$lib/components/grid/ClientFilteredGrid.svelte';
	import TitleCard from '$lib/components/cards/TitleCard.svelte';

	let { data } = $props();
	let system = $derived(data.system);
</script>

{#if system.titles.length === 0}
	<p class="empty">No titles on this system.</p>
{:else}
	<section>
		<h2>Titles ({system.titles.length})</h2>
		<ClientFilteredGrid items={system.titles} showCount={false}>
			{#snippet children(title)}
				<TitleCard
					slug={title.slug}
					name={title.name}
					thumbnailUrl={title.thumbnail_url}
					manufacturerName={title.manufacturer_name}
					year={title.year}
				/>
			{/snippet}
		</ClientFilteredGrid>
	</section>
{/if}

<style>
	h2 {
		font-size: var(--font-size-3);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	.empty {
		color: var(--color-text-muted);
		font-size: var(--font-size-2);
		padding: var(--size-8) 0;
		text-align: center;
	}
</style>
