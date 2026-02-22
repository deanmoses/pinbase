<script lang="ts">
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';

	let { data } = $props();
	let mfr = $derived(data.manufacturer);
</script>

{#if mfr.models.length === 0}
	<p class="empty">No models listed for this manufacturer.</p>
{:else}
	<section>
		<h2>Models ({mfr.models.length})</h2>
		<FilterableGrid
			items={mfr.models}
			filterFields={(item) => [item.name]}
			placeholder="Search models..."
			entityName="model"
		>
			{#snippet children(model)}
				<MachineCard
					slug={model.slug}
					name={model.name}
					thumbnailUrl={model.thumbnail_url}
					year={model.year}
					machineType={model.machine_type}
				/>
			{/snippet}
		</FilterableGrid>
	</section>
{/if}

<style>
	h2 {
		font-size: var(--font-size-3);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	section {
		margin-bottom: var(--size-6);
	}

	.empty {
		color: var(--color-text-muted);
		font-size: var(--font-size-2);
		padding: var(--size-8) 0;
		text-align: center;
	}
</style>
