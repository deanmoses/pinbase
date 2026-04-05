<script lang="ts" generics="T extends { slug: string; name: string }">
	import type { Snippet } from 'svelte';
	import { resolveHref } from '$lib/utils';
	import { pageTitle } from '$lib/constants';

	interface Props {
		title: string;
		subtitle?: string;
		basePath: string;
		items: T[];
		loading: boolean;
		error: string | null;
		rowStyle?: string;
		headerSnippet?: Snippet;
		rowSnippet?: Snippet<[item: T]>;
	}

	let {
		title,
		subtitle,
		basePath,
		items,
		loading,
		error,
		rowStyle,
		headerSnippet,
		rowSnippet
	}: Props = $props();

	let entityLabel = $derived(title.toLowerCase());
	let endpoint = $derived(`/api${basePath}/`);
</script>

<svelte:head>
	<title>{pageTitle(title)}</title>
	<link rel="preload" as="fetch" href={endpoint} crossorigin="anonymous" />
</svelte:head>

<article>
	<header>
		<h1>{title}</h1>
		{#if headerSnippet}
			{@render headerSnippet()}
		{:else if subtitle}
			<p class="subtitle">{subtitle}</p>
		{/if}
	</header>

	{#if loading}
		<p class="status">Loading...</p>
	{:else if error}
		<p class="status error">Failed to load {entityLabel}.</p>
	{:else if items.length === 0}
		<p class="status">No {entityLabel} found.</p>
	{:else}
		<ul class="item-list">
			{#each items as item (item.slug)}
				<li>
					<a href={resolveHref(`${basePath}/${item.slug}`)} class="item-row" style={rowStyle}>
						{#if rowSnippet}
							{@render rowSnippet(item)}
						{:else}
							<span class="item-name">{item.name}</span>
						{/if}
					</a>
				</li>
			{/each}
		</ul>
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
	}

	.subtitle {
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
		margin-top: var(--size-2);
	}

	.item-list {
		list-style: none;
		padding: 0;
	}

	.item-row {
		display: flex;
		align-items: baseline;
		padding: var(--size-3) 0;
		border-bottom: 1px solid var(--color-border-soft);
		text-decoration: none;
		color: var(--color-text-primary);
	}

	.item-row:hover {
		color: var(--color-accent);
	}

	.item-name {
		font-size: var(--font-size-2);
		color: inherit;
		font-weight: 500;
	}

	.status {
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
		padding: var(--size-8) 0;
		text-align: center;
	}

	.status.error {
		color: var(--color-error);
	}
</style>
