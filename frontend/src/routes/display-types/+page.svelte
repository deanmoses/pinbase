<script lang="ts">
	import client from '$lib/api/client';
	import { createAsyncLoader } from '$lib/async-loader.svelte';
	import TaxonomyListPage from '$lib/components/TaxonomyListPage.svelte';
	import { resolveHref } from '$lib/utils';

	const loader = createAsyncLoader(async () => {
		const { data } = await client.GET('/api/display-types/');
		return data ?? [];
	}, []);
</script>

<TaxonomyListPage
	catalogKey="display-type"
	items={loader.data}
	loading={loader.loading}
	error={loader.error}
	canCreate
>
	{#snippet headerSnippet()}
		<p class="overview">
			A <strong>display type</strong> is the technology a game machine uses to show the player's
			score and — in later eras — animations, artwork, and video. Early
			<a href="/technology-generations/electromechanical">electromechanical</a> (EM) machines
			totaled points with banks of <a href="/display-types/backglass-lights">backglass lights</a>,
			then moved to the clattering mechanical <a href="/display-types/score-reels">score reels</a>
			that defined the EM golden age. The
			<a href="/technology-generations/solid-state">solid-state</a>
			era replaced reels with glowing
			<a href="/display-types/alphanumeric">alphanumeric</a> LED segments, which in 1991 gave way to
			the iconic orange <a href="/display-types/dot-matrix">dot-matrix display</a> that
			<a href="/manufacturers/williams">Williams</a> introduced on
			<a href="/titles/funhouse"><em>Funhouse</em></a> and
			<a href="/titles/the-addams-family"><em>The Addams Family</em></a>. A handful of hybrids —
			<a href="/manufacturers/bally">Bally</a>'s
			<a href="/titles/baby-pac-man"><em>Baby Pac-Man</em></a> and Williams' Pinball 2000 — used
			<a href="/display-types/cga">CGA monitors</a> instead. Today's machines, starting with
			<a href="/manufacturers/jersey-jack">Jersey Jack</a>'s
			<a href="/titles/the-wizard-of-oz"><em>The Wizard of Oz</em></a> in 2013, ship with full-color
			<a href="/display-types/lcd">LCD screens</a>.
		</p>
	{/snippet}

	{#snippet listSnippet(items)}
		<ul class="type-list">
			{#each items as type (type.slug)}
				<li class="type-group">
					<a href={resolveHref(`/display-types/${type.slug}`)} class="type-row">
						<span class="type-name">{type.name}</span>
						<span class="count">
							{type.title_count} title{type.title_count === 1 ? '' : 's'}
						</span>
					</a>
					{#if type.subtypes.length > 0}
						<ul class="subtype-list">
							{#each type.subtypes as sub (sub.slug)}
								<li>
									<a href={resolveHref(`/display-subtypes/${sub.slug}`)} class="subtype-row">
										<span class="subtype-name">{sub.name}</span>
										<span class="count">
											{sub.title_count} title{sub.title_count === 1 ? '' : 's'}
										</span>
									</a>
								</li>
							{/each}
						</ul>
					{/if}
				</li>
			{/each}
		</ul>
	{/snippet}
</TaxonomyListPage>

<style>
	.overview {
		font-size: var(--font-size-2);
		color: var(--color-text-muted);
		margin-top: var(--size-2);
		max-width: 42rem;
		line-height: 1.5;
	}

	.overview a {
		color: var(--color-accent);
	}

	.type-list,
	.subtype-list {
		list-style: none;
		padding: 0;
	}

	.type-group {
		margin-bottom: var(--size-4);
	}

	.type-row,
	.subtype-row {
		display: flex;
		align-items: baseline;
		padding: var(--size-3) 0;
		border-bottom: 1px solid var(--color-border-soft);
		text-decoration: none;
		color: var(--color-text-primary);
	}

	.type-row:hover,
	.subtype-row:hover {
		color: var(--color-accent);
	}

	.type-name {
		font-size: var(--font-size-3);
		font-weight: 600;
		flex: 1;
	}

	.subtype-list {
		margin-left: var(--size-6);
	}

	.subtype-name {
		font-size: var(--font-size-2);
		font-weight: 500;
		flex: 1;
	}

	.count {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
		flex-shrink: 0;
	}
</style>
