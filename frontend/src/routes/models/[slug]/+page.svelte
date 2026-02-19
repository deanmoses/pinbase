<script lang="ts">
	import { resolve } from '$app/paths';

	let { data } = $props();
	let model = $derived(data.model);

	type Claim = (typeof model.activity)[number];
	type FieldGroup = { field: string; claims: Claim[] };

	let activityGroups = $derived.by(() => {
		// Group claims by field.
		const byField: Record<string, Claim[]> = {};
		for (const claim of model.activity) {
			(byField[claim.field_name] ??= []).push(claim);
		}

		const conflicts: FieldGroup[] = [];
		const agreed: FieldGroup[] = [];
		const single: FieldGroup[] = [];

		for (const [field, claims] of Object.entries(byField)) {
			const group = { field, claims };
			if (claims.length === 1) {
				single.push(group);
			} else {
				const values = claims.map((c) => JSON.stringify(c.value));
				const allSame = values.every((v) => v === values[0]);
				if (allSame) agreed.push(group);
				else conflicts.push(group);
			}
		}

		return { conflicts, agreed, single };
	});

	function formatValue(v: unknown): string {
		const s = typeof v === 'string' ? v : JSON.stringify(v);
		return s.length > 100 ? s.slice(0, 100) + '...' : s;
	}
</script>

<svelte:head>
	<title>{model.name} — The Flip Pinball DB</title>
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
			<span>{model.machine_type}</span>
			<span>{model.display_type}</span>
			{#if model.group_slug}
				<span>
					<a href={resolve(`/groups/${model.group_slug}`)}>{model.group_name}</a>
				</span>
			{/if}
		</div>
		{#if model.features.length > 0}
			<div class="features">
				{#each model.features as feature (feature)}
					<span class="chip">{feature}</span>
				{/each}
			</div>
		{/if}
	</header>

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

	{#if model.educational_text}
		<section class="description">
			<h2>About</h2>
			<p>{model.educational_text}</p>
		</section>
	{/if}

	{#if model.activity.length > 0}
		{@const { conflicts, agreed, single } = activityGroups}
		{@const sourceNames = [...new Set(model.activity.map((c) => c.source_name))]}
		<section class="activity">
			<h2>Activity</h2>
			<p class="activity-summary">
				{sourceNames.join(' and ')} contributed to this record.
			</p>

			{#if conflicts.length > 0}
				<details class="activity-group">
					<summary>
						<h3>
							Conflicts resolved ({conflicts.length} field{conflicts.length === 1 ? '' : 's'})
						</h3>
					</summary>
					<dl class="field-list">
						{#each conflicts as { field, claims } (field)}
							<div class="field-row conflict">
								<dt>{field}</dt>
								<dd>
									{#each claims as claim (claim.source_slug)}
										<span class="claim" class:used={claim.is_winner}>
											<span class="source-badge">{claim.source_name}</span>
											{formatValue(claim.value)}
											{#if claim.is_winner}
												<span class="badge-used">used</span>
											{/if}
										</span>
									{/each}
								</dd>
							</div>
						{/each}
					</dl>
				</details>
			{/if}

			{#if agreed.length > 0}
				<details class="activity-group">
					<summary>
						<h3>Sources agree ({agreed.length} field{agreed.length === 1 ? '' : 's'})</h3>
					</summary>
					<dl class="field-list">
						{#each agreed as { field, claims } (field)}
							<div class="field-row">
								<dt>{field}</dt>
								<dd>
									<span class="claim used">
										{formatValue(claims[0].value)}
										<span class="source-list">
											{claims.map((c) => c.source_name).join(', ')}
										</span>
									</span>
								</dd>
							</div>
						{/each}
					</dl>
				</details>
			{/if}

			{#if single.length > 0}
				<details class="activity-group">
					<summary>
						<h3>Single source ({single.length} field{single.length === 1 ? '' : 's'})</h3>
					</summary>
					<dl class="field-list">
						{#each single as { field, claims } (field)}
							<div class="field-row">
								<dt>{field}</dt>
								<dd>
									<span class="claim used">
										<span class="source-badge">{claims[0].source_name}</span>
										{formatValue(claims[0].value)}
									</span>
								</dd>
							</div>
						{/each}
					</dl>
				</details>
			{/if}
		</section>
	{/if}

	<footer class="external-ids">
		{#if model.ipdb_id}
			<a href="https://www.ipdb.org/machine.cgi?id={model.ipdb_id}" target="_blank" rel="noopener">
				IPDB #{model.ipdb_id}
			</a>
		{/if}
		{#if model.opdb_id}
			<a href="https://opdb.org/machines/{model.opdb_id}" target="_blank" rel="noopener"> OPDB </a>
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
		margin-bottom: var(--size-6);
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

	.description p {
		font-size: var(--font-size-2);
		color: var(--color-text-primary);
		line-height: var(--font-lineheight-3);
	}

	.activity-summary {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
		margin-bottom: var(--size-4);
	}

	.activity-group {
		margin-bottom: var(--size-4);
	}

	.activity-group h3 {
		font-size: var(--font-size-1);
		font-weight: 600;
		color: var(--color-text-primary);
		margin-bottom: var(--size-2);
	}

	.activity-group summary {
		cursor: pointer;
		list-style: revert;
	}

	.activity-group summary h3 {
		display: inline;
	}

	.field-list {
		display: grid;
		grid-template-columns: 1fr;
		gap: 0;
	}

	.field-row {
		display: flex;
		gap: var(--size-3);
		padding: var(--size-2) 0;
		border-bottom: 1px solid var(--color-border-soft);
		font-size: var(--font-size-0);
	}

	.field-row dt {
		min-width: 10rem;
		font-weight: 500;
		color: var(--color-text-muted);
		font-size: var(--font-size-0);
	}

	.field-row dd {
		display: flex;
		flex-direction: column;
		gap: var(--size-1);
		font-size: var(--font-size-0);
		color: var(--color-text-primary);
		word-break: break-word;
	}

	.claim {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--size-2);
		opacity: 0.5;
	}

	.claim.used {
		opacity: 1;
	}

	.source-badge {
		display: inline-block;
		padding: 1px var(--size-2);
		font-size: var(--font-size-00, 0.7rem);
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		border-radius: var(--radius-1);
		background-color: var(--color-surface);
		border: 1px solid var(--color-border-soft);
		color: var(--color-text-muted);
	}

	.badge-used {
		font-size: var(--font-size-00, 0.7rem);
		font-weight: 600;
		color: var(--color-accent);
	}

	.source-list {
		font-size: var(--font-size-00, 0.7rem);
		color: var(--color-text-muted);
	}

	.external-ids {
		display: flex;
		gap: var(--size-4);
		padding-top: var(--size-4);
		border-top: 1px solid var(--color-border-soft);
	}
</style>
