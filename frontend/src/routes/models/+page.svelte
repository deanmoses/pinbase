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
	let totalPages = $derived(Math.ceil(data.result.count / PAGE_SIZES.models));
</script>

<svelte:head>
	<title>Models — The Flip Pinball DB</title>
</svelte:head>

<h1>Models</h1>

<form class="search-bar" onsubmit={handleSearch}>
	<div class="search-box">
		<FaIcon icon={faMagnifyingGlass} class="search-icon" />
		<input
			type="search"
			placeholder="Search models..."
			aria-label="Search models"
			bind:value={searchValue}
		/>
	</div>
</form>

{#if data.result.items.length === 0}
	<p class="empty">No models found.</p>
{:else}
	<p class="count">{data.result.count} model{data.result.count === 1 ? '' : 's'}</p>

	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th class="img-col"></th>
					<th>Name</th>
					<th>Manufacturer</th>
					<th>Year</th>
					<th>Type</th>
					<th class="num">IPDB</th>
					<th class="num">Pinside</th>
				</tr>
			</thead>
			<tbody>
				{#each data.result.items as model (model.slug)}
					<tr>
						<td class="img-col">
							{#if model.thumbnail_url}
								<img src={model.thumbnail_url} alt="" class="thumbnail" loading="lazy" />
							{/if}
						</td>
						<td><a href={resolve(`/models/${model.slug}`)}>{model.name}</a></td>
						<td>
							{#if model.manufacturer_slug}
								<a href={resolve(`/manufacturers/${model.manufacturer_slug}`)}>
									{model.manufacturer_name}
								</a>
							{:else}
								{model.manufacturer_name ?? '—'}
							{/if}
						</td>
						<td>{model.year ?? '—'}</td>
						<td>{model.machine_type}</td>
						<td class="num">{model.ipdb_rating ?? '—'}</td>
						<td class="num">{model.pinside_rating ?? '—'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
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

	.table-wrap {
		overflow-x: auto;
	}

	table {
		width: 100%;
		border-collapse: collapse;
	}

	th {
		text-align: left;
		font-size: var(--font-size-0);
		font-weight: 600;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		padding: var(--size-2) var(--size-3);
		border-bottom: 2px solid var(--color-border);
	}

	td {
		padding: var(--size-2) var(--size-3);
		border-bottom: 1px solid var(--color-border-soft);
		font-size: var(--font-size-1);
		color: var(--color-text-primary);
	}

	.img-col {
		width: 3.5rem;
		padding: var(--size-1) var(--size-2);
	}

	.thumbnail {
		width: 3rem;
		height: 2.25rem;
		object-fit: cover;
		border-radius: var(--radius-1);
	}

	.num {
		text-align: right;
	}

	a {
		color: var(--color-link);
		text-decoration: none;
	}

	a:hover {
		text-decoration: underline;
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
