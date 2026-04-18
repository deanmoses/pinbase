<script lang="ts">
	import type { SectionEditorHandle } from '$lib/components/editors/editor-contract';
	import type { FranchiseEditSectionKey } from '$lib/components/editors/franchise-edit-sections';
	import FranchiseDescriptionEditor from './FranchiseDescriptionEditor.svelte';
	import FranchiseNameEditor from './FranchiseNameEditor.svelte';
	import type { FranchiseEditView } from './franchise-edit-types';

	let {
		sectionKey,
		initialData,
		slug,
		editorRef = $bindable<SectionEditorHandle | undefined>(undefined),
		onsaved,
		onerror,
		ondirtychange
	}: {
		sectionKey: FranchiseEditSectionKey;
		initialData: FranchiseEditView;
		slug: string;
		editorRef?: SectionEditorHandle | undefined;
		onsaved: () => void;
		onerror: (message: string) => void;
		ondirtychange: (dirty: boolean) => void;
	} = $props();
</script>

{#if sectionKey === 'name'}
	<FranchiseNameEditor
		bind:this={editorRef}
		{initialData}
		{slug}
		{onsaved}
		{onerror}
		{ondirtychange}
	/>
{:else if sectionKey === 'description'}
	<FranchiseDescriptionEditor
		bind:this={editorRef}
		{initialData}
		{slug}
		{onsaved}
		{onerror}
		{ondirtychange}
	/>
{/if}
