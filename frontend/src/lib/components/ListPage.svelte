<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import type { Snippet } from 'svelte';
	import SearchBar from './SearchBar.svelte';
	import Pagination from './Pagination.svelte';

	let {
		title,
		count,
		pageSize,
		entityName,
		entityNamePlural = `${entityName}s`,
		search = false,
		children
	}: {
		title: string;
		count: number;
		pageSize: number;
		entityName: string;
		entityNamePlural?: string;
		search?: boolean;
		children: Snippet;
	} = $props();

	function gotoPage(p: number) {
		const url = new URL(page.url);
		if (p > 1) {
			url.searchParams.set('page', String(p));
		} else {
			url.searchParams.delete('page');
		}
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- same-page param update
		goto(url);
	}

	let currentPage = $derived(Number(page.url.searchParams.get('page') ?? '1'));
	let totalPages = $derived(Math.ceil(count / pageSize));
</script>

<svelte:head>
	<title>{title} — The Flip Pinball DB</title>
</svelte:head>

<h1>{title}</h1>

{#if search}
	<SearchBar placeholder="Search {entityNamePlural}..." ariaLabel="Search {entityNamePlural}" />
{/if}

{#if count === 0}
	<p class="empty">No {entityNamePlural} found.</p>
{:else}
	<p class="count">{count} {count === 1 ? entityName : entityNamePlural}</p>

	{@render children()}

	<Pagination {currentPage} {totalPages} onPageChange={gotoPage} />
{/if}

<style>
	h1 {
		font-size: var(--font-size-6);
		font-weight: 700;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	.count {
		color: var(--color-text-muted);
		font-size: var(--font-size-1);
		margin-bottom: var(--size-3);
	}

	.empty {
		color: var(--color-text-muted);
		font-size: var(--font-size-2);
		padding: var(--size-8) 0;
		text-align: center;
	}
</style>
