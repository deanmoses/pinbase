<script lang="ts">
	import { afterNavigate, replaceState } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import SearchBox from '$lib/components/SearchBox.svelte';
	import SearchResults from '$lib/components/SearchResults.svelte';
	import { SITE_NAME } from '$lib/constants';
	import { normalizeText } from '$lib/util';

	const MIN_QUERY_LENGTH = 2;

	let searchQuery = $state('');
	let lastSyncedQ = '';

	// Sync URL → state. Uses window.location directly because page.url
	// may still reflect the prerendered URL (no query params) during hydration.
	function syncFromUrl() {
		const urlQ = new URLSearchParams(window.location.search).get('q') ?? '';
		searchQuery = urlQ;
		lastSyncedQ = urlQ.trim();
	}

	// onMount guarantees we read the real browser URL after hydration.
	onMount(syncFromUrl);

	// afterNavigate handles back/forward navigation (does NOT fire on replaceState).
	afterNavigate(syncFromUrl);

	// State → URL: update query string as user types.
	$effect(() => {
		const q = searchQuery.trim();
		if (q !== lastSyncedQ) {
			lastSyncedQ = q;
			const search = q ? `?q=${encodeURIComponent(q)}` : '';
			replaceState(`${resolve('/')}${search}`, {});
		}
	});

	let isSearching = $derived(normalizeText(searchQuery.trim()).length >= MIN_QUERY_LENGTH);
</script>

<svelte:head>
	<title>{SITE_NAME}</title>
	<link rel="preload" as="fetch" href="/api/titles/all/" crossorigin="anonymous" />
	<link rel="preload" as="fetch" href="/api/manufacturers/all/" crossorigin="anonymous" />
	<link rel="preload" as="fetch" href="/api/models/all/" crossorigin="anonymous" />
	<link rel="preload" as="fetch" href="/api/people/all/" crossorigin="anonymous" />
</svelte:head>

<div class="search-page">
	<div class="search-hero" class:compact={isSearching}>
		<h1 class="site-title">{SITE_NAME}</h1>
		{#if !isSearching}
			<p class="tagline">The open encyclopedia of pinball machines</p>
		{/if}
		<SearchBox bind:value={searchQuery} placeholder="Search titles, manufacturers, people..." />
	</div>

	<SearchResults query={searchQuery} />
</div>

<style>
	.search-page {
		padding: var(--size-5) 0;
	}

	.search-hero {
		text-align: center;
		padding: var(--size-10) 0 var(--size-6);
		transition: padding 0.2s ease;
	}

	.search-hero.compact {
		padding: var(--size-4) 0 var(--size-4);
	}

	.site-title {
		font-size: var(--font-size-8);
		font-weight: 700;
		color: var(--color-text-primary);
		margin-bottom: var(--size-2);
	}

	.compact .site-title {
		font-size: var(--font-size-5);
	}

	.tagline {
		font-size: var(--font-size-3);
		color: var(--color-text-muted);
		margin-bottom: var(--size-6);
	}
</style>
