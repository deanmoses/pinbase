<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { pageTitle } from '$lib/constants';
	import { auth } from '$lib/auth.svelte';

	let { data, children } = $props();
	let model = $derived(data.model);
	let slug = $derived(page.params.slug);

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
	<title>{pageTitle(model.name)}</title>
</svelte:head>

<article>
	{#if model.hero_image_url}
		<div class="hero-image">
			<img src={model.hero_image_url} alt="{model.name} backglass" />
		</div>
	{/if}

	<header>
		<h1>{model.name}</h1>
		<div class="meta">
			{#if model.manufacturer_name}
				<span>
					<a href={resolve(`/manufacturers/${model.manufacturer_slug}`)}>
						{model.manufacturer_name}
					</a>
				</span>
			{/if}
			{#if model.year}
				<span
					>{model.year}{#if model.month}/{String(model.month).padStart(2, '0')}{/if}</span
				>
			{/if}
			{#if model.technology_generation_slug}
				<span>
					<a href={resolve(`/technology-generations/${model.technology_generation_slug}`)}>
						{model.technology_generation_name}
					</a>
				</span>
			{/if}
			{#if model.display_type_slug}
				<span>
					<a href={resolve(`/display-types/${model.display_type_slug}`)}>
						{model.display_type_name}
					</a>
				</span>
			{/if}
			{#if model.title_slug}
				<span>
					<a href={resolve(`/titles/${model.title_slug}`)}>{model.title_name}</a>
				</span>
			{/if}
			{#if model.franchise}
				<span>{model.franchise.name}</span>
			{/if}
		</div>
		{#if model.variant_features.length > 0}
			<div class="features">
				{#each model.variant_features as feature (feature)}
					<span class="chip">{feature}</span>
				{/each}
			</div>
		{/if}
	</header>

	<nav class="tabs" aria-label="Page sections">
		<a class="tab" class:active={isDetail} href={resolve(`/models/${slug}`)}>Detail</a>
		{#if auth.isAuthenticated}
			<a class="tab" class:active={isEdit} href={resolve(`/models/${slug}/edit`)}>Edit</a>
		{/if}
		<a class="tab" class:active={isActivity} href={resolve(`/models/${slug}/activity`)}>
			Activity
		</a>
	</nav>

	{@render children()}

	<footer class="external-ids">
		{#if model.ipdb_id}
			<a href="https://www.ipdb.org/machine.cgi?id={model.ipdb_id}" target="_blank" rel="noopener">
				IPDB #{model.ipdb_id}
			</a>
		{/if}
		{#if model.opdb_id}
			<a href="https://opdb.org/machines/{model.opdb_id}" target="_blank" rel="noopener">OPDB</a>
		{/if}
		{#if model.pinside_id}
			<a
				href="https://pinside.com/pinball/machine/{model.pinside_id}"
				target="_blank"
				rel="noopener"
			>
				Pinside
			</a>
		{/if}
	</footer>
</article>

<style>
	article {
		max-width: 48rem;
	}

	.hero-image {
		margin-bottom: var(--size-5);
	}

	.hero-image img {
		width: 100%;
		max-height: 24rem;
		object-fit: contain;
		border-radius: var(--radius-2);
		background-color: var(--color-surface);
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

	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: var(--size-2);
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
	}

	.meta span:not(:last-child)::after {
		content: '·';
		margin-left: var(--size-2);
	}

	.features {
		display: flex;
		flex-wrap: wrap;
		gap: var(--size-2);
		margin-top: var(--size-3);
	}

	.chip {
		display: inline-block;
		padding: var(--size-1) var(--size-3);
		font-size: var(--font-size-0);
		background-color: var(--color-surface);
		border: 1px solid var(--color-border-soft);
		border-radius: var(--radius-round);
		color: var(--color-text-muted);
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
