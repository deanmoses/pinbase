<script lang="ts" generics="T">
	import type { Snippet } from 'svelte';
	import SearchBox from './SearchBox.svelte';
	import CardGrid from './CardGrid.svelte';
	import SkeletonCard from './SkeletonCard.svelte';
	import { normalizeText } from '$lib/util';

	const SEARCH_THRESHOLD = 12;
	const SKELETON_INDICES = Array.from({ length: 12 }, (_, i) => i);

	let {
		items,
		filterFields,
		loading = false,
		error = null,
		placeholder = 'Search...',
		entityName = 'result',
		entityNamePlural = `${entityName}s`,
		children
	}: {
		items: T[];
		filterFields: (item: T) => (string | number | null | undefined)[];
		loading?: boolean;
		error?: string | null;
		placeholder?: string;
		entityName?: string;
		entityNamePlural?: string;
		children: Snippet<[T]>;
	} = $props();

	const BATCH_SIZE = 100;

	let searchQuery = $state('');
	let visibleCount = $state(BATCH_SIZE);
	let sentinel: HTMLDivElement | undefined = $state();

	let filteredItems = $derived.by(() => {
		const q = normalizeText(searchQuery.trim());
		if (!q) return items;
		return items.filter((item) =>
			filterFields(item).some((field) => field != null && normalizeText(String(field)).includes(q))
		);
	});

	let showSearch = $derived(items.length >= SEARCH_THRESHOLD || searchQuery.trim() !== '');
	let visibleItems = $derived(filteredItems.slice(0, visibleCount));
	let hasMore = $derived(visibleCount < filteredItems.length);
	let countLabel = $derived(
		`${filteredItems.length.toLocaleString()} ${filteredItems.length === 1 ? entityName : entityNamePlural}`
	);

	// Reset visible count when search changes
	$effect(() => {
		void searchQuery;
		visibleCount = BATCH_SIZE;
	});

	// IntersectionObserver for infinite scroll
	$effect(() => {
		if (!sentinel) return;
		const observer = new IntersectionObserver(
			(entries) => {
				if (entries[0].isIntersecting && hasMore) {
					visibleCount += BATCH_SIZE;
				}
			},
			{ rootMargin: '200px' }
		);
		observer.observe(sentinel);
		return () => observer.disconnect();
	});
</script>

<div class="filterable-grid">
	{#if loading}
		{#if showSearch}
			<SearchBox {placeholder} disabled />
			<p class="count">{countLabel}</p>
		{/if}
		<CardGrid>
			{#each SKELETON_INDICES as i (i)}
				<SkeletonCard />
			{/each}
		</CardGrid>
	{:else if error}
		<p class="error">{error}</p>
	{:else}
		{#if showSearch}
			<SearchBox bind:value={searchQuery} {placeholder} />
			<p class="count">{countLabel}</p>
		{/if}

		<CardGrid>
			{#each visibleItems as item (item)}
				{@render children(item)}
			{/each}
		</CardGrid>

		{#if hasMore}
			<div class="sentinel" bind:this={sentinel}></div>
		{/if}
	{/if}
</div>

<style>
	.filterable-grid {
		padding: var(--size-5) 0;
	}

	.count {
		text-align: center;
		color: var(--color-text-muted);
		font-size: var(--font-size-1);
		margin-bottom: var(--size-4);
	}

	.error {
		text-align: center;
		color: var(--color-error);
		padding: var(--size-6) 0;
	}

	.sentinel {
		height: 1px;
	}
</style>
