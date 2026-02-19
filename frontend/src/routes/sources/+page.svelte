<script lang="ts">
	let { data } = $props();
</script>

<svelte:head>
	<title>Sources — The Flip Pinball DB</title>
</svelte:head>

<h1>Sources</h1>

{#if data.sources.length === 0}
	<p class="empty">No sources found.</p>
{:else}
	<div class="table-wrap">
		<table>
			<thead>
				<tr>
					<th>Name</th>
					<th>Type</th>
					<th class="num">Priority</th>
					<th>URL</th>
					<th>Description</th>
				</tr>
			</thead>
			<tbody>
				{#each data.sources as source (source.slug)}
					<tr>
						<td class="name">{source.name}</td>
						<td>{source.source_type}</td>
						<td class="num">{source.priority}</td>
						<td>
							{#if source.url}
								<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- external URL -->
								<a href={source.url} target="_blank" rel="noopener">{source.url}</a>
							{:else}
								—
							{/if}
						</td>
						<td class="desc">{source.description || '—'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

<style>
	h1 {
		font-size: var(--font-size-6);
		font-weight: 700;
		color: var(--color-text-primary);
		margin-bottom: var(--size-5);
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
		vertical-align: top;
	}

	.name {
		font-weight: 500;
		white-space: nowrap;
	}

	.num {
		text-align: right;
	}

	.desc {
		max-width: 20rem;
	}

	a {
		word-break: break-all;
	}
</style>
