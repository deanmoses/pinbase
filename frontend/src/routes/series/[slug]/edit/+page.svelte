<script lang="ts">
	import { untrack } from 'svelte';
	import { goto, invalidateAll } from '$app/navigation';
	import client from '$lib/api/client';
	import { diffScalarFields } from '$lib/edit-helpers';
	import { getEditRedirectHref } from '$lib/edit-routes';
	import EditFormShell from '$lib/components/form/EditFormShell.svelte';
	import TextField from '$lib/components/form/TextField.svelte';
	import MarkdownTextArea from '$lib/components/form/MarkdownTextArea.svelte';

	let { data } = $props();
	let series = $derived(data.series);

	function toFormFields(s: typeof series) {
		return {
			slug: s.slug,
			name: s.name,
			description: s.description?.text ?? ''
		};
	}

	// untrack: intentional one-time capture; re-synced explicitly after save
	let editFields = $state(untrack(() => toFormFields(data.series)));

	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let saveError = $state('');

	function getChangedFields(): Record<string, unknown> {
		return diffScalarFields(editFields, toFormFields(series));
	}

	async function saveChanges() {
		const fields = getChangedFields();
		if (Object.keys(fields).length === 0) return;

		saveStatus = 'saving';
		saveError = '';

		const { data: updated, error } = await client.PATCH('/api/series/{slug}/claims/', {
			params: { path: { slug: series.slug } },
			body: { fields }
		});

		if (updated) {
			const redirectHref = getEditRedirectHref('series', series.slug, updated.slug);
			editFields = toFormFields(updated);
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
	<MarkdownTextArea label="Description" bind:value={editFields.description} />
</EditFormShell>
