<script lang="ts">
	import { resolve } from '$app/paths';
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import { pageTitle } from '$lib/constants';

	const entities = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/corporate-entities/');
		return data ?? [];
	}, []);

	function yearsLabel(e: { year_start?: number | null; year_end?: number | null }): string {
		if (e.year_start && e.year_end) return `${e.year_start}–${e.year_end}`;
		if (e.year_start) return `${e.year_start}–present`;
		if (e.year_end) return `–${e.year_end}`;
		return '';
	}
</script>

<svelte:head>
	<title>{pageTitle('Corporate Entities')}</title>
</svelte:head>

<article>
	<header>
		<h1>Corporate Entities</h1>
	</header>

	{#if entities.loading}
		<p class="status">Loading...</p>
	{:else if entities.error}
		<p class="status error">Failed to load corporate entities.</p>
	{:else if entities.data.length === 0}
		<p class="status">No corporate entities found.</p>
	{:else}
		<ul class="entity-list">
			{#each entities.data as entity (entity.slug)}
				<li>
					<a href={resolve(`/corporate-entities/${entity.slug}`)} class="entity-row">
						<span class="entity-name">{entity.name}</span>
						<span class="entity-meta">
							<span class="manufacturer">{entity.manufacturer.name}</span>
							{#if yearsLabel(entity)}
								<span class="years">{yearsLabel(entity)}</span>
							{/if}
							<span class="count">
								{entity.model_count} model{entity.model_count === 1 ? '' : 's'}
							</span>
						</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</article>

<style>
	article {
		max-width: 56rem;
	}

	header {
		margin-bottom: var(--size-6);
	}

	h1 {
		font-size: var(--font-size-7);
		font-weight: 700;
		color: var(--color-text-primary);
	}

	.entity-list {
		list-style: none;
		padding: 0;
	}

	.entity-row {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		padding: var(--size-3) 0;
		border-bottom: 1px solid var(--color-border-soft);
		text-decoration: none;
		color: inherit;
		gap: var(--size-4);
	}

	.entity-row:hover .entity-name {
		color: var(--color-accent);
	}

	.entity-name {
		font-size: var(--font-size-2);
		color: var(--color-text-primary);
		font-weight: 500;
	}

	.entity-meta {
		display: flex;
		gap: var(--size-4);
		flex-shrink: 0;
		align-items: baseline;
	}

	.manufacturer {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
	}

	.years {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
	}

	.count {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
		min-width: 6rem;
		text-align: right;
	}

	.status {
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
		padding: var(--size-8) 0;
		text-align: center;
	}

	.status.error {
		color: var(--color-error, #c0392b);
	}
</style>
