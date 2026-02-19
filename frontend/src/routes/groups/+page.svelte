<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { faMagnifyingGlass } from '@fortawesome/free-solid-svg-icons';
	import FaIcon from '$lib/components/FaIcon.svelte';
	import { PAGE_SIZES } from '$lib/api/pagination';

	let { data } = $props();

	let searchValue = $state(page.url.searchParams.get('search') ?? '');

	function handleSearch(e: SubmitEvent) {
		e.preventDefault();
		const url = new URL(page.url);
		if (searchValue.trim()) {
			url.searchParams.set('search', searchValue.trim());
		} else {
			url.searchParams.delete('search');
		}
		url.searchParams.delete('page');
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- same-page param update
		goto(url, { keepFocus: true });
	}

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
	let totalPages = $derived(Math.ceil(data.result.count / PAGE_SIZES.groups));
</script>

<svelte:head>
	<title>Groups — The Flip Pinball DB</title>
</svelte:head>

<h1>Groups</h1>

<form class="search-bar" onsubmit={handleSearch}>
	<div class="search-box">
		<FaIcon icon={faMagnifyingGlass} class="search-icon" />
		<input
			type="search"
			placeholder="Search groups..."
			aria-label="Search groups"
			bind:value={searchValue}
		/>
	</div>
</form>

{#if data.result.items.length === 0}
	<p class="empty">No groups found.</p>
{:else}
	<p class="count">{data.result.count} group{data.result.count === 1 ? '' : 's'}</p>

	<div class="card-grid">
		{#each data.result.items as group (group.slug)}
			<a href={resolve(`/groups/${group.slug}`)} class="card">
				{#if group.thumbnail_url}
					<img src={group.thumbnail_url} alt="" class="card-img" loading="lazy" />
				{:else}
					<div class="card-img-placeholder"></div>
				{/if}
				<div class="card-body">
					<h2 class="card-title">{group.name}</h2>
					{#if group.shortname && group.shortname !== group.name}
						<p class="card-shortname">{group.shortname}</p>
					{/if}
					<p class="card-count">
						{group.machine_count} machine{group.machine_count === 1 ? '' : 's'}
					</p>
				</div>
			</a>
		{/each}
	</div>

	{#if totalPages > 1}
		<nav class="pagination" aria-label="Pagination">
			<button onclick={() => gotoPage(currentPage - 1)} disabled={currentPage <= 1}>
				Previous
			</button>
			<span class="page-info">Page {currentPage} of {totalPages}</span>
			<button onclick={() => gotoPage(currentPage + 1)} disabled={currentPage >= totalPages}>
				Next
			</button>
		</nav>
	{/if}
{/if}

<style>
	h1 {
		font-size: var(--font-size-6);
		font-weight: 700;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	.search-bar {
		margin-bottom: var(--size-5);
	}

	.search-box {
		position: relative;
		max-width: 24rem;
	}

	:global(.search-box .search-icon) {
		position: absolute;
		left: var(--size-3);
		top: 50%;
		transform: translateY(-50%);
		width: 0.875rem;
		height: 0.875rem;
		color: var(--color-text-muted);
		pointer-events: none;
	}

	input[type='search'] {
		width: 100%;
		padding: var(--size-2) var(--size-3) var(--size-2) var(--size-8);
		font-size: var(--font-size-1);
		font-family: var(--font-body);
		background-color: var(--color-input-bg);
		color: var(--color-text-primary);
		border: 1px solid var(--color-input-border);
		border-radius: var(--radius-2);
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

	.card-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
		gap: var(--size-4);
	}

	.card {
		display: flex;
		flex-direction: column;
		background-color: var(--color-surface);
		border: 1px solid var(--color-border-soft);
		border-radius: var(--radius-2);
		overflow: hidden;
		text-decoration: none;
		color: inherit;
		transition:
			border-color 0.15s var(--ease-2),
			box-shadow 0.15s var(--ease-2);
	}

	.card:hover {
		border-color: var(--color-accent);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
	}

	.card-img {
		width: 100%;
		height: 8rem;
		object-fit: cover;
	}

	.card-img-placeholder {
		width: 100%;
		height: 8rem;
		background-color: var(--color-border-soft);
	}

	.card-body {
		padding: var(--size-3);
	}

	.card-title {
		font-size: var(--font-size-2);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-1);
	}

	.card-shortname {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
		margin-bottom: var(--size-1);
	}

	.card-count {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
	}

	.pagination {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--size-4);
		padding: var(--size-5) 0;
	}

	.page-info {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
	}

	button {
		padding: var(--size-2) var(--size-4);
		font-size: var(--font-size-1);
		font-family: var(--font-body);
		background-color: var(--color-surface);
		color: var(--color-text-primary);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-2);
		cursor: pointer;
		transition:
			background-color 0.15s var(--ease-2),
			border-color 0.15s var(--ease-2);
	}

	button:hover:not(:disabled) {
		border-color: var(--color-accent);
		color: var(--color-accent);
	}

	button:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
</style>
