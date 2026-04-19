<script lang="ts">
	import { untrack } from 'svelte';
	import NumberField from '$lib/components/form/NumberField.svelte';
	import type { SectionEditorProps } from '$lib/components/editors/editor-contract';
	import { diffScalarFields } from '$lib/edit-helpers';
	import type { DisplayTypeEditView } from './display-type-edit-types';
	import {
		saveDisplayTypeClaims,
		type FieldErrors,
		type SaveMeta,
		type SaveResult
	} from './save-display-type-claims';

	type DisplayOrderFields = {
		display_order: string | number;
	};

	let {
		initialData,
		slug,
		onsaved,
		onerror,
		ondirtychange = () => {}
	}: SectionEditorProps<DisplayTypeEditView> = $props();

	function extractFields(displayType: DisplayTypeEditView): DisplayOrderFields {
		return {
			display_order: displayType.display_order ?? ''
		};
	}

	const original = untrack(() => extractFields(initialData));
	let fields = $state<DisplayOrderFields>({ ...original });
	let fieldErrors = $state<FieldErrors>({});
	let changedFields = $derived(diffScalarFields(fields, original));
	let dirty = $derived(Object.keys(changedFields).length > 0);

	$effect(() => {
		ondirtychange(dirty);
	});

	export function isDirty(): boolean {
		return dirty;
	}

	export async function save(meta?: SaveMeta): Promise<void> {
		fieldErrors = {};
		if (!dirty) {
			onsaved();
			return;
		}

		const result: SaveResult = await saveDisplayTypeClaims(slug, {
			fields: changedFields,
			...meta
		});

		if (result.ok) {
			onsaved();
		} else {
			fieldErrors = result.fieldErrors;
			onerror(
				Object.keys(result.fieldErrors).length > 0 ? 'Please fix the errors below.' : result.error
			);
		}
	}
</script>

<div class="editor-fields">
	<NumberField
		label="Display order"
		bind:value={fields.display_order}
		error={fieldErrors.display_order ?? ''}
	/>
</div>

<style>
	.editor-fields {
		display: flex;
		flex-direction: column;
		gap: var(--size-3);
	}
</style>
