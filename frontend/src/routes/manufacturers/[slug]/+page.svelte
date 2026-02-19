<script lang="ts">
	import { resolve } from '$app/paths';

	let { data } = $props();
	let mfr = $derived(data.manufacturer);
</script>

<svelte:head>
	<title>{mfr.name} — The Flip Pinball DB</title>
</svelte:head>

<article>
	<header>
		<h1>{mfr.name}</h1>
		{#if mfr.trade_name && mfr.trade_name !== mfr.name}
			<p class="trade-name">Trade name: {mfr.trade_name}</p>
		{/if}
	</header>

	{#if mfr.models.length === 0}
		<p class="empty">No models listed for this manufacturer.</p>
	{:else}
		<section>
			<h2>Models ({mfr.models.length})</h2>
			<div class="table-wrap">
				<table>
					<thead>
						<tr>
							<th>Name</th>
							<th>Year</th>
							<th>Type</th>
						</tr>
					</thead>
					<tbody>
						{#each mfr.models as model (model.slug)}
							<tr>
								<td><a href={resolve(`/models/${model.slug}`)}>{model.name}</a></td>
								<td>{model.year ?? '—'}</td>
								<td>{model.machine_type}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/if}

	{#if mfr.ipdb_manufacturer_id}
		<footer class="external-ids">
			<a
				href="https://www.ipdb.org/search.pl?any=&searchtype=advanced&mfgid={mfr.ipdb_manufacturer_id}"
				target="_blank"
				rel="noopener"
			>
				IPDB
			</a>
		</footer>
	{/if}
</article>

<style>
	article {
		max-width: 48rem;
	}

	header {
		margin-bottom: var(--size-6);
	}

	h1 {
		font-size: var(--font-size-7);
		font-weight: 700;
		color: var(--color-text-primary);
		margin-bottom: var(--size-2);
	}

	.trade-name {
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
	}

	h2 {
		font-size: var(--font-size-3);
		font-weight: 600;
		color: var(--color-text-primary);
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

	a {
		color: var(--color-link);
		text-decoration: none;
	}

	a:hover {
		text-decoration: underline;
	}

	.external-ids {
		display: flex;
		gap: var(--size-4);
		padding-top: var(--size-4);
		margin-top: var(--size-6);
		border-top: 1px solid var(--color-border-soft);
	}
</style>
