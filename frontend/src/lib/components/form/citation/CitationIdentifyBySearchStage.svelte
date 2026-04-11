<script lang="ts">
	import client from '$lib/api/client';
	import { parseIdentifierInput, type ParentContext, type ChildSource } from './citation-types';
	import DropdownHeader from '../DropdownHeader.svelte';
	import DropdownItem from '../DropdownItem.svelte';
	import DropdownSearchInput from '../DropdownSearchInput.svelte';

	let {
		parentContext,
		onsourceidentified,
		onsourcecreatestarted,
		oncancel,
		onback
	}: {
		parentContext: ParentContext;
		onsourceidentified: (child: {
			sourceId: number;
			sourceName: string;
			skipLocator: boolean;
		}) => void;
		onsourcecreatestarted: (prefillName: string) => void;
		oncancel: () => void;
		onback: () => void;
	} = $props();

	// -----------------------------------------------------------------------
	// State
	// -----------------------------------------------------------------------

	let filterQuery = $state('');
	let children = $state<ChildSource[]>([]);
	let loading = $state(true);
	let loadError = $state(false);
	let activeIndex = $state(-1);
	let searchInputEl: HTMLInputElement | undefined = $state();
	let resultsListEl: HTMLDivElement | undefined = $state();

	// -----------------------------------------------------------------------
	// Fetch children on mount
	// -----------------------------------------------------------------------

	$effect(() => {
		if (searchInputEl) {
			searchInputEl.focus();
		}
	});

	$effect(() => {
		if (activeIndex < 0 || !resultsListEl) return;
		resultsListEl.querySelector('[data-active="true"]')?.scrollIntoView({ block: 'nearest' });
	});

	$effect(() => {
		fetchChildren();
	});

	async function fetchChildren() {
		loading = true;
		loadError = false;
		const { data, error } = await client.GET('/api/citation-sources/{source_id}/', {
			params: { path: { source_id: parentContext.id } }
		});
		if (error || !data) {
			loading = false;
			loadError = true;
			return;
		}
		// Sort newest-first by year (nulls at end)
		children = [...(data.children as ChildSource[])].sort((a, b) => {
			if (a.year == null && b.year == null) return 0;
			if (a.year == null) return 1;
			if (b.year == null) return -1;
			return b.year - a.year;
		});
		loading = false;
	}

	// -----------------------------------------------------------------------
	// Filtering and identifier matching
	// -----------------------------------------------------------------------

	let parsedIdentifier = $derived(
		parseIdentifierInput(parentContext.source_type, parentContext.identifier_key, filterQuery)
	);

	let identifierMatch = $derived.by(() => {
		if (!parsedIdentifier) return null;
		return (
			children.find((c) => {
				// Match by ISBN
				if (c.isbn) {
					const normalizedIsbn = c.isbn.replace(/[-\s]/g, '').toUpperCase();
					if (normalizedIsbn === parsedIdentifier) return true;
				}
				// Match by URL
				for (const url of c.urls) {
					const parsed = parseIdentifierInput(
						parentContext.source_type,
						parentContext.identifier_key,
						url
					);
					if (parsed === parsedIdentifier) return true;
				}
				return false;
			}) ?? null
		);
	});

	let filteredChildren = $derived.by(() => {
		if (!filterQuery.trim()) return children;
		// If we found an identifier match, show just that child
		if (identifierMatch) return [identifierMatch];
		// Otherwise text-filter across name, year, isbn
		const q = filterQuery.toLowerCase();
		return children.filter((c) => {
			if (c.name.toLowerCase().includes(q)) return true;
			if (c.year != null && String(c.year).includes(q)) return true;
			if (c.isbn && c.isbn.toLowerCase().includes(q)) return true;
			return false;
		});
	});

	// -----------------------------------------------------------------------
	// Item index math
	// -----------------------------------------------------------------------

	let showCreateNew = $derived(filterQuery.trim().length > 0);
	let createNewIndex = $derived(filteredChildren.length);
	let totalItems = $derived(filteredChildren.length + (showCreateNew ? 1 : 0));

	// -----------------------------------------------------------------------
	// Actions
	// -----------------------------------------------------------------------

	function selectChild(child: ChildSource) {
		onsourceidentified({
			sourceId: child.id,
			sourceName: child.name,
			skipLocator: child.skip_locator
		});
	}

	function startCreate() {
		onsourcecreatestarted(filterQuery);
	}

	// -----------------------------------------------------------------------
	// Input handling
	// -----------------------------------------------------------------------

	function handleSearchInput(e: Event) {
		filterQuery = (e.currentTarget as HTMLInputElement).value;
		activeIndex = -1;
	}

	// -----------------------------------------------------------------------
	// Keyboard navigation
	// -----------------------------------------------------------------------

	function handleKeydown(e: KeyboardEvent) {
		switch (e.key) {
			case 'ArrowDown':
				e.preventDefault();
				activeIndex = Math.min(activeIndex + 1, totalItems - 1);
				break;
			case 'ArrowUp':
				e.preventDefault();
				activeIndex = Math.max(activeIndex - 1, -1);
				break;
			case 'Enter':
				e.preventDefault();
				if (activeIndex < 0) break;
				if (activeIndex < createNewIndex) {
					selectChild(filteredChildren[activeIndex]);
				} else if (showCreateNew && activeIndex === createNewIndex) {
					startCreate();
				}
				break;
			case 'Escape':
				e.preventDefault();
				oncancel();
				break;
			case 'Backspace':
				if (!filterQuery) {
					e.preventDefault();
					onback();
				}
				break;
			case 'ArrowLeft':
				if (searchInputEl && searchInputEl.selectionStart === 0) {
					e.preventDefault();
					onback();
				}
				break;
		}
	}
</script>

<DropdownHeader {onback}>{parentContext.name}</DropdownHeader>
<DropdownSearchInput
	placeholder="Filter editions..."
	value={filterQuery}
	oninput={handleSearchInput}
	onkeydown={handleKeydown}
	bind:inputRef={searchInputEl}
/>
<div class="results-list" bind:this={resultsListEl}>
	{#if loading}
		<div class="status-msg">Loading…</div>
	{:else if loadError}
		<div class="status-msg status-error">Failed to load editions.</div>
	{:else}
		{#each filteredChildren as child, i (child.id)}
			<DropdownItem
				active={i === activeIndex}
				onselect={() => selectChild(child)}
				onhover={() => (activeIndex = i)}
			>
				<span class="item-label">{child.name}{child.year != null ? ` — ${child.year}` : ''}</span>
				{#if identifierMatch?.id === child.id}
					<span class="item-desc">Match</span>
				{/if}
			</DropdownItem>
		{/each}
		{#if showCreateNew}
			<DropdownItem
				active={activeIndex === createNewIndex}
				onselect={startCreate}
				onhover={() => (activeIndex = createNewIndex)}
			>
				<span class="item-label create-new">+ Create "{filterQuery}"</span>
			</DropdownItem>
		{/if}
		{#if !filteredChildren.length && !filterQuery.trim()}
			<div class="status-msg">No editions yet — type to create one</div>
		{:else if !filteredChildren.length && filterQuery.trim()}
			<div class="status-msg">No matches</div>
		{/if}
	{/if}
</div>

<style>
	.item-label {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.item-desc {
		color: var(--color-text-muted);
		font-size: var(--font-size-0);
		flex-shrink: 0;
	}

	.create-new {
		color: var(--color-text-muted);
		font-style: italic;
	}

	.results-list {
		max-height: 14rem;
		overflow-y: auto;
	}

	.status-msg {
		padding: var(--size-3);
		color: var(--color-text-muted);
		text-align: center;
		font-size: var(--font-size-1);
	}

	.status-error {
		color: var(--color-danger, #c00);
	}
</style>
