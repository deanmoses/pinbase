<script lang="ts">
	import { resolve } from '$app/paths';

	let { data } = $props();
	let model = $derived(data.model);
</script>

<section class="specs">
	<h2>Specifications</h2>
	<dl>
		{#if model.player_count}
			<dt>Players</dt>
			<dd>{model.player_count}</dd>
		{/if}
		{#if model.flipper_count}
			<dt>Flippers</dt>
			<dd>{model.flipper_count}</dd>
		{/if}
		{#if model.production_quantity}
			<dt>Production</dt>
			<dd>{model.production_quantity}</dd>
		{/if}
		{#if model.mpu}
			<dt>MPU</dt>
			<dd>{model.mpu}</dd>
		{/if}
		{#if model.theme}
			<dt>Theme</dt>
			<dd>{model.theme}</dd>
		{/if}
	</dl>
</section>

{#if model.aliases.length > 0}
	<section class="variants">
		<h2>Variants</h2>
		<ul>
			{#each model.aliases as alias (alias.slug)}
				<li>
					<a href={resolve(`/models/${alias.slug}`)}>{alias.name}</a>
					{#if alias.features.length > 0}
						<span class="alias-features">{alias.features.join(', ')}</span>
					{/if}
				</li>
			{/each}
		</ul>
	</section>
{/if}

{#if model.ipdb_rating || model.pinside_rating}
	<section class="ratings">
		<h2>Ratings</h2>
		<div class="rating-cards">
			{#if model.ipdb_rating}
				<div class="rating-card">
					<span class="rating-value">{model.ipdb_rating.toFixed(1)}</span>
					<span class="rating-label">IPDB</span>
				</div>
			{/if}
			{#if model.pinside_rating}
				<div class="rating-card">
					<span class="rating-value">{model.pinside_rating.toFixed(1)}</span>
					<span class="rating-label">Pinside</span>
				</div>
			{/if}
		</div>
	</section>
{/if}

{#if model.credits.length > 0}
	<section class="credits">
		<h2>Credits</h2>
		<ul>
			{#each model.credits as credit (credit.person_slug + credit.role)}
				<li>
					<a href={resolve(`/people/${credit.person_slug}`)}>{credit.person_name}</a>
					<span class="role">{credit.role_display}</span>
				</li>
			{/each}
		</ul>
	</section>
{/if}

{#if model.extra_data.notes}
	<section class="notes">
		<h2>Notes</h2>
		<p>{model.extra_data.notes}</p>
	</section>
{/if}

{#if model.extra_data.Notes}
	<section class="notes">
		<h2>Notes Capitalized</h2>
		<p>{model.extra_data.Notes}</p>
	</section>
{/if}

{#if model.educational_text}
	<section class="description">
		<h2>About</h2>
		<p>{model.educational_text}</p>
	</section>
{/if}

<style>
	h2 {
		font-size: var(--font-size-3);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-3);
	}

	section {
		margin-bottom: var(--size-6);
	}

	dl {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--size-1) var(--size-4);
	}

	dt {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
		font-weight: 500;
	}

	dd {
		font-size: var(--font-size-1);
		color: var(--color-text-primary);
	}

	.variants ul {
		list-style: none;
		padding: 0;
	}

	.variants li {
		display: flex;
		justify-content: space-between;
		padding: var(--size-2) 0;
		border-bottom: 1px solid var(--color-border-soft);
		font-size: var(--font-size-1);
	}

	.alias-features {
		color: var(--color-text-muted);
		font-size: var(--font-size-0);
	}

	.rating-cards {
		display: flex;
		gap: var(--size-4);
	}

	.rating-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: var(--size-3) var(--size-5);
		background-color: var(--color-surface);
		border: 1px solid var(--color-border-soft);
		border-radius: var(--radius-2);
	}

	.rating-value {
		font-size: var(--font-size-5);
		font-weight: 700;
		color: var(--color-accent);
	}

	.rating-label {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.credits ul {
		list-style: none;
		padding: 0;
	}

	.credits li {
		display: flex;
		justify-content: space-between;
		padding: var(--size-2) 0;
		border-bottom: 1px solid var(--color-border-soft);
		font-size: var(--font-size-1);
	}

	.role {
		color: var(--color-text-muted);
		font-size: var(--font-size-0);
	}

	.notes p,
	.description p {
		font-size: var(--font-size-2);
		color: var(--color-text-primary);
		line-height: var(--font-lineheight-3);
	}
</style>
