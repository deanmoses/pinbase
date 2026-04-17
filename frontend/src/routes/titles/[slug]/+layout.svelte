<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { auth } from '$lib/auth.svelte';
	import MetaTags from '$lib/components/MetaTags.svelte';
	import ExternalLinksSidebarSection from '$lib/components/ExternalLinksSidebarSection.svelte';
	import HeroHeader from '$lib/components/HeroHeader.svelte';
	import ModelHierarchy from '$lib/components/ModelHierarchy.svelte';
	import ModelSpecsSidebar from '$lib/components/ModelSpecsSidebar.svelte';
	import PageActionBar from '$lib/components/PageActionBar.svelte';
	import RatingsSidebarSection from '$lib/components/RatingsSidebarSection.svelte';
	import SidebarList from '$lib/components/SidebarList.svelte';
	import SidebarListItem from '$lib/components/SidebarListItem.svelte';
	import SidebarSection from '$lib/components/SidebarSection.svelte';
	import TaxonomyLinkSidebarSection from '$lib/components/TaxonomyLinkSidebarSection.svelte';
	import TwoColumnLayout from '$lib/components/TwoColumnLayout.svelte';
	import NeedsReviewBanner from '$lib/components/NeedsReviewBanner.svelte';
	import type { EditSectionDropdown, EditSectionMenuItem } from '$lib/components/edit-section-menu';
	import { MODEL_EDIT_SECTIONS } from '$lib/components/editors/model-edit-sections';
	import { titleSectionsFor } from '$lib/components/editors/title-edit-sections';

	let { data, children } = $props();
	let title = $derived(data.title);
	let md = $derived(title.model_detail);
	let specs = $derived(title.agreed_specs);
	let slug = $derived(page.params.slug);

	$effect(() => {
		auth.load();
	});

	let isEdit = $derived(
		page.url.pathname.endsWith('/edit') || page.url.pathname.includes('/edit/')
	);
	let isDetail = $derived(
		!isEdit &&
			!page.url.pathname.endsWith('/sources') &&
			!page.url.pathname.endsWith('/edit-history') &&
			!page.url.pathname.includes('/media')
	);

	let metaDescription = $derived.by(() => {
		if (title.description?.text) return title.description.text;
		const parts = [title.name];
		if (md?.year) parts.push(`a ${md.year} pinball machine`);
		else parts.push('pinball title');
		if (md?.manufacturer) parts.push(`by ${md.manufacturer.name}`);
		return parts.join(' — ');
	});
	let heroImage = $derived(md ? md.hero_image_url : title.hero_image_url);

	let metaItems = $derived.by(() => {
		if (!md) return [];
		const items: Array<{ text: string; href?: string }> = [];
		if (md.manufacturer) {
			items.push({
				text: md.manufacturer.name,
				href: resolve(`/manufacturers/${md.manufacturer.slug}`)
			});
		}
		if (md.year) {
			const yearText = md.month
				? `${new Date(md.year, md.month - 1).toLocaleString('en', { month: 'long' })} ${md.year}`
				: `${md.year}`;
			items.push({ text: yearText });
		}
		return items;
	});

	// Single-model titles: two labeled dropdowns ("Edit Title" + "Edit Model") in the action bar.
	// Multi-model titles: one "Edit" dropdown with title sections.
	let editDropdowns = $derived.by<EditSectionDropdown[] | undefined>(() => {
		if (!auth.isAuthenticated) return undefined;

		if (md) {
			const titleItems: EditSectionMenuItem[] = titleSectionsFor(true).map((s) => ({
				key: s.key,
				label: s.label,
				href: resolve(`/titles/${slug}/edit/${s.segment}`)
			}));
			const modelItems: EditSectionMenuItem[] = MODEL_EDIT_SECTIONS.map((s) => ({
				key: s.key,
				label: s.label,
				href: resolve(`/models/${md.slug}/edit/${s.segment}`)
			}));
			return [
				{ label: 'Edit Title', items: titleItems },
				{ label: 'Edit Model', items: modelItems }
			];
		}

		const titleItems: EditSectionMenuItem[] = titleSectionsFor(false).map((s) => ({
			key: s.key,
			label: s.label,
			href: resolve(`/titles/${slug}/edit/${s.segment}`)
		}));
		return [{ label: 'Edit', items: titleItems }];
	});
</script>

<MetaTags
	title={title.name}
	description={metaDescription}
	url={page.url.href}
	image={heroImage}
	imageAlt={heroImage ? `${title.name} pinball machine` : undefined}
/>

{#if title.needs_review}
	<NeedsReviewBanner notes={title.needs_review_notes} links={title.review_links} />
{/if}

<article>
	<HeroHeader
		name={title.name}
		heroImageUrl={md ? md.hero_image_url : title.hero_image_url}
		heroImageAlt="{title.name} backglass"
		{metaItems}
	/>

	{#if !isEdit}
		<PageActionBar
			{editDropdowns}
			historyHref={resolve(`/titles/${slug}/edit-history`)}
			sourcesHref={resolve(`/titles/${slug}/sources`)}
		/>
	{/if}

	<TwoColumnLayout>
		{#snippet main()}
			{@render children()}
		{/snippet}

		{#snippet sidebar()}
			<div class:desktop-only={isDetail}>
				{#if md}
					<SidebarSection heading="Specifications">
						<ModelSpecsSidebar model={md} />
					</SidebarSection>

					<RatingsSidebarSection ipdbRating={md.ipdb_rating} pinsideRating={md.pinside_rating} />

					{#if md.variants.length > 0}
						<SidebarSection heading="Variants">
							<SidebarList>
								{#each md.variants as variant (variant.slug)}
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

					<ExternalLinksSidebarSection
						ipdbId={md.ipdb_id}
						opdbId={md.opdb_id}
						pinsideId={md.pinside_id}
						note="See this title on other sites:"
					/>
				{:else}
					{#if specs.technology_generation || specs.display_type || specs.player_count || specs.system || specs.cabinet || specs.game_format || specs.display_subtype || specs.production_quantity || (specs.themes && specs.themes.length > 0) || title.abbreviations.length > 0}
						<SidebarSection heading="Specifications">
							<dl>
								{#if specs.technology_generation}
									<dt>Generation</dt>
									<dd>
										<a href={resolve(`/technology-generations/${specs.technology_generation.slug}`)}
											>{specs.technology_generation.name}</a
										>
									</dd>
								{/if}
								{#if specs.display_type}
									<dt>Display Type</dt>
									<dd>
										<a href={resolve(`/display-types/${specs.display_type.slug}`)}
											>{specs.display_type.name}</a
										>
									</dd>
								{/if}
								{#if specs.player_count}
									<dt>Players</dt>
									<dd>{specs.player_count}</dd>
								{/if}
								{#if specs.flipper_count}
									<dt>Flippers</dt>
									<dd>{specs.flipper_count}</dd>
								{/if}
								{#if specs.production_quantity}
									<dt>Units Made</dt>
									<dd>{specs.production_quantity}</dd>
								{/if}
								{#if specs.system}
									<dt>System</dt>
									<dd>
										<a href={resolve(`/systems/${specs.system.slug}`)}>{specs.system.name}</a>
									</dd>
								{/if}
								{#if specs.themes && specs.themes.length > 0}
									<dt>Themes</dt>
									<dd>
										{#each specs.themes as theme, i (theme.slug)}
											{#if i > 0},{/if}
											<a href={resolve(`/themes/${theme.slug}`)}>{theme.name}</a>
										{/each}
									</dd>
								{/if}
								{#if specs.gameplay_features && specs.gameplay_features.length > 0}
									<dt>Features</dt>
									<dd>
										{#each specs.gameplay_features as feature, i (feature.slug)}
											{#if i > 0},{/if}
											<a href={resolve(`/gameplay-features/${feature.slug}`)}>{feature.name}</a
											>{#if feature.count}&nbsp;({feature.count}){/if}
										{/each}
									</dd>
								{/if}
								{#if specs.reward_types && specs.reward_types.length > 0}
									<dt>Reward Types</dt>
									<dd>
										{#each specs.reward_types as rt, i (rt.slug)}
											{#if i > 0},{/if}
											<a href={resolve(`/reward-types/${rt.slug}`)}>{rt.name}</a>
										{/each}
									</dd>
								{/if}
								{#if title.abbreviations.length > 0}
									<dt>Abbrs</dt>
									<dd>{title.abbreviations.join(', ')}</dd>
								{/if}
								{#if specs.cabinet}
									<dt>Cabinet</dt>
									<dd>
										<a href={resolve(`/cabinets/${specs.cabinet.slug}`)}>{specs.cabinet.name}</a>
									</dd>
								{/if}
								{#if specs.game_format}
									<dt>Format</dt>
									<dd>
										<a href={resolve(`/game-formats/${specs.game_format.slug}`)}
											>{specs.game_format.name}</a
										>
									</dd>
								{/if}
								{#if specs.display_subtype}
									<dt>Display</dt>
									<dd>
										<a href={resolve(`/display-subtypes/${specs.display_subtype.slug}`)}
											>{specs.display_subtype.name}</a
										>
									</dd>
								{/if}
							</dl>
						</SidebarSection>
					{/if}

					<TaxonomyLinkSidebarSection
						heading="Franchise"
						basePath="/franchises"
						item={title.franchise}
					/>
					<TaxonomyLinkSidebarSection heading="Series" basePath="/series" item={title.series} />

					{#if title.machines.length > 0}
						<ModelHierarchy models={title.machines} />
					{/if}
				{/if}
			</div>
		{/snippet}
	</TwoColumnLayout>
</article>

<style>
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

	/* Hide sidebar on mobile for the detail reader — accordions carry all the same data. */
	/* Keep in sync with LAYOUT_BREAKPOINT (52rem). */
	.desktop-only {
		display: none;
	}

	@media (min-width: 52rem) {
		.desktop-only {
			display: contents;
		}
	}
</style>
