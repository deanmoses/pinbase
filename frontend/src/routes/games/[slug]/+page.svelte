<script lang="ts">
	import { resolve } from '$app/paths';
	import CardGrid from '$lib/components/CardGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';
	import { pageTitle } from '$lib/constants';

	let { data } = $props();
	let game = $derived(data.game);
</script>

<svelte:head>
	<title>{pageTitle(game.name)}</title>
</svelte:head>

<article>
	<header>
		<h1>{game.name}</h1>
		{#if game.short_name && game.short_name !== game.name}
			<p class="short_name">{game.short_name}</p>
		{/if}
		{#if game.series.length > 0}
			<p class="series-list">
				Series:
				{#each game.series as s, i (s.slug)}
					{#if i > 0},{/if}
					<a href={resolve(`/series/${s.slug}`)}>{s.name}</a>
				{/each}
			</p>
		{/if}
	</header>

	{#if game.machines.length === 0}
		<p class="empty">No machines in this game.</p>
	{:else}
		<section>
			<h2>Machines ({game.machines.length})</h2>
			<CardGrid>
				{#each game.machines as machine (machine.slug)}
					<MachineCard
						slug={machine.slug}
						name={machine.name}
						thumbnailUrl={machine.thumbnail_url}
						manufacturerName={machine.manufacturer_name}
						year={machine.year}
						machineType={machine.machine_type}
					/>
				{/each}
			</CardGrid>
		</section>
	{/if}
</article>

<style>
	article {
		max-width: 64rem;
	}

	header {
		margin-bottom: var(--size-6);
	}

	h1 {
		font-size: var(--font-size-7);
		font-weight: 700;
		color: var(--color-text-primary);
		margin-bottom: var(--size-2);
	}

	.short_name {
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
	}

	.series-list {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
		margin-top: var(--size-1);
	}

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
