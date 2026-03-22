<script lang="ts">
	import { resolve } from '$app/paths';
	import client from '$lib/api/client';
	import { createPaginatedLoader } from '$lib/paginated-loader.svelte';
	import EntityDetailLayout from '$lib/components/EntityDetailLayout.svelte';
	import PaginatedSection from '$lib/components/grid/PaginatedSection.svelte';
	import MachineCard from '$lib/components/cards/MachineCard.svelte';

	let { data } = $props();
	let profile = $derived(data.profile);

	const machines = createPaginatedLoader(async (page) => {
		const { data: result } = await client.GET('/api/models/', {
			params: { query: { feature: profile.slug, page } }
		});
		return result ?? { items: [], count: 0 };
	});
</script>

<EntityDetailLayout
	name={profile.name}
	descriptionHtml={profile.description_html}
	breadcrumbs={[{ label: 'Gameplay Features', href: '/gameplay-features' }]}
>
	{#if profile.aliases && profile.aliases.length > 0}
		<section class="also-known-as">
			<h2>Also known as</h2>
			<p>{profile.aliases.join(', ')}</p>
		</section>
	{/if}

	{#if profile.children && profile.children.length > 0}
		<section>
			<h2>Child features ({profile.children.length})</h2>
			<ul class="feature-list">
				{#each profile.children as child (child.slug)}
					<li><a href={resolve(`/gameplay-features/${child.slug}`)}>{child.name}</a></li>
				{/each}
			</ul>
		</section>
	{/if}

	<PaginatedSection
		loader={machines}
		heading="Machines"
		emptyMessage="No machines with this feature."
	>
		{#snippet children(machine)}
			<MachineCard
				slug={machine.slug}
				name={machine.name}
				thumbnailUrl={machine.thumbnail_url}
				manufacturerName={machine.manufacturer_name}
				year={machine.year}
			/>
		{/snippet}
	</PaginatedSection>
</EntityDetailLayout>

<style>
	h2 {
		font-size: var(--font-size-3);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	.also-known-as {
		margin-bottom: var(--size-6);
	}

	.also-known-as p {
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
	}

	.feature-list {
		list-style: none;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--size-2) var(--size-4);
		margin-bottom: var(--size-6);
	}
</style>
