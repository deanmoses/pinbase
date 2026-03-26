<script lang="ts">
	import { resolve } from '$app/paths';
	import MachineCard from '$lib/components/cards/MachineCard.svelte';
	import ModelDetailBody from '$lib/components/ModelDetailBody.svelte';
	import CreditsList from '$lib/components/CreditsList.svelte';
	import TabNav from '$lib/components/TabNav.svelte';
	import Tab from '$lib/components/Tab.svelte';

	let { data } = $props();
	let title = $derived(data.title);
	let md = $derived(title.model_detail);

	let activeTab = $state<'people' | 'machines'>('people');
</script>

{#if md}
	<ModelDetailBody model={md} />
{:else}
	<TabNav>
		<Tab active={activeTab === 'machines'} onclick={() => (activeTab = 'machines')}>
			Models ({title.machines.length +
				title.machines.reduce((n, m) => n + (m.variants?.length ?? 0), 0)})
		</Tab>
		<Tab active={activeTab === 'people'} onclick={() => (activeTab = 'people')}>People</Tab>
	</TabNav>

	{#if activeTab === 'machines'}
		{#if title.machines.length === 0}
			<p class="empty">No models in this title.</p>
		{:else}
			{#each title.machines as machine (machine.slug)}
				<div class="model-group">
					<MachineCard
						slug={machine.slug}
						name={machine.name}
						thumbnailUrl={machine.thumbnail_url}
						manufacturerName={machine.manufacturer?.name}
						year={machine.year}
					/>
					{#if machine.variants.length > 0}
						<ul class="variant-list">
							{#each machine.variants as variant (variant.slug)}
								<li>
									<a href={resolve(`/models/${variant.slug}`)}>{variant.name}</a>
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			{/each}
		{/if}
	{:else if activeTab === 'people'}
		<CreditsList credits={title.credits} />
	{/if}
{/if}

<style>
	.empty {
		color: var(--color-text-muted);
		font-size: var(--font-size-2);
		padding: var(--size-8) 0;
		text-align: center;
	}

	.model-group {
		margin-bottom: var(--size-4);
	}

	.variant-list {
		list-style: none;
		padding: 0 0 0 var(--size-6);
		margin: var(--size-2) 0 0 0;
	}

	.variant-list li {
		padding: var(--size-1) 0;
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
	}

	.variant-list li::before {
		content: '└';
		margin-right: var(--size-2);
		color: var(--color-text-muted);
	}
</style>
