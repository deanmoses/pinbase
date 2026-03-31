<script lang="ts">
	import { untrack } from 'svelte';
	import { goto, invalidateAll } from '$app/navigation';
	import client from '$lib/api/client';
	import { getEditRedirectHref } from '$lib/edit-routes';
	import EditFormShell from '$lib/components/form/EditFormShell.svelte';
	import TagInput from '$lib/components/form/TagInput.svelte';
	import TextField from '$lib/components/form/TextField.svelte';
	import MarkdownTextArea from '$lib/components/form/MarkdownTextArea.svelte';
	import NumberField from '$lib/components/form/NumberField.svelte';
	import { fetchFieldConstraints, fc, type FieldConstraints } from '$lib/field-constraints';
	import {
		buildCorporateEntityPatchBody,
		corporateEntityToFormFields
	} from './corporate-entity-edit';

	let { data } = $props();
	let ce = $derived(data.corporateEntity);

	let editFields = $state(untrack(() => corporateEntityToFormFields(data.corporateEntity)));
	let editAliases = $state<string[]>(untrack(() => [...(data.corporateEntity.aliases ?? [])]));
	let editNote = $state('');

	let constraints = $state<FieldConstraints>({});

	$effect(() => {
		fetchFieldConstraints('corporate-entity').then((c) => {
			constraints = c;
		});
	});

	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let saveError = $state('');

	async function saveChanges() {
		const body = buildCorporateEntityPatchBody(
			{ fields: editFields, aliases: editAliases, note: editNote },
			ce
		);
		if (!body) return;

		saveStatus = 'saving';
		saveError = '';

		const { data: updated, error } = await client.PATCH('/api/corporate-entities/{slug}/claims/', {
			params: { path: { slug: ce.slug } },
			body
		});

		if (updated) {
			const redirectHref = getEditRedirectHref('corporate-entities', ce.slug, updated.slug);
			editFields = corporateEntityToFormFields(updated);
			editAliases = [...(updated.aliases ?? [])];
			editNote = '';
			if (redirectHref) {
				await goto(redirectHref, { replaceState: true });
				return;
			}
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
	<TextField label="Name" bind:value={editFields.name} />
	<TextField label="Slug" bind:value={editFields.slug} />
	<MarkdownTextArea label="Description" bind:value={editFields.description} rows={6} />

	<fieldset class="date-group">
		<legend>Years active</legend>
		<div class="date-row">
			<NumberField
				label="Established"
				bind:value={editFields.year_start}
				{...fc(constraints, 'year_start')}
			/>
			<NumberField
				label="Ceased operations"
				bind:value={editFields.year_end}
				{...fc(constraints, 'year_end')}
			/>
		</div>
	</fieldset>

	<TagInput
		label="Aliases"
		bind:tags={editAliases}
		placeholder="Type an alias and press Enter"
		optional
	/>

	<TextField
		label="Edit note"
		bind:value={editNote}
		placeholder="Why are you making this change?"
		optional
	/>
</EditFormShell>

<style>
	.date-group {
		border: 1px solid var(--color-border-soft);
		border-radius: var(--radius-2);
		padding: var(--size-3);
		margin: 0;
	}

	.date-group legend {
		font-size: var(--font-size-1);
		font-weight: 500;
		color: var(--color-text-muted);
		padding: 0 var(--size-1);
	}

	.date-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--size-3);
	}
</style>
