<script lang="ts">
	import CardGrid from '$lib/components/CardGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';

	let { data } = $props();
	let group = $derived(data.group);
</script>

<svelte:head>
	<title>{group.name} — The Flip Pinball DB</title>
</svelte:head>

<article>
	<header>
		<h1>{group.name}</h1>
		{#if group.shortname && group.shortname !== group.name}
			<p class="shortname">{group.shortname}</p>
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

	.shortname {
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
