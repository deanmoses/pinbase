<script lang="ts">
	import { untrack } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { resolveHref } from '$lib/utils';
	import client from '$lib/api/client';
	import SearchableSelect from '$lib/components/SearchableSelect.svelte';
	import EditFormShell from '$lib/components/form/EditFormShell.svelte';
	import TextAreaField from '$lib/components/form/TextAreaField.svelte';
	import TextField from '$lib/components/form/TextField.svelte';
	import { buildModelBoundary, buildTitlePatchBody, titleToFormState } from '../title-edit';

	let { data } = $props();
	let title = $derived(data.title);
	let boundary = $derived(buildModelBoundary(title));

	let editFields = $state(untrack(() => titleToFormState(data.title)));
	let selectedFranchise = $state<string | null>(untrack(() => data.title.franchise?.slug ?? null));
	let editNote = $state('');

	let franchiseOptions = $state<{ slug: string; label: string; count: number }[]>([]);

	$effect(() => {
		client.GET('/api/franchises/all/').then(({ data: franchises }) => {
			if (franchises) {
				franchiseOptions = franchises.map((franchise) => ({
					slug: franchise.slug,
					label: franchise.name,
					count: franchise.title_count
				}));
			}
		});
	});

	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let saveError = $state('');

	async function saveChanges() {
		const body = buildTitlePatchBody(
			{ ...editFields, franchiseSlug: selectedFranchise ?? '' },
			title,
			editNote
		);
		if (!body) return;

		saveStatus = 'saving';
		saveError = '';

		const { data: updated, error } = await client.PATCH('/api/titles/{slug}/claims/', {
			params: { path: { slug: title.slug } },
			body
		});

		if (updated) {
			editFields = titleToFormState(updated);
			selectedFranchise = updated.franchise?.slug ?? null;
			editNote = '';
			await invalidateAll();
			saveStatus = 'saved';
			setTimeout(() => (saveStatus = 'idle'), 3000);
		} else {
			saveStatus = 'error';
			saveError = error ? JSON.stringify(error) : 'Save failed.';
		}
	}
</script>

<EditFormShell {saveStatus} {saveError} onsave={saveChanges}>
	<section class="boundary">
		<h3>Edited On Model Pages</h3>
		<p>
			Credits, machine roster, variants, specifications, ratings, external IDs, and other
			model-specific metadata stay read-only here.
		</p>

		<ul class="boundary-list">
			<li>People and credits</li>
			<li>Machine roster and variants</li>
			<li>Specifications, ratings, and production data</li>
			<li>External IDs and model-specific metadata</li>
		</ul>

		{#if boundary.modelLinks.length > 0}
			<div class="boundary-links">
				<span class="boundary-label">Models in this title</span>
				<ul>
					{#each boundary.modelLinks as model (model.slug)}
						<li><a href={resolveHref(`/models/${model.slug}`)}>{model.name}</a></li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if boundary.singleModelActions}
			<div class="single-model-actions">
				<a href={resolveHref(boundary.singleModelActions.editHref)}>Edit model</a>
				<a href={resolveHref(boundary.singleModelActions.activityHref)}>Model activity</a>
			</div>
		{/if}
	</section>

	<TextField label="Name" bind:value={editFields.name} />
	<TextAreaField label="Description" bind:value={editFields.description} rows={6} />

	<div class="field-group">
		<SearchableSelect
			label="Franchise"
			options={franchiseOptions}
			bind:selected={selectedFranchise}
			allowZeroCount
			placeholder="Search franchises..."
		/>
	</div>

	<TextAreaField label="Abbreviations" bind:value={editFields.abbreviationsText} rows={3} />
	<p class="field-help">Separate abbreviations with commas or new lines.</p>

	<TextField
		label="Edit note"
		bind:value={editNote}
		placeholder="Why are you making this change?"
		optional
	/>
</EditFormShell>

<style>
	.boundary {
		border: 1px solid var(--color-border-soft);
		border-radius: var(--radius-2);
		padding: var(--size-4);
		background: var(--color-surface-2, rgba(0, 0, 0, 0.02));
	}

	.boundary h3 {
		margin: 0 0 var(--size-2);
		font-size: var(--font-size-2);
	}

	.boundary p {
		margin: 0 0 var(--size-3);
		color: var(--color-text-muted);
	}

	.boundary-list,
	.boundary-links ul {
		margin: 0;
		padding-left: var(--size-4);
	}

	.boundary-links {
		margin-top: var(--size-3);
	}

	.boundary-label {
		display: block;
		margin-bottom: var(--size-1);
		font-weight: 600;
	}

	.single-model-actions {
		display: flex;
		gap: var(--size-4);
		margin-top: var(--size-3);
	}

	.field-help {
		margin: calc(var(--size-3) * -1) 0 0;
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
	}
</style>
