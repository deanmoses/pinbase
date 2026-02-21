<script lang="ts">
	import CardGrid from '$lib/components/CardGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';
	import { pageTitle } from '$lib/constants';

	let { data } = $props();
	let group = $derived(data.group);
</script>

<svelte:head>
	<title>{pageTitle(group.name)}</title>
</svelte:head>

<article>
	<header>
		<h1>{group.name}</h1>
		{#if group.short_name && group.short_name !== group.name}
			<p class="short_name">{group.short_name}</p>
		{/if}
	</header>

	{#if group.machines.length === 0}
		<p class="empty">No machines in this group.</p>
	{:else}
		<section>
			<h2>Machines ({group.machines.length})</h2>
			<CardGrid>
				{#each group.machines as machine (machine.slug)}
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
