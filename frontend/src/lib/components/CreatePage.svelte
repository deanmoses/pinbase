<script lang="ts" generics="T extends { slug: string; name: string }">
	import { goto } from '$app/navigation';
	import Button from '$lib/components/Button.svelte';
	import NotesAndCitationsDetails from '$lib/components/NotesAndCitationsDetails.svelte';
	import TextField from '$lib/components/form/TextField.svelte';
	import { buildEditCitationRequest, type EditCitationSelection } from '$lib/edit-citation';
	import { pageTitle } from '$lib/constants';
	import { resolveHref } from '$lib/utils';
	import { classifyCreateResponse, reconcileSlug, slugifyForCatalog } from '$lib/create-form';
	import { toast } from '$lib/toast/toast.svelte';

	type SubmitBody = {
		name: string;
		slug: string;
		note: string;
		citation: ReturnType<typeof buildEditCitationRequest>;
	};

	type SubmitResult = {
		data?: T | undefined;
		error?: unknown;
		response: Response;
	};

	type Props = {
		entityLabel: string;
		heading?: string;
		initialName: string;
		submit: (body: SubmitBody) => Promise<SubmitResult>;
		detailHref: (slug: string) => string;
		cancelHref: string;
		parentBreadcrumb?: { text: string; href: string };
		projectSlug?: (name: string) => string;
		notePlaceholder?: string;
	};

	let {
		entityLabel,
		heading,
		initialName,
		submit,
		detailHref,
		cancelHref,
		parentBreadcrumb,
		projectSlug,
		notePlaceholder
	}: Props = $props();

	const project = (value: string) => (projectSlug ? projectSlug(value) : slugifyForCatalog(value));

	const headingText = $derived(heading ?? `New ${entityLabel}`);

	// svelte-ignore state_referenced_locally
	const initialSlug = project(initialName);
	// svelte-ignore state_referenced_locally
	let name = $state(initialName);
	let slug = $state(initialSlug);
	let syncedSlug = $state(initialSlug);
	let note = $state('');
	let citation = $state<EditCitationSelection | null>(null);

	let formError = $state('');
	let nameError = $state('');
	let slugError = $state('');
	let submitting = $state(false);

	$effect(() => {
		const next = reconcileSlug({ name, slug, syncedSlug, projectedSlug: project(name) });
		if (next.slug !== slug) {
			slug = next.slug;
			syncedSlug = next.syncedSlug;
		}
	});

	async function handleSave() {
		formError = '';
		nameError = '';
		slugError = '';

		if (!name.trim()) {
			nameError = 'Name cannot be blank.';
			return;
		}
		if (!slug.trim()) {
			slugError = 'Slug cannot be blank.';
			return;
		}

		submitting = true;
		try {
			const {
				data: created,
				error,
				response
			} = await submit({
				name: name.trim(),
				slug: slug.trim(),
				note: note || '',
				citation: buildEditCitationRequest(citation)
			});

			const outcome = classifyCreateResponse({ data: created, error, response });
			switch (outcome.kind) {
				case 'ok':
					toast.success(`Created “${outcome.data.name}”.`, { persistUntilNav: true });
					await goto(resolveHref(detailHref(outcome.slug)));
					return;
				case 'rate_limited':
					formError = outcome.message;
					return;
				case 'field_errors':
					nameError = outcome.fieldErrors.name ?? '';
					slugError = outcome.fieldErrors.slug ?? '';
					if (!nameError && !slugError) {
						formError = outcome.message;
					}
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
		goto(resolveHref(cancelHref));
	}
</script>

<svelte:head>
	<title>{pageTitle(headingText)}</title>
</svelte:head>

<div class="create-page">
	<header class="hdr">
		{#if parentBreadcrumb}
			<p class="parent-breadcrumb">
				<a href={resolveHref(parentBreadcrumb.href)}>{parentBreadcrumb.text}</a>
			</p>
		{/if}
		<h1>{headingText}</h1>
	</header>

	{#if formError}
		<p class="save-error" role="alert">{formError}</p>
	{/if}

	<div class="fields">
		<TextField label="Name" bind:value={name} error={nameError} />
		<TextField
			label="Slug"
			bind:value={slug}
			error={slugError}
			placeholder="lowercase-hyphenated"
		/>
	</div>

	<NotesAndCitationsDetails
		bind:note
		bind:citation
		noteLabel="Creation note"
		notePlaceholder={notePlaceholder ?? `Why are you adding this ${entityLabel.toLowerCase()}?`}
	/>

	<div class="form-footer">
		<Button variant="secondary" onclick={handleCancel}>Cancel</Button>
		<Button onclick={handleSave} disabled={submitting}>
			{submitting ? 'Creating…' : `Create ${entityLabel}`}
		</Button>
	</div>
</div>

<style>
	.create-page {
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

	.parent-breadcrumb {
		margin: 0 0 var(--size-1);
		font-size: var(--font-size-1);
		color: var(--color-text-muted);
	}

	.parent-breadcrumb a {
		color: var(--color-text-muted);
		text-decoration: none;
	}

	.parent-breadcrumb a:hover {
		color: var(--color-text-primary);
		text-decoration: underline;
	}

	.save-error {
		color: var(--color-error, #d32f2f);
		font-size: var(--font-size-1);
		margin: 0;
	}

	.fields {
		display: flex;
		flex-direction: column;
		gap: var(--size-3);
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
