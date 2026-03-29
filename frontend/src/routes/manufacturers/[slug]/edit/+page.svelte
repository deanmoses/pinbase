<script lang="ts">
	import { untrack } from 'svelte';
	import { goto, invalidateAll } from '$app/navigation';
	import client from '$lib/api/client';
	import { getEditRedirectHref } from '$lib/edit-routes';
	import EditFormShell from '$lib/components/form/EditFormShell.svelte';
	import TextField from '$lib/components/form/TextField.svelte';
	import TextAreaField from '$lib/components/form/TextAreaField.svelte';
	import { buildManufacturerPatchBody, manufacturerToFormFields } from './manufacturer-edit';

	let { data } = $props();
	let mfr = $derived(data.manufacturer);

	// untrack: intentional one-time capture; re-synced explicitly after save
	let editFields = $state(untrack(() => manufacturerToFormFields(data.manufacturer)));

	let saveStatus = $state<'idle' | 'saving' | 'saved' | 'error'>('idle');
	let saveError = $state('');

	async function saveChanges() {
		const body = buildManufacturerPatchBody(editFields, mfr);
		if (!body) return;

		saveStatus = 'saving';
		saveError = '';

		const { data: updated, error } = await client.PATCH('/api/manufacturers/{slug}/claims/', {
			params: { path: { slug: mfr.slug } },
			body
		});

		if (updated) {
			const redirectHref = getEditRedirectHref('manufacturers', mfr.slug, updated.slug);
			editFields = manufacturerToFormFields(updated);
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
	<TextAreaField label="Description" bind:value={editFields.description} />
	<TextField label="Website" bind:value={editFields.website} type="url" />
	<TextField label="Logo URL" bind:value={editFields.logo_url} type="url" />
</EditFormShell>
