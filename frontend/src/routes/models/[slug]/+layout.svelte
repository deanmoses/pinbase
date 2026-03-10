<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { pageTitle } from '$lib/constants';
	import { auth } from '$lib/auth.svelte';
	import ExternalLinksSidebarSection from '$lib/components/ExternalLinksSidebarSection.svelte';
	import ModelHierarchy from '$lib/components/ModelHierarchy.svelte';
	import RatingsSidebarSection from '$lib/components/RatingsSidebarSection.svelte';
	import SidebarList from '$lib/components/SidebarList.svelte';
	import SidebarListItem from '$lib/components/SidebarListItem.svelte';
	import SidebarSection from '$lib/components/SidebarSection.svelte';
	import TwoColumnLayout from '$lib/components/TwoColumnLayout.svelte';

	let { data, children } = $props();
	let model = $derived(data.model);
	let slug = $derived(page.params.slug);

	$effect(() => {
		auth.load();
	});

	let isOnlyModelInTitle = $derived(model.title_models.length <= 1);
	let isDetail = $derived(
		!page.url.pathname.endsWith('/edit') && !page.url.pathname.endsWith('/activity')
	);
	let isEdit = $derived(page.url.pathname.endsWith('/edit'));
	let isActivity = $derived(page.url.pathname.endsWith('/activity'));
</script>

<svelte:head>
	<title>{pageTitle(model.name)}</title>
</svelte:head>

<TwoColumnLayout heroImageUrl={model.hero_image_url} heroImageAlt="{model.name} backglass">
	{#snippet header()}
		{#if model.title_slug}
			<a class="kicker" href={resolve(`/titles/${model.title_slug}`)}>
				{model.title_name}
			</a>
		{/if}
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
					>{#if model.month}{new Date(model.year, model.month - 1).toLocaleString('en', {
							month: 'long'
						}) + ' '}{/if}{model.year}</span
				>
			{/if}
		</div>
		{#if model.variant_features.length > 0}
			<div class="features">
				{#each model.variant_features as feature (feature)}
					<span class="chip">{feature}</span>
				{/each}
			</div>
		{/if}
	{/snippet}

	{#snippet main()}
		{#if model.title_description && isOnlyModelInTitle}
			<section class="prose">
				<h2>About</h2>
				<p>{model.title_description}</p>
			</section>
		{/if}

		{#if model.extra_data.notes}
			<section class="prose">
				<h2>Notes</h2>
				<p>{model.extra_data.notes}</p>
			</section>
		{/if}

		{#if model.extra_data.Notes}
			<section class="prose">
				<h2>Notes</h2>
				<p>{model.extra_data.Notes}</p>
			</section>
		{/if}

		<nav class="tabs" aria-label="Page sections">
			<a class="tab" class:active={isDetail} href={resolve(`/models/${slug}`)}>People</a>
			{#if auth.isAuthenticated}
				<a class="tab" class:active={isEdit} href={resolve(`/models/${slug}/edit`)}>Edit</a>
			{/if}
			<a class="tab" class:active={isActivity} href={resolve(`/models/${slug}/activity`)}>
				Activity
			</a>
		</nav>

		{@render children()}
	{/snippet}

	{#snippet sidebar()}
		<SidebarSection heading="Specifications">
			<dl>
				{#if model.technology_generation_slug}
					<dt>Generation</dt>
					<dd>
						<a href={resolve(`/technology-generations/${model.technology_generation_slug}`)}
							>{model.technology_generation_name}</a
						>
					</dd>
				{/if}
				{#if model.display_type_slug}
					<dt>Display Type</dt>
					<dd>
						<a href={resolve(`/display-types/${model.display_type_slug}`)}
							>{model.display_type_name}</a
						>
					</dd>
				{/if}
				{#if model.player_count}
					<dt>Players</dt>
					<dd>{model.player_count}</dd>
				{/if}
				{#if model.flipper_count}
					<dt>Flippers</dt>
					<dd>{model.flipper_count}</dd>
				{/if}
				{#if model.production_quantity}
					<dt>Units Made</dt>
					<dd>{model.production_quantity}</dd>
				{/if}
				{#if model.system_slug}
					<dt>System</dt>
					<dd>
						<a href={resolve(`/systems/${model.system_slug}`)}>{model.system_name}</a>
					</dd>
				{/if}
				{#if model.franchise}
					<dt>Franchise</dt>
					<dd>
						<a href={resolve(`/franchises/${model.franchise.slug}`)}>{model.franchise.name}</a>
					</dd>
				{/if}
				{#if model.themes.length > 0}
					<dt>Themes</dt>
					<dd>
						{#each model.themes as theme, i (theme.slug)}
							{#if i > 0},{/if}
							<a href={resolve(`/themes/${theme.slug}`)}>{theme.name}</a>
						{/each}
					</dd>
				{/if}
				{#if model.abbreviations.length > 0}
					<dt>Abbrs</dt>
					<dd>{model.abbreviations.join(', ')}</dd>
				{/if}
				{#if model.cabinet_name}
					<dt>Cabinet</dt>
					<dd>{model.cabinet_name}</dd>
				{/if}
				{#if model.game_format_name}
					<dt>Format</dt>
					<dd>{model.game_format_name}</dd>
				{/if}
				{#if model.display_subtype_name}
					<dt>Display</dt>
					<dd>{model.display_subtype_name}</dd>
				{/if}
				{#if model.gameplay_features.length > 0}
					<dt>Features</dt>
					<dd>
						{#each model.gameplay_features as feature, i (feature.slug)}
							{#if i > 0},{/if}
							{feature.name}
						{/each}
					</dd>
				{/if}
				{#if model.series.length > 0}
					<dt>Series</dt>
					<dd>
						{#each model.series as s, i (s.slug)}
							{#if i > 0},{/if}
							<a href={resolve(`/series/${s.slug}`)}>{s.name}</a>
						{/each}
					</dd>
				{/if}
			</dl>
		</SidebarSection>

		<RatingsSidebarSection ipdbRating={model.ipdb_rating} pinsideRating={model.pinside_rating} />

		{#if model.variants.length > 0}
			<SidebarSection heading="Variants">
				<SidebarList>
					{#each model.variants as variant (variant.slug)}
						<SidebarListItem>
							<a href={resolve(`/models/${variant.slug}`)}>{variant.name}</a>
							{#if variant.year}
								<span class="muted">{variant.year}</span>
							{/if}
						</SidebarListItem>
					{/each}
				</SidebarList>
			</SidebarSection>
		{/if}

		{#if model.variant_of_slug}
			<SidebarSection heading="Parent Game">
				<SidebarList>
					<SidebarListItem>
						<a href={resolve(`/models/${model.variant_of_slug}`)}>{model.variant_of_name}</a>
						{#if model.variant_of_year}
							<span class="muted">{model.variant_of_year}</span>
						{/if}
					</SidebarListItem>
				</SidebarList>
			</SidebarSection>
		{/if}

		{#if model.variant_siblings && model.variant_siblings.length > 0}
			<SidebarSection heading="Other Variants">
				<SidebarList>
					{#each model.variant_siblings as sibling (sibling.slug)}
						<SidebarListItem>
							<a href={resolve(`/models/${sibling.slug}`)}>{sibling.name}</a>
							{#if sibling.year}
								<span class="muted">{sibling.year}</span>
							{/if}
						</SidebarListItem>
					{/each}
				</SidebarList>
			</SidebarSection>
		{/if}

		<ModelHierarchy
			models={model.title_models}
			heading="Other Models"
			excludeSlug={model.variant_of_slug ?? model.slug}
		/>

		<ExternalLinksSidebarSection
			ipdbId={model.ipdb_id}
			opdbId={model.opdb_id}
			pinsideId={model.pinside_id}
			note="See this model on other sites:"
		/>
	{/snippet}
</TwoColumnLayout>

<style>
	.kicker {
		font-size: var(--font-size-1);
		font-weight: 500;
		color: var(--color-text-muted);
		text-decoration: none;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.kicker:hover {
		color: var(--color-accent);
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

	/* Main column */
	.prose {
		margin-bottom: var(--size-5);
	}

	.prose h2 {
		font-size: var(--font-size-3);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	.prose p {
		font-size: var(--font-size-2);
		color: var(--color-text-primary);
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

	/* Sidebar */
	dl {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0 var(--size-3);
		align-items: baseline;
	}

	dt,
	dd {
		font-size: var(--font-size-0);
		margin: 0;
		padding: 2px 0;
	}

	dt {
		color: var(--color-text-muted);
		font-weight: 500;
	}

	dd {
		color: var(--color-text-primary);
	}

	.muted {
		color: var(--color-text-muted);
		font-size: var(--font-size-0);
	}
</style>
