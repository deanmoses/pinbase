<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { pageTitle } from '$lib/constants';
	import { auth } from '$lib/auth.svelte';

	let { data, children } = $props();
	let mfr = $derived(data.manufacturer);
	let slug = $derived(page.params.slug);
	let ipdbId = $derived(
		mfr.entities.find((e: { ipdb_manufacturer_id?: number | null }) => e.ipdb_manufacturer_id)
			?.ipdb_manufacturer_id
	);

	$effect(() => {
		auth.load();
	});

	let isDetail = $derived(
		!page.url.pathname.endsWith('/edit') && !page.url.pathname.endsWith('/activity')
	);
	let isEdit = $derived(page.url.pathname.endsWith('/edit'));
	let isActivity = $derived(page.url.pathname.endsWith('/activity'));
</script>

<svelte:head>
	<title>{pageTitle(mfr.name)}</title>
</svelte:head>

<article>
	<header>
		<h1>{mfr.name}</h1>
		{#if mfr.trade_name && mfr.trade_name !== mfr.name}
			<p class="trade-name">Trade name: {mfr.trade_name}</p>
		{/if}
		{#if mfr.description}
			<p class="description">{mfr.description}</p>
		{/if}
	</header>

	<nav class="tabs" aria-label="Page sections">
		<a class="tab" class:active={isDetail} href={resolve(`/manufacturers/${slug}`)}>Detail</a>
		{#if auth.isAuthenticated}
			<a class="tab" class:active={isEdit} href={resolve(`/manufacturers/${slug}/edit`)}>Edit</a>
		{/if}
		<a class="tab" class:active={isActivity} href={resolve(`/manufacturers/${slug}/activity`)}>
			Activity
		</a>
	</nav>

	{@render children()}

	{#if ipdbId}
		<footer class="external-ids">
			<a
				href="https://www.ipdb.org/search.pl?any=&searchtype=advanced&mfgid={ipdbId}"
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
		max-width: 64rem;
	}

	header {
		margin-bottom: var(--size-5);
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
		margin-top: var(--size-2);
	}

	.description {
		font-size: var(--font-size-2);
		color: var(--color-text-secondary);
		margin-top: var(--size-2);
		line-height: var(--font-lineheight-3);
	}

	.tabs {
		display: flex;
		gap: 0;
		border-bottom: 2px solid var(--color-border-soft);
		margin-bottom: var(--size-6);
	}

	.tab {
		padding: var(--size-2) var(--size-4);
		font-size: var(--font-size-1);
		font-weight: 500;
		color: var(--color-text-muted);
		text-decoration: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -2px;
		transition:
			color 0.15s,
			border-color 0.15s;
	}

	.tab:hover {
		color: var(--color-text-primary);
	}

	.tab.active {
		color: var(--color-accent);
		border-bottom-color: var(--color-accent);
	}

	.external-ids {
		display: flex;
		gap: var(--size-4);
		padding-top: var(--size-4);
		border-top: 1px solid var(--color-border-soft);
		margin-top: var(--size-4);
	}
</style>
