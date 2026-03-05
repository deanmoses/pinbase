<script lang="ts">
	import { resolve } from '$app/paths';
	import CardGrid from '$lib/components/grid/CardGrid.svelte';
	import MachineCard from '$lib/components/cards/MachineCard.svelte';
	import ModelDetailBody from '$lib/components/ModelDetailBody.svelte';
	import CreditsList from '$lib/components/CreditsList.svelte';
	import { pageTitle } from '$lib/constants';
	import { resolveHref } from '$lib/utils';
	import { auth } from '$lib/auth.svelte';

	let { data } = $props();
	let title = $derived(data.title);
	let md = $derived(title.model_detail);

	$effect(() => {
		if (md) auth.load();
	});
</script>

<svelte:head>
	<title>{pageTitle(title.name)}</title>
</svelte:head>

{#if md}
	<!-- Single-model title: show full model detail inline -->
	<article class="single-model">
		{#if title.needs_review}
			<aside class="review-banner">
				<strong>Needs review</strong>
				<p>{title.needs_review_notes}</p>
				{#if title.review_links.length > 0}
					<p class="review-links">
						{#each title.review_links as link, i (link.url)}
							{#if i > 0}
								·
							{/if}
							{#if link.url.startsWith('/')}
								<a href={resolveHref(link.url)}>{link.label}</a>
							{:else}
								<a href={link.url} target="_blank" rel="noopener">{link.label}</a>
							{/if}
						{/each}
					</p>
				{/if}
			</aside>
		{/if}

		{#if md.hero_image_url}
			<div class="hero-image">
				<img src={md.hero_image_url} alt="{title.name} backglass" />
			</div>
		{/if}

		<header>
			<h1>{title.name}</h1>
			<div class="meta">
				{#if md.manufacturer_name}
					<span>
						<a href={resolve(`/manufacturers/${md.manufacturer_slug}`)}>
							{md.manufacturer_name}
						</a>
					</span>
				{/if}
				{#if md.year}
					<span
						>{#if md.month}{new Date(md.year, md.month - 1).toLocaleString('en', {
								month: 'long'
							}) + ' '}{/if}{md.year}</span
					>
				{/if}
				{#if md.franchise}
					<span>{md.franchise.name}</span>
				{/if}
			</div>
			{#if title.series.length > 0}
				<p class="series-list">
					Series:
					{#each title.series as s, i (s.slug)}
						{#if i > 0},{/if}
						<a href={resolve(`/series/${s.slug}`)}>{s.name}</a>
					{/each}
				</p>
			{/if}
			{#if md.variant_features.length > 0}
				<div class="features">
					{#each md.variant_features as feature (feature)}
						<span class="chip">{feature}</span>
					{/each}
				</div>
			{/if}
		</header>

		<nav class="tabs" aria-label="Page sections">
			<span class="tab active">Detail</span>
			{#if auth.isAuthenticated}
				<a class="tab" href={resolve(`/models/${md.slug}/edit`)}>Edit</a>
			{/if}
			<a class="tab" href={resolve(`/models/${md.slug}/activity`)}>Activity</a>
		</nav>

		<ModelDetailBody model={md} />

		<footer class="external-ids">
			{#if md.ipdb_id}
				<a href="https://www.ipdb.org/machine.cgi?id={md.ipdb_id}" target="_blank" rel="noopener">
					IPDB #{md.ipdb_id}
				</a>
			{/if}
			{#if md.opdb_id}
				<a href="https://opdb.org/machines/{md.opdb_id}" target="_blank" rel="noopener"> OPDB </a>
			{/if}
			{#if md.pinside_id}
				<a
					href="https://pinside.com/pinball/machine/{md.pinside_id}"
					target="_blank"
					rel="noopener"
				>
					Pinside
				</a>
			{/if}
		</footer>
	</article>
{:else}
	<!-- Multi-model title: show card grid -->
	<article class="multi-model">
		{#if title.needs_review}
			<aside class="review-banner">
				<strong>Needs review</strong>
				<p>{title.needs_review_notes}</p>
				{#if title.review_links.length > 0}
					<p class="review-links">
						{#each title.review_links as link, i (link.url)}
							{#if i > 0}
								·
							{/if}
							{#if link.url.startsWith('/')}
								<a href={resolveHref(link.url)}>{link.label}</a>
							{:else}
								<a href={link.url} target="_blank" rel="noopener">{link.label}</a>
							{/if}
						{/each}
					</p>
				{/if}
			</aside>
		{/if}

		<header>
			<h1>{title.name}</h1>
			{#if title.series.length > 0}
				<p class="series-list">
					Series:
					{#each title.series as s, i (s.slug)}
						{#if i > 0},{/if}
						<a href={resolve(`/series/${s.slug}`)}>{s.name}</a>
					{/each}
				</p>
			{/if}
		</header>

		{#if title.machines.length === 0}
			<p class="empty">No machines in this title.</p>
		{:else}
			<section>
				<h2>Machines ({title.machines.length})</h2>
				<CardGrid>
					{#each title.machines as machine (machine.slug)}
						<MachineCard
							slug={machine.slug}
							name={machine.name}
							thumbnailUrl={machine.thumbnail_url}
							manufacturerName={machine.manufacturer_name}
							year={machine.year}
						/>
					{/each}
				</CardGrid>
			</section>
		{/if}

		<CreditsList credits={title.credits} />
	</article>
{/if}

<style>
	/* Shared styles */
	.review-banner {
		background-color: color-mix(in srgb, var(--color-warning) 12%, transparent);
		border: 1px solid var(--color-warning);
		border-radius: var(--radius-2);
		padding: var(--size-3) var(--size-4);
		margin-bottom: var(--size-5);
		font-size: var(--font-size-1);
		color: var(--color-text-primary);
	}

	.review-banner strong {
		color: var(--color-warning);
	}

	.review-banner p {
		margin-top: var(--size-1);
	}

	.review-links a {
		color: var(--color-warning);
		text-decoration: underline;
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

	.series-list {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
		margin-top: var(--size-1);
	}

	/* Multi-model layout */
	.multi-model {
		max-width: 64rem;
	}

	.multi-model header {
		margin-bottom: var(--size-6);
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

	/* Single-model layout (matches model detail page) */
	.single-model {
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
