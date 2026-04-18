<script lang="ts">
	import type { SectionEditorHandle } from '$lib/components/editors/editor-contract';
	import type { ManufacturerEditSectionKey } from '$lib/components/editors/manufacturer-edit-sections';
	import ManufacturerBasicsEditor from './ManufacturerBasicsEditor.svelte';
	import ManufacturerDescriptionEditor from './ManufacturerDescriptionEditor.svelte';
	import ManufacturerNameEditor from './ManufacturerNameEditor.svelte';
	import type { ManufacturerEditView } from './manufacturer-edit-types';

	let {
		sectionKey,
		initialData,
		slug,
		editorRef = $bindable<SectionEditorHandle | undefined>(undefined),
		onsaved,
		onerror,
		ondirtychange
	}: {
		sectionKey: ManufacturerEditSectionKey;
		initialData: ManufacturerEditView;
		slug: string;
		editorRef?: SectionEditorHandle | undefined;
		onsaved: () => void;
		onerror: (message: string) => void;
		ondirtychange: (dirty: boolean) => void;
	} = $props();
</script>

{#if sectionKey === 'name'}
	<ManufacturerNameEditor
		bind:this={editorRef}
		{initialData}
		{slug}
		{onsaved}
		{onerror}
		{ondirtychange}
	/>
{:else if sectionKey === 'description'}
	<ManufacturerDescriptionEditor
		bind:this={editorRef}
		{initialData}
		{slug}
		{onsaved}
		{onerror}
		{ondirtychange}
	/>
{:else if sectionKey === 'basics'}
	<ManufacturerBasicsEditor
		bind:this={editorRef}
		{initialData}
		{slug}
		{onsaved}
		{onerror}
		{ondirtychange}
	/>
{/if}
