<script lang="ts">
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';

	let { data } = $props();
	let person = $derived(data.person);
</script>

{#if person.bio}
	<section class="bio">
		<p>{person.bio}</p>
	</section>
{/if}

{#if person.machines.length > 0}
	<FilterableGrid
		items={person.machines}
		filterFields={(item) => [item.model_name]}
		placeholder="Search models..."
		entityName="machine"
	>
		{#snippet children(machine)}
			<MachineCard
				slug={machine.model_slug}
				name={machine.model_name}
				thumbnailUrl={machine.thumbnail_url}
				roles={machine.roles}
			/>
		{/snippet}
	</FilterableGrid>
{:else}
	<p class="empty">No credits listed.</p>
{/if}

<style>
	.bio p {
		font-size: var(--font-size-2);
		color: var(--color-text-primary);
		line-height: var(--font-lineheight-3);
		margin-bottom: var(--size-6);
	}

	.empty {
		color: var(--color-text-muted);
		font-size: var(--font-size-2);
		padding: var(--size-8) 0;
		text-align: center;
	}
</style>
