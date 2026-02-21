<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { pageTitle } from '$lib/constants';
	import { auth } from '$lib/auth.svelte';
	import client from '$lib/api/client';

	let { data } = $props();
	// untrack: intentional one-time capture; model is updated explicitly after save
	let model = $state(untrack(() => data.model));

	$effect(() => {
		auth.load();
	});

	// ── Tab state ──────────────────────────────────────────────────────────────

	type Tab = 'detail' | 'edit' | 'activity';
	let activeTab = $derived<Tab>((page.state.tab as Tab) ?? 'detail');

	function setTab(tab: Tab) {
		replaceState('', { tab });
	}

	// ── Activity grouping ──────────────────────────────────────────────────────

	type Claim = (typeof model.activity)[number];
	type FieldGroup = { field: string; claims: Claim[] };

	let activityGroups = $derived.by(() => {
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

	function claimAttribution(claim: Claim): string {
		return claim.source_name ?? (claim.user_display ? `@${claim.user_display}` : 'Unknown');
	}

	function formatValue(v: unknown): string {
		const s = typeof v === 'string' ? v : JSON.stringify(v);
		return s.length > 100 ? s.slice(0, 100) + '...' : s;
	}

	// ── Edit form ──────────────────────────────────────────────────────────────

	function modelToFormFields(m: typeof model) {
		return {
			name: m.name,
			year: m.year ?? '',
			month: m.month ?? '',
			machine_type: m.machine_type,
			display_type: m.display_type,
			player_count: m.player_count ?? '',
			flipper_count: m.flipper_count ?? '',
			production_quantity: m.production_quantity,
			theme: m.theme,
			mpu: m.mpu,
			ipdb_id: m.ipdb_id ?? '',
			opdb_id: m.opdb_id ?? '',
			pinside_id: m.pinside_id ?? '',
			ipdb_rating: m.ipdb_rating ?? '',
			pinside_rating: m.pinside_rating ?? '',
			educational_text: m.educational_text,
			sources_notes: m.sources_notes
		};
	}

	// untrack: intentional one-time capture; re-synced explicitly after save
	let editFields = $state(untrack(() => modelToFormFields(model)));

	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let saveError = $state('');

	function getChangedFields(): Record<string, unknown> {
		const original = modelToFormFields(model);
		const changed: Record<string, unknown> = {};
		for (const key of Object.keys(editFields) as (keyof typeof editFields)[]) {
			const val = editFields[key];
			if (String(val) !== String(original[key])) {
				// Send null for empty optional fields, the raw value otherwise.
				changed[key] = val === '' ? null : val;
			}
		}
		return changed;
	}

	async function saveChanges() {
		const fields = getChangedFields();
		if (Object.keys(fields).length === 0) return;

		saveStatus = 'saving';
		saveError = '';

		const { data: updated, error } = await client.PATCH('/api/models/{slug}/claims/', {
			params: { path: { slug: model.slug } },
			body: { fields }
		});

		if (updated) {
			model = updated;
			editFields = modelToFormFields(updated);
			saveStatus = 'saved';
			setTimeout(() => (saveStatus = 'idle'), 3000);
		} else {
			saveStatus = 'error';
			saveError = error ? JSON.stringify(error) : 'Save failed.';
		}
	}
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

	<!-- Tab bar -->
	<nav class="tabs" aria-label="Page sections">
		<button class="tab" class:active={activeTab === 'detail'} onclick={() => setTab('detail')}>
			Detail
		</button>
		{#if auth.isAuthenticated}
			<button class="tab" class:active={activeTab === 'edit'} onclick={() => setTab('edit')}>
				Edit
			</button>
		{/if}
		<button class="tab" class:active={activeTab === 'activity'} onclick={() => setTab('activity')}>
			Activity
		</button>
	</nav>

	<!-- ── Detail tab ────────────────────────────────────────────────────────── -->
	{#if activeTab === 'detail'}
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
	{/if}

	<!-- ── Edit tab ──────────────────────────────────────────────────────────── -->
	{#if activeTab === 'edit' && auth.isAuthenticated}
		<section class="edit-form">
			<h2>Edit</h2>
			<form
				onsubmit={(e) => {
					e.preventDefault();
					saveChanges();
				}}
			>
				<div class="field-group">
					<label for="ef-name">Name</label>
					<input id="ef-name" type="text" bind:value={editFields.name} />
				</div>

				<div class="form-row">
					<div class="field-group">
						<label for="ef-year">Year</label>
						<input id="ef-year" type="number" min="1940" max="2100" bind:value={editFields.year} />
					</div>
					<div class="field-group">
						<label for="ef-month">Month</label>
						<input id="ef-month" type="number" min="1" max="12" bind:value={editFields.month} />
					</div>
				</div>

				<div class="form-row">
					<div class="field-group">
						<label for="ef-machine-type">Machine type</label>
						<select id="ef-machine-type" bind:value={editFields.machine_type}>
							<option value="PM">PM — Pure Mechanical</option>
							<option value="EM">EM — Electromechanical</option>
							<option value="SS">SS — Solid State</option>
						</select>
					</div>
					<div class="field-group">
						<label for="ef-display-type">Display type</label>
						<select id="ef-display-type" bind:value={editFields.display_type}>
							<option value="reels">Reels</option>
							<option value="lights">Lights</option>
							<option value="alpha">Alphanumeric</option>
							<option value="dmd">DMD</option>
							<option value="cga">CGA</option>
							<option value="lcd">LCD</option>
						</select>
					</div>
				</div>

				<div class="form-row">
					<div class="field-group">
						<label for="ef-players">Players</label>
						<input
							id="ef-players"
							type="number"
							min="1"
							max="8"
							bind:value={editFields.player_count}
						/>
					</div>
					<div class="field-group">
						<label for="ef-flippers">Flippers</label>
						<input
							id="ef-flippers"
							type="number"
							min="0"
							max="10"
							bind:value={editFields.flipper_count}
						/>
					</div>
				</div>

				<div class="form-row">
					<div class="field-group">
						<label for="ef-theme">Theme</label>
						<input id="ef-theme" type="text" bind:value={editFields.theme} />
					</div>
					<div class="field-group">
						<label for="ef-mpu">MPU</label>
						<input id="ef-mpu" type="text" bind:value={editFields.mpu} />
					</div>
				</div>

				<div class="field-group">
					<label for="ef-production">Production quantity</label>
					<input
						id="ef-production"
						type="number"
						min="0"
						bind:value={editFields.production_quantity}
					/>
				</div>

				<fieldset>
					<legend>Cross-reference IDs</legend>
					<div class="form-row">
						<div class="field-group">
							<label for="ef-ipdb">IPDB ID</label>
							<input id="ef-ipdb" type="number" min="1" bind:value={editFields.ipdb_id} />
						</div>
						<div class="field-group">
							<label for="ef-opdb">OPDB ID</label>
							<input id="ef-opdb" type="text" bind:value={editFields.opdb_id} />
						</div>
						<div class="field-group">
							<label for="ef-pinside">Pinside ID</label>
							<input id="ef-pinside" type="number" min="1" bind:value={editFields.pinside_id} />
						</div>
					</div>
				</fieldset>

				<fieldset>
					<legend>Ratings</legend>
					<div class="form-row">
						<div class="field-group">
							<label for="ef-ipdb-rating">IPDB rating</label>
							<input
								id="ef-ipdb-rating"
								type="number"
								min="0"
								max="10"
								step="0.01"
								bind:value={editFields.ipdb_rating}
							/>
						</div>
						<div class="field-group">
							<label for="ef-pinside-rating">Pinside rating</label>
							<input
								id="ef-pinside-rating"
								type="number"
								min="0"
								max="10"
								step="0.01"
								bind:value={editFields.pinside_rating}
							/>
						</div>
					</div>
				</fieldset>

				<div class="field-group">
					<label for="ef-educational">About / educational text</label>
					<textarea id="ef-educational" rows="6" bind:value={editFields.educational_text}
					></textarea>
				</div>

				<div class="field-group">
					<label for="ef-sources-notes">Sources notes</label>
					<textarea id="ef-sources-notes" rows="4" bind:value={editFields.sources_notes}></textarea>
				</div>

				<div class="form-actions">
					<button type="submit" class="btn-save" disabled={saveStatus === 'saving'}>
						{saveStatus === 'saving' ? 'Saving…' : 'Save changes'}
					</button>
					{#if saveStatus === 'saved'}
						<span class="save-feedback saved">Saved</span>
					{/if}
					{#if saveStatus === 'error'}
						<span class="save-feedback error">{saveError}</span>
					{/if}
				</div>
			</form>
		</section>
	{/if}

	<!-- ── Activity tab ──────────────────────────────────────────────────────── -->
	{#if activeTab === 'activity'}
		{#if model.activity.length > 0}
			{@const { conflicts, agreed, single } = activityGroups}
			{@const contributorNames = [
				...new Set(
					model.activity
						.map((c) => c.source_name ?? (c.user_display ? `@${c.user_display}` : null))
						.filter(Boolean)
				)
			]}
			<section class="activity">
				<h2>Sources</h2>
				<p class="activity-summary">
					{contributorNames.join(' and ')} contributed to this record.
				</p>

				{#if conflicts.length > 0}
					<details class="activity-group" open>
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
										{#each claims as claim (claim.source_slug ?? claim.user_display ?? claim.created_at)}
											<span class="claim" class:used={claim.is_winner}>
												<span class="source-badge">{claimAttribution(claim)}</span>
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
												{claims.map(claimAttribution).join(', ')}
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
											<span class="source-badge">{claimAttribution(claims[0])}</span>
											{formatValue(claims[0].value)}
										</span>
									</dd>
								</div>
							{/each}
						</dl>
					</details>
				{/if}
			</section>
		{:else}
			<p class="no-activity">No source data recorded yet.</p>
		{/if}
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

	/* ── Tabs ─────────────────────────────────────────────────────────────── */

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
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -2px;
		cursor: pointer;
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

	/* ── Detail tab ───────────────────────────────────────────────────────── */

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

	/* ── Edit tab ─────────────────────────────────────────────────────────── */

	.edit-form {
		margin-bottom: var(--size-6);
	}

	form {
		display: flex;
		flex-direction: column;
		gap: var(--size-4);
	}

	fieldset {
		border: 1px solid var(--color-border-soft);
		border-radius: var(--radius-2);
		padding: var(--size-4);
		display: flex;
		flex-direction: column;
		gap: var(--size-4);
	}

	legend {
		font-size: var(--font-size-1);
		font-weight: 600;
		color: var(--color-text-muted);
		padding: 0 var(--size-2);
	}

	.form-row {
		display: flex;
		gap: var(--size-4);
	}

	.form-row .field-group {
		flex: 1;
	}

	.field-group {
		display: flex;
		flex-direction: column;
		gap: var(--size-1);
	}

	.field-group label {
		font-size: var(--font-size-1);
		font-weight: 500;
		color: var(--color-text-muted);
	}

	.field-group input,
	.field-group select,
	.field-group textarea {
		font-size: var(--font-size-1);
		color: var(--color-text-primary);
		background-color: var(--color-surface);
		border: 1px solid var(--color-border-soft);
		border-radius: var(--radius-2);
		padding: var(--size-2) var(--size-3);
		width: 100%;
		font-family: inherit;
	}

	.field-group input:focus,
	.field-group select:focus,
	.field-group textarea:focus {
		outline: 2px solid var(--color-accent);
		outline-offset: -1px;
		border-color: var(--color-accent);
	}

	textarea {
		resize: vertical;
	}

	.form-actions {
		display: flex;
		align-items: center;
		gap: var(--size-4);
	}

	.btn-save {
		padding: var(--size-2) var(--size-5);
		font-size: var(--font-size-1);
		font-weight: 600;
		color: #fff;
		background-color: var(--color-accent);
		border: none;
		border-radius: var(--radius-2);
		cursor: pointer;
	}

	.btn-save:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.save-feedback {
		font-size: var(--font-size-1);
	}

	.save-feedback.saved {
		color: var(--color-accent);
	}

	.save-feedback.error {
		color: var(--color-error, #c0392b);
	}

	/* ── Activity tab ─────────────────────────────────────────────────────── */

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

	.no-activity {
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
	}

	/* ── Footer ───────────────────────────────────────────────────────────── */

	.external-ids {
		display: flex;
		gap: var(--size-4);
		padding-top: var(--size-4);
		border-top: 1px solid var(--color-border-soft);
		margin-top: var(--size-4);
	}
</style>
