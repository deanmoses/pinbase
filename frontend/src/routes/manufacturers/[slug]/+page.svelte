<script lang="ts">
	import DetailPage from '$lib/components/DetailPage.svelte';
	import FilterableGrid from '$lib/components/FilterableGrid.svelte';
	import MachineCard from '$lib/components/MachineCard.svelte';
	import { normalizeText } from '$lib/util';

	let { data } = $props();
	let mfr = $derived(data.manufacturer);
	let ipdbId = $derived(
		mfr.entities.find((e: { ipdb_manufacturer_id?: number | null }) => e.ipdb_manufacturer_id)
			?.ipdb_manufacturer_id
	);
</script>

<DetailPage title={mfr.name}>
	{#snippet subtitle()}
		{#if mfr.trade_name && mfr.trade_name !== mfr.name}
			<p class="trade-name">Trade name: {mfr.trade_name}</p>
		{/if}
	{/snippet}

	{#if mfr.models.length === 0}
		<p class="empty">No models listed for this manufacturer.</p>
	{:else}
		<section>
			<h2>Models ({mfr.models.length})</h2>
			<FilterableGrid
				items={mfr.models}
				filterFn={(item, q) => normalizeText(item.name).includes(q)}
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

	{#if ipdbId}
		<footer class="external-ids">
			<a
				href="https://www.ipdb.org/search.pl?any=&searchtype=advanced&mfgid={ipdbId}"
				target="_blank"
				rel="noopener"
			>
				IPDB
			</a>
		</footer>
	{/if}
</DetailPage>

<style>
	.trade-name {
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
		margin-top: var(--size-2);
	}

	.external-ids {
		display: flex;
		gap: var(--size-4);
		padding-top: var(--size-4);
		margin-top: var(--size-6);
		border-top: 1px solid var(--color-border-soft);
	}
</style>
