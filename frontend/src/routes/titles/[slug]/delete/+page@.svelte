<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import Button from '$lib/components/Button.svelte';
	import NotesAndCitationsDetails from '$lib/components/NotesAndCitationsDetails.svelte';
	import { pageTitle } from '$lib/constants';
	import { resolveHref } from '$lib/utils';
	import { toast } from '$lib/toast/toast.svelte';
	import type { EditCitationSelection } from '$lib/edit-citation';
	import type { BlockingReferrer } from './title-delete';
	import { submitDelete, submitUndoDelete } from './title-delete';

	let { data } = $props();
	let { preview, slug } = $derived(data);

	let note = $state('');
	let citation = $state<EditCitationSelection | null>(null);
	let formError = $state('');
	let submitting = $state(false);

	let blockedBy = $derived<BlockingReferrer[]>(preview.blocked_by ?? []);
	let isBlocked = $derived(blockedBy.length > 0);

	function pluralize(n: number, one: string, many?: string): string {
		return `${n} ${n === 1 ? one : (many ?? `${one}s`)}`;
	}

	async function handleDelete() {
		formError = '';
		submitting = true;
		try {
			const outcome = await submitDelete(slug, { note, citation });
			switch (outcome.kind) {
				case 'ok': {
					const titleName = preview.title_name;
					const changesetId = outcome.data.changeset_id;
					const handle = toast.success(`Deleted “${titleName}”.`, {
						persistUntilNav: true,
						dwellMs: 8_000,
						action: {
							label: 'Undo',
							onAction: async () => {
								const undo = await submitUndoDelete(changesetId);
								switch (undo.kind) {
									case 'ok':
										handle.update(`Restored “${titleName}”.`, {
											dwellMs: 4_000
										});
										return;
									case 'superseded':
										handle.update(undo.message, {
											dwellMs: 8_000,
											href: `/titles/${slug}/edit-history`
										});
										return;
									case 'form_error':
										handle.update(undo.message, { dwellMs: 8_000 });
										return;
								}
							}
						}
					});
					await goto(resolve('/titles'));
					return;
				}
				case 'rate_limited':
					formError = outcome.message;
					return;
				case 'blocked':
					// Shouldn't normally reach here — preview should have shown
					// blockers — but handle it defensively if state changed
					// between preview and submit.
					formError = outcome.message;
					return;
				case 'form_error':
					formError = outcome.message;
					return;
			}
		} finally {
			submitting = false;
		}
	}

	function handleCancel() {
		goto(resolve(`/titles/${slug}`));
	}
</script>

<svelte:head>
	<title>{pageTitle(`Delete ${preview.title_name}?`)}</title>
</svelte:head>

<div class="delete-page">
	<header class="hdr">
		<h1>Delete “{preview.title_name}”?</h1>
	</header>

	{#if isBlocked}
		<section class="blocked">
			<p class="blocked-lead">
				This title can't be deleted because active records still point at
				{blockedBy.length === 1 ? 'it' : 'parts of it'}:
			</p>
			<ul>
				{#each blockedBy as ref (ref.entity_type + (ref.slug ?? ''))}
					<li>
						{#if ref.slug && ref.entity_type === 'machinemodel'}
							<a href={resolveHref(`/models/${ref.slug}`)}>{ref.name}</a>
						{:else}
							{ref.name}
						{/if}
						<span class="muted">
							references
							{#if ref.blocked_target_slug}
								{ref.blocked_target_slug}
							{:else}
								this title
							{/if}
							via {ref.relation}
						</span>
					</li>
				{/each}
			</ul>
			<p class="muted">Resolve these references, then try again.</p>
		</section>
	{:else}
		<section class="impact">
			<p>This will hide:</p>
			<ul>
				<li>{pluralize(preview.active_model_count, 'model')}</li>
				<li>{pluralize(preview.changeset_count, 'change set')}</li>
			</ul>
			<p class="muted">
				You can undo this from the toast that appears on the titles list, or restore the record
				later from its edit history.
			</p>
		</section>
	{/if}

	{#if formError}
		<p class="save-error" role="alert">{formError}</p>
	{/if}

	{#if !isBlocked}
		<NotesAndCitationsDetails
			bind:note
			bind:citation
			noteLabel="Deletion note"
			notePlaceholder="Why are you deleting this title?"
		/>
	{/if}

	<div class="form-footer">
		<Button variant="secondary" onclick={handleCancel}>Cancel</Button>
		{#if !isBlocked}
			<Button onclick={handleDelete} disabled={submitting}>
				{submitting ? 'Deleting…' : 'Delete Title'}
			</Button>
		{/if}
	</div>
</div>

<style>
	.delete-page {
		max-width: 36rem;
		margin: 0 auto;
		padding: var(--size-6) var(--size-5);
		display: flex;
		flex-direction: column;
		gap: var(--size-4);
	}

	.hdr h1 {
		margin: 0 0 var(--size-2);
	}

	.impact,
	.blocked {
		background: var(--color-surface-muted);
		border: 1px solid var(--color-border-soft);
		border-radius: var(--size-2);
		padding: var(--size-3) var(--size-4);
	}

	.impact ul,
	.blocked ul {
		margin: var(--size-2) 0;
		padding-left: var(--size-4);
	}

	.impact li,
	.blocked li {
		margin: var(--size-1) 0;
	}

	.muted {
		color: var(--color-text-muted);
		font-size: var(--font-size-0);
	}

	.blocked-lead {
		margin: 0 0 var(--size-2);
	}

	.save-error {
		color: var(--color-error, #d32f2f);
		font-size: var(--font-size-1);
		margin: 0;
	}

	.form-footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--size-3);
		margin-top: var(--size-4);
		padding-top: var(--size-3);
		border-top: 1px solid var(--color-border-soft);
	}
</style>
