<script lang="ts">
	import { untrack } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import client from '$lib/api/client';
	import EditFormShell from '$lib/components/form/EditFormShell.svelte';
	import TagInput from '$lib/components/form/TagInput.svelte';
	import TextField from '$lib/components/form/TextField.svelte';
	import TextAreaField from '$lib/components/form/TextAreaField.svelte';
	import NumberField from '$lib/components/form/NumberField.svelte';

	let { data } = $props();
	let ce = $derived(data.corporateEntity);

	// --- Form state ---

	function toFormFields(e: typeof ce) {
		return {
			name: e.name,
			description: e.description?.text ?? '',
			year_start: e.year_start ?? '',
			year_end: e.year_end ?? ''
		};
	}

	let editFields = $state(untrack(() => toFormFields(data.corporateEntity)));
	let editAliases = $state<string[]>(untrack(() => [...(data.corporateEntity.aliases ?? [])]));
	let editNote = $state('');

	// --- Change detection ---

	function getChangedScalarFields(): Record<string, unknown> {
		const original = toFormFields(ce);
		const changed: Record<string, unknown> = {};
		for (const key of Object.keys(editFields) as (keyof typeof editFields)[]) {
			let val: unknown = editFields[key];
			if (typeof val === 'number' && isNaN(val)) val = '';
			if (String(val) !== String(original[key])) {
				changed[key] = val === '' ? null : val;
			}
		}
		return changed;
	}

	function aliasesChanged(): boolean {
		const original = [...(ce.aliases ?? [])].sort();
		const current = [...editAliases].sort();
		return JSON.stringify(original) !== JSON.stringify(current);
	}

	// --- Save ---

	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let saveError = $state('');

	async function saveChanges() {
		const fields = getChangedScalarFields();
		const hasFields = Object.keys(fields).length > 0;
		const hasAliases = aliasesChanged();

		if (!hasFields && !hasAliases) return;

		saveStatus = 'saving';
		saveError = '';

		const { data: updated, error } = await client.PATCH('/api/corporate-entities/{slug}/claims/', {
			params: { path: { slug: ce.slug } },
			body: {
				fields: hasFields ? fields : {},
				aliases: hasAliases ? editAliases : null,
				note: editNote.trim()
			}
		});

		if (updated) {
			editFields = toFormFields(updated);
			editAliases = [...(updated.aliases ?? [])];
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
	<TextField label="Name" bind:value={editFields.name} />
	<TextAreaField label="Description" bind:value={editFields.description} rows={6} />

	<fieldset class="date-group">
		<legend>Years active</legend>
		<div class="date-row">
			<NumberField label="Established" bind:value={editFields.year_start} min={1800} max={2100} />
			<NumberField
				label="Ceased operations"
				bind:value={editFields.year_end}
				min={1800}
				max={2100}
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
