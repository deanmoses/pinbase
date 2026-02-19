<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { PAGE_SIZES } from '$lib/api/pagination';

	let { data } = $props();

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
	let totalPages = $derived(Math.ceil(data.result.count / PAGE_SIZES.people));
</script>

<svelte:head>
	<title>People — The Flip Pinball DB</title>
</svelte:head>

<h1>People</h1>

{#if data.result.items.length === 0}
	<p class="empty">No people found.</p>
{:else}
	<p class="count">{data.result.count} {data.result.count === 1 ? 'person' : 'people'}</p>

	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>Name</th>
					<th class="num">Credits</th>
				</tr>
			</thead>
			<tbody>
				{#each data.result.items as person (person.slug)}
					<tr>
						<td><a href={resolve(`/people/${person.slug}`)}>{person.name}</a></td>
						<td class="num">{person.credit_count}</td>
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
