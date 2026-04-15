<script lang="ts">
	import type { Snippet } from 'svelte';
	import { type EditCitationSelection } from '$lib/edit-citation';
	import Button from '$lib/components/Button.svelte';
	import EditCitationField from '$lib/components/form/EditCitationField.svelte';
	import TextField from '$lib/components/form/TextField.svelte';
	import Modal from '$lib/components/Modal.svelte';

	type ModalSaveMeta = { note: string; citation: EditCitationSelection | null };

	let {
		heading,
		open,
		error = '',
		showCitation = true,
		showMixedEditWarning = false,
		onclose,
		onsave,
		children
	}: {
		heading: string;
		open: boolean;
		error?: string;
		showCitation?: boolean;
		showMixedEditWarning?: boolean;
		onclose: () => void;
		onsave: (meta: ModalSaveMeta) => void;
		children: Snippet;
	} = $props();

	let note = $state('');
	let citation = $state<EditCitationSelection | null>(null);

	// Reset note/citation state when the modal opens
	$effect(() => {
		if (open) {
			note = '';
			citation = null;
		}
	});

	function close() {
		onclose();
	}
</script>

<Modal title={`Edit ${heading}`} {open} onclose={close}>
	{#if error}
		<p class="save-error">{error}</p>
	{/if}
	{@render children()}

	<details class="meta-section">
		<summary>{showCitation ? 'Notes & Citations' : 'Notes'}</summary>
		<div class="meta-fields">
			<TextField
				label="Edit note"
				bind:value={note}
				placeholder="Why are you making this change?"
			/>
			{#if showCitation}
				<EditCitationField bind:citation {showMixedEditWarning} />
			{/if}
		</div>
	</details>

	{#snippet footer()}
		<button type="button" class="btn-cancel" onclick={close}>Cancel</button>
		<Button onclick={() => onsave({ note, citation })}>Save</Button>
	{/snippet}
</Modal>

<style>
	.btn-cancel {
		background: none;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-2);
		padding: var(--size-1) var(--size-3);
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
		cursor: pointer;
	}

	.btn-cancel:hover {
		color: var(--color-text-primary);
		border-color: var(--color-text-muted);
	}

	.save-error {
		color: var(--color-error, #d32f2f);
		font-size: var(--font-size-1);
		margin: 0 0 var(--size-3);
	}

	.meta-section {
		margin-top: var(--size-4);
		border-top: 1px solid var(--color-border-soft);
		padding-top: var(--size-3);
		background: inherit;
	}

	.meta-section > summary {
		cursor: pointer;
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
		user-select: none;
		background: inherit;
	}

	.meta-fields {
		display: flex;
		flex-direction: column;
		gap: var(--size-3);
		margin-top: var(--size-3);
	}
</style>
