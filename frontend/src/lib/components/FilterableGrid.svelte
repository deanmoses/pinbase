<script lang="ts" generics="T">
	import type { Snippet } from 'svelte';
	import { faMagnifyingGlass } from '@fortawesome/free-solid-svg-icons';
	import FaIcon from './FaIcon.svelte';
	import CardGrid from './CardGrid.svelte';
	import { normalizeText } from '$lib/util';

	let {
		items,
		filterFn,
		title,
		placeholder = 'Search...',
		entityName = 'result',
		entityNamePlural = `${entityName}s`,
		children
	}: {
		items: T[];
		filterFn: (item: T, query: string) => boolean;
		title: string;
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
		return items.filter((item) => filterFn(item, q));
	});

	let visibleItems = $derived(filteredItems.slice(0, visibleCount));
	let hasMore = $derived(visibleCount < filteredItems.length);
	let countLabel = $derived(
		`${filteredItems.length.toLocaleString()} ${filteredItems.length === 1 ? entityName : entityNamePlural}`
	);

	// Reset visible count when search changes
	let prevQuery = $state(searchQuery);
	$effect(() => {
		if (searchQuery !== prevQuery) {
			prevQuery = searchQuery;
			visibleCount = BATCH_SIZE;
		}
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

<svelte:head>
	<title>{title}</title>
</svelte:head>

<div class="filterable-grid">
	<form class="search-box" onsubmit={(e) => e.preventDefault()}>
		<FaIcon icon={faMagnifyingGlass} class="search-icon" />
		<input type="search" {placeholder} aria-label={placeholder} bind:value={searchQuery} />
	</form>

	<p class="count">{countLabel}</p>

	<CardGrid>
		{#each visibleItems as item (item)}
			{@render children(item)}
		{/each}
	</CardGrid>

	{#if hasMore}
		<div class="sentinel" bind:this={sentinel}></div>
	{/if}
</div>

<style>
	.filterable-grid {
		padding: var(--size-5) 0;
	}

	.search-box {
		position: relative;
		max-width: 36rem;
		margin: 0 auto var(--size-4);
	}

	:global(.search-icon) {
		position: absolute;
		left: var(--size-4);
		top: 50%;
		transform: translateY(-50%);
		width: 1rem;
		height: 1rem;
		color: var(--color-text-muted);
		pointer-events: none;
	}

	input[type='search'] {
		width: 100%;
		padding: var(--size-3) var(--size-4) var(--size-3) var(--size-9);
		font-size: var(--font-size-2);
		font-family: var(--font-body);
		background-color: var(--color-input-bg);
		color: var(--color-text-primary);
		border: 1px solid var(--color-input-border);
		border-radius: var(--radius-3);
		transition:
			border-color 0.15s var(--ease-2),
			box-shadow 0.15s var(--ease-2);
	}

	input[type='search']:focus {
		outline: none;
		border-color: var(--color-input-focus);
		box-shadow: 0 0 0 3px var(--color-input-focus-ring);
	}

	input[type='search']::placeholder {
		color: var(--color-text-muted);
	}

	.count {
		text-align: center;
		color: var(--color-text-muted);
		font-size: var(--font-size-1);
		margin-bottom: var(--size-4);
	}

	.sentinel {
		height: 1px;
	}
</style>
