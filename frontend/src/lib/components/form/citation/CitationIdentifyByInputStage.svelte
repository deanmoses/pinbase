<script lang="ts">
	import client from '$lib/api/client';
	import {
		parseIdentifierInput,
		buildChildUrl,
		type ParentContext,
		type ChildSource
	} from './citation-types';
	import { createDebouncedSearch } from '../search-helpers';
	import DropdownHeader from '../DropdownHeader.svelte';

	let {
		parentContext,
		prefillIdentifier,
		onsourceidentified,
		oncancel,
		onback
	}: {
		parentContext: ParentContext;
		prefillIdentifier?: string;
		onsourceidentified: (child: {
			sourceId: number;
			sourceName: string;
			skipLocator: boolean;
		}) => void;
		oncancel: () => void;
		onback: () => void;
	} = $props();

	// -----------------------------------------------------------------------
	// State
	// -----------------------------------------------------------------------

	// svelte-ignore state_referenced_locally
	let rawInput = $state(prefillIdentifier ?? '');
	let children = $state<ChildSource[]>([]);
	let loading = $state(false);
	let lookupFailed = $state(false);
	let submitting = $state(false);
	let error = $state('');
	let inputEl: HTMLInputElement | undefined = $state();

	// -----------------------------------------------------------------------
	// Debounced children lookup
	// -----------------------------------------------------------------------

	const debouncedSearch = createDebouncedSearch<ChildSource>(
		async (q: string) => {
			if (!q.trim()) return [];
			loading = true;
			lookupFailed = false;
			try {
				const { data, error: apiError } = await client.GET(
					'/api/citation-sources/{source_id}/children/',
					{ params: { path: { source_id: parentContext.id }, query: { q } } }
				);
				if (apiError || !data) {
					lookupFailed = true;
					return [];
				}
				return data as ChildSource[];
			} catch {
				lookupFailed = true;
				return [];
			} finally {
				loading = false;
			}
		},
		(results) => {
			children = results;
		},
		200
	);

	$effect(() => {
		debouncedSearch.search(rawInput);
		return () => debouncedSearch.cancel();
	});

	$effect(() => {
		if (inputEl) {
			inputEl.focus();
		}
	});

	// -----------------------------------------------------------------------
	// Identifier parsing and matching
	// -----------------------------------------------------------------------

	let parsedId = $derived(
		parseIdentifierInput(parentContext.source_type, parentContext.identifier_key, rawInput)
	);

	let matchedChild = $derived.by(() => {
		if (!parsedId) return null;
		return (
			children.find((c) => {
				for (const url of c.urls) {
					const parsed = parseIdentifierInput(
						parentContext.source_type,
						parentContext.identifier_key,
						url
					);
					if (parsed === parsedId) return true;
				}
				return false;
			}) ?? null
		);
	});

	let canAct = $derived(!loading && !lookupFailed && parsedId !== null);
	let actionLabel = $derived(matchedChild ? 'Cite' : 'Create & cite');

	// -----------------------------------------------------------------------
	// Actions
	// -----------------------------------------------------------------------

	async function handleSubmit() {
		if (!parsedId || submitting) return;

		if (matchedChild) {
			onsourceidentified({
				sourceId: matchedChild.id,
				sourceName: matchedChild.name,
				skipLocator: matchedChild.skip_locator
			});
			return;
		}

		// Create a new child source
		submitting = true;
		error = '';

		const childUrl = buildChildUrl(parentContext.identifier_key, parsedId);
		const { data, error: apiError } = await client.POST('/api/citation-sources/', {
			body: {
				name: `${parentContext.name} #${parsedId}`,
				source_type: parentContext.source_type,
				author: '',
				publisher: '',
				date_note: '',
				description: '',
				parent_id: parentContext.id,
				url: childUrl,
				link_label: '',
				link_type: 'homepage'
			}
		});
		submitting = false;

		if (apiError) {
			error = typeof apiError === 'string' ? apiError : 'Failed to create source.';
			return;
		}

		onsourceidentified({
			sourceId: data.id,
			sourceName: data.name,
			skipLocator: data.skip_locator
		});
	}

	// -----------------------------------------------------------------------
	// Keyboard handling
	// -----------------------------------------------------------------------

	function handleKeydown(e: KeyboardEvent) {
		switch (e.key) {
			case 'Enter':
				e.preventDefault();
				if (canAct) handleSubmit();
				break;
			case 'Escape':
				e.preventDefault();
				oncancel();
				break;
			case 'Backspace':
				if (!rawInput) {
					e.preventDefault();
					onback();
				}
				break;
			case 'ArrowLeft':
				if (inputEl?.selectionStart === 0) {
					e.preventDefault();
					onback();
				}
				break;
		}
	}
</script>

<DropdownHeader {onback}>{parentContext.name}</DropdownHeader>
<div class="identify-form">
	<input
		bind:this={inputEl}
		type="text"
		aria-label="Enter identifier"
		placeholder="Paste URL or enter ID…"
		bind:value={rawInput}
		onkeydown={handleKeydown}
		autocomplete="off"
		data-1p-ignore
		data-lpignore="true"
	/>
	<div aria-live="polite">
		{#if loading}
			<div class="status-msg">Loading…</div>
		{:else if lookupFailed}
			<div class="status-msg status-error">Lookup failed — try again</div>
		{:else if parsedId && matchedChild}
			<div class="match-info">{matchedChild.name}</div>
		{:else if parsedId && !matchedChild}
			<div class="match-info new-hint">New — will create child source</div>
		{/if}
	</div>
	{#if error}
		<div class="form-error">{error}</div>
	{/if}
	<button
		class="submit-btn"
		disabled={!canAct || submitting}
		onpointerdown={(e) => {
			e.preventDefault();
			handleSubmit();
		}}
	>
		{#if submitting}
			Creating…
		{:else}
			{actionLabel}
		{/if}
	</button>
</div>

<style>
	.identify-form {
		padding: var(--size-2) var(--size-3);
		display: flex;
		flex-direction: column;
		gap: var(--size-2);
	}

	.match-info {
		font-size: var(--font-size-0);
		color: var(--color-text-muted);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.new-hint {
		font-style: italic;
	}

	.form-error {
		color: var(--color-danger, #c00);
		font-size: var(--font-size-0);
	}

	.status-msg {
		color: var(--color-text-muted);
		font-size: var(--font-size-0);
	}

	.status-error {
		color: var(--color-danger, #c00);
	}

	.submit-btn {
		padding: var(--size-1) var(--size-2);
		font-size: var(--font-size-1);
		font-family: inherit;
		border: 1px solid var(--color-input-border);
		border-radius: var(--radius-2);
		background-color: var(--color-input-focus-ring);
		color: var(--color-text-primary);
		cursor: pointer;
	}

	.submit-btn:hover:not(:disabled) {
		border-color: var(--color-input-focus);
	}

	.submit-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
